"""Read boundaries: no-follow files, descriptor checks and a YAML parsing budget (review P2s)."""
import importlib
import os

import pytest


def state():
    return importlib.import_module('axiom_agent.state')


def context():
    return importlib.import_module('axiom_agent.context')


class Context:
    def has_plugin(self, name):
        return False


def manifest_dir(home, name='sample'):
    folder = home / 'plugins' / name
    folder.mkdir(parents=True)
    return folder


def test_symlinked_owner_folder_is_never_followed(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'doctrine.local.md').write_text('Never inject this file.', encoding='utf-8')
    (tmp_path / 'axiom-agent').symlink_to(outside)
    text = context().owner_additions(tmp_path, cap=800)
    assert 'unreadable' in text
    assert 'Never inject' not in text


def test_symlinked_hermes_home_is_allowed_for_owner_additions(tmp_path):
    real = tmp_path / 'real-home'
    (real / 'axiom-agent').mkdir(parents=True)
    (real / 'axiom-agent' / 'doctrine.local.md').write_text('Owner rule.', encoding='utf-8')
    (tmp_path / 'home').symlink_to(real)
    assert 'Owner rule.' in context().owner_additions(tmp_path / 'home', cap=800)


def test_owner_additions_normalise_newlines_like_text_mode(tmp_path):
    (tmp_path / 'axiom-agent').mkdir()
    (tmp_path / 'axiom-agent' / 'doctrine.local.md').write_bytes(b'one\r\ntwo\rthree\n')
    assert context().owner_additions(tmp_path).endswith('one\ntwo\nthree\n')


def test_owner_cap_keeps_a_multibyte_character_split_at_the_read_limit(tmp_path):
    (tmp_path / 'axiom-agent').mkdir()
    (tmp_path / 'axiom-agent' / 'doctrine.local.md').write_text('\u00e9' * 5000, encoding='utf-8')
    text = context().owner_additions(tmp_path, cap=800)
    assert len(text) <= 800
    assert 'truncated' in text and 'unreadable' not in text


def test_symlinked_manifest_file_is_unknown_not_read(tmp_path):
    outside = tmp_path / 'outside.yaml'
    outside.write_text('name: tripwire\n', encoding='utf-8')
    (manifest_dir(tmp_path) / 'plugin.yaml').symlink_to(outside)
    states = state().read_states(Context(), tmp_path)
    assert states['tripwire'].installed is None


def test_symlinked_plugin_checkout_is_a_normal_install(tmp_path):
    checkout = tmp_path / 'dev' / 'tripwire'
    checkout.mkdir(parents=True)
    (checkout / 'plugin.yaml').write_text('name: tripwire\n', encoding='utf-8')
    (tmp_path / 'plugins').mkdir()
    (tmp_path / 'plugins' / 'tripwire').symlink_to(checkout)
    states = state().read_states(Context(), tmp_path)
    assert states['tripwire'].installed is True
    assert states['standing'].installed is False


def test_fifo_manifest_is_unknown_without_blocking(tmp_path):
    os.mkfifo(manifest_dir(tmp_path) / 'plugin.yaml')
    assert state().read_states(Context(), tmp_path)['standing'].installed is None


LAUGHS = 'a: &a [x, x, x, x, x, x, x, x, x]\n' + ''.join(
    f'{chr(98 + i)}: &{chr(98 + i)} [' + ', '.join([f'*{chr(97 + i)}'] * 9) + ']\n' for i in range(9))


@pytest.mark.parametrize('metadata', [
    LAUGHS + 'name: tripwire\n',
    'base: &base {k: v}\nname: tripwire\nother:\n  <<: *base\n',
    'name: tripwire\nnested: ' + '[' * 5000 + ']' * 5000 + '\n',
    "junk: {p: don't, a: &a {x: x}, q: can't}\nname: tripwire\nmore: [*a, *a]\n",
])
def test_yaml_expansion_costs_nothing_because_no_document_is_built(tmp_path, monkeypatch, metadata):
    import sys
    (manifest_dir(tmp_path) / 'plugin.yaml').write_text(metadata, encoding='utf-8')
    for name in ('yaml', 'hermes_yaml'):  # a YAML import here would fail the test
        monkeypatch.setitem(sys.modules, name, None)
    module = importlib.reload(state())
    assert module.read_states(Context(), tmp_path)['tripwire'].installed is True


def test_plain_descriptions_with_stars_or_ampersands_still_parse(tmp_path):
    (manifest_dir(tmp_path) / 'plugin.yaml').write_text(
        'name: tripwire\ndescription: "Q&A, 5 * 3, a & b"\n', encoding='utf-8')
    assert state().read_states(Context(), tmp_path)['tripwire'].installed is True


@pytest.mark.parametrize('line,expected', [
    ('name: tripwire', 'tripwire'),
    ('name:   tripwire   # comment', 'tripwire'),
    ('name: "hermes-standing"', 'hermes-standing'),
    ("name: 'tripwire'  # quoted", 'tripwire'),
    ('\ufeffname: tripwire', 'tripwire'),
])
def test_top_level_name_line_forms(line, expected):
    assert state()._top_level_name(line + '\nversion: 1.0.0\n') == expected


@pytest.mark.parametrize('text', [
    'version: 1\n', 'name:\n  tripwire\n', 'name: |\n  tripwire\n', 'name: [tripwire]\n',
    'name: tripwire\nname: standing\n', '  name: tripwire\n', 'name: "trip wire"\n',
    'name: tripwire#x\n', 'name: *alias\n', '{name: tripwire}\n',
])
def test_unclear_names_are_refused(text):
    with pytest.raises(ValueError):
        state()._top_level_name(text)


def test_inventory_work_is_bounded(tmp_path, monkeypatch):
    module = state()
    monkeypatch.setattr(module, 'ENTRY_CAP', 3)
    for index in range(5):
        manifest_dir(tmp_path, f'p{index}')
    states = module.read_states(Context(), tmp_path)
    assert states['tripwire'].installed is None


def open_fds():
    return len(os.listdir('/dev/fd'))


@pytest.mark.parametrize('failure', ['scandir', 'manifest', 'subdir'])
def test_failed_inventory_never_leaks_descriptors(tmp_path, monkeypatch, failure):
    from axiom_agent import files
    module = state()
    folder = manifest_dir(tmp_path)
    (folder / 'plugin.yaml').write_text('name: tripwire\n', encoding='utf-8')
    def denied(*args, **kwargs):
        raise PermissionError('private error')
    if failure == 'scandir':
        monkeypatch.setattr(files.os, 'scandir', denied)
    elif failure == 'manifest':
        monkeypatch.setattr(module, '_manifest_name', denied)
    else:
        real = files.open_dir
        monkeypatch.setattr(files, 'open_dir',
                            lambda name, parent=None, follow=False: denied() if name == 'sample'
                            else real(name, parent, follow))
    before = open_fds()
    for _ in range(50):
        assert module.read_states(Context(), tmp_path)['tripwire'].installed is None
    assert open_fds() == before


def test_successful_inventory_and_owner_reads_never_leak_descriptors(tmp_path):
    (manifest_dir(tmp_path, 'group') / 'tripwire').mkdir()
    (tmp_path / 'plugins' / 'group' / 'tripwire' / 'plugin.yaml').write_text('name: tripwire\n', encoding='utf-8')
    (tmp_path / 'axiom-agent').mkdir()
    (tmp_path / 'axiom-agent' / 'doctrine.local.md').write_text('Owner rule.', encoding='utf-8')
    before = open_fds()
    for _ in range(50):
        assert state().read_states(Context(), tmp_path)['tripwire'].installed is True
        assert 'Owner rule.' in context().owner_additions(tmp_path, cap=800)
    assert open_fds() == before


def test_platform_without_descriptor_support_degrades_to_unknown(tmp_path, monkeypatch):
    from axiom_agent import files
    from axiom_agent.service import DoctrineService
    (manifest_dir(tmp_path) / 'plugin.yaml').write_text('name: tripwire\n', encoding='utf-8')
    (tmp_path / 'axiom-agent').mkdir()
    (tmp_path / 'axiom-agent' / 'doctrine.local.md').write_text('Owner rule.', encoding='utf-8')
    monkeypatch.setattr(files, 'SUPPORTED', False)
    assert state().read_states(Context(), tmp_path)['tripwire'].installed is None
    assert 'unreadable' in context().owner_additions(tmp_path, cap=800)
    assert '0 of 9 enforced' in DoctrineService(Context(), lambda: tmp_path).command('')


@pytest.mark.parametrize('metadata', [
    'name: tripwire\ndescription: Use *markdown* for output.\n',
    "name: tripwire\ndescription: '*quoted* & <<: fine'\n",
    'name: tripwire  # *not an alias*\n',
    'name: tripwire\ntags: [a&b, "x*y"]\n',
    'name: tripwire\ndescription: |\n  Intro\n  *markdown* line\n',
])
def test_ordinary_prose_is_never_misread(tmp_path, metadata):
    (manifest_dir(tmp_path) / 'plugin.yaml').write_text(metadata, encoding='utf-8')
    assert state().read_states(Context(), tmp_path)['tripwire'].installed is True


def test_runtime_never_imports_a_yaml_parser():
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for path in [root / '__init__.py', *sorted((root / 'axiom_agent').glob('*.py'))]:
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            assert not any('yaml' in name for name in names), path.name
