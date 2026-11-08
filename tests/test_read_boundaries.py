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


@pytest.mark.parametrize('metadata', [
    'a: &a [x, x]\nb: &b [*a, *a]\nc: [*b, *b]\nname: tripwire\n',
    'base: &base {k: v}\nname: tripwire\nother:\n  <<: *base\n',
    'name: tripwire\nnested: ' + '[' * 300 + ']' * 300 + '\n',
])
def test_yaml_expansion_features_are_refused_before_parsing(tmp_path, monkeypatch, metadata):
    module = state()
    (manifest_dir(tmp_path) / 'plugin.yaml').write_text(metadata, encoding='utf-8')
    def unexpected(text):
        pytest.fail('must refuse before parsing')
    monkeypatch.setattr(module.yaml, 'safe_load', unexpected)
    assert module.read_states(Context(), tmp_path)['tripwire'].installed is None


def test_plain_descriptions_with_stars_or_ampersands_still_parse(tmp_path):
    (manifest_dir(tmp_path) / 'plugin.yaml').write_text(
        'name: tripwire\ndescription: "Q&A, 5 * 3, a & b"\n', encoding='utf-8')
    assert state().read_states(Context(), tmp_path)['tripwire'].installed is True


def test_inventory_work_is_bounded(tmp_path, monkeypatch):
    module = state()
    monkeypatch.setattr(module, 'ENTRY_CAP', 3)
    for index in range(5):
        manifest_dir(tmp_path, f'p{index}')
    states = module.read_states(Context(), tmp_path)
    assert states['tripwire'].installed is None
