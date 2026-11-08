import importlib
from itertools import product
from pathlib import Path

import pytest

NAMES = ('standing', 'hermes-axioma', 'tripwire', 'handydandy', 'hermes-gatekeeper')


def module():
    return importlib.import_module('axiom_agent.state')


class Context:
    def __init__(self, active=()):
        self.active = set(active)
        self.probes = []

    def has_plugin(self, name):
        self.probes.append(name)
        return name in self.active


@pytest.mark.parametrize('flags', list(product((False, True), repeat=5)))
def test_runtime_probe_for_every_enforcer_combination(tmp_path, flags):
    active = {name for name, flag in zip(NAMES, flags) if flag}
    ctx = Context(active)
    states = module().read_states(ctx, tmp_path)
    assert tuple(states) == NAMES
    for name in NAMES:
        assert states[name].enabled is (name in active)
        assert states[name].installed is (name in active)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('catalog,manifest', [(name, name) for name in NAMES] + [('standing', 'hermes-standing')])
@pytest.mark.parametrize('layout', ['flat', 'category'])
def test_disabled_installs_use_only_metadata_never_plugin_code(tmp_path, catalog, manifest, layout):
    root = tmp_path / 'plugins'
    folder = root / ('group/renamed' if layout == 'category' else 'renamed')
    folder.mkdir(parents=True)
    (folder / 'plugin.yaml').write_text(f'name: {manifest}\nversion: 1.0.0\n', encoding='utf-8')
    (folder / '__init__.py').write_text('raise AssertionError("must never import")', encoding='utf-8')
    state = module().read_states(Context(), tmp_path)[catalog]
    assert state.installed is True
    assert state.enabled is False


def test_standing_manifest_alias_is_a_runtime_probe(tmp_path):
    ctx = Context({'hermes-standing'})
    state = module().read_states(ctx, tmp_path)['standing']
    assert state.enabled is True
    assert state.installed is True
    assert 'hermes-standing' in ctx.probes


def test_probe_errors_are_unknown_not_enforced(tmp_path):
    class Broken:
        def has_plugin(self, name):
            raise RuntimeError('private error')
    states = module().read_states(Broken(), tmp_path)
    assert all(state.enabled is None for state in states.values())


@pytest.mark.parametrize('metadata', ['[', 'name: [invalid]', 'a' * 70000, '\u001b',
                                    'name: unrelated\nversion: 1' + ':00' * 180 + '.0\n'])
def test_bad_metadata_is_unknown_not_absent(tmp_path, metadata):
    folder = tmp_path / 'plugins' / 'sample'
    folder.mkdir(parents=True)
    (folder / 'plugin.yaml').write_text(metadata, encoding='utf-8')
    states = module().read_states(Context(), tmp_path)
    assert all(state.installed is None for state in states.values())
    assert all(state.enabled is False for state in states.values())


def test_unreadable_inventory_preserves_positive_runtime_evidence(tmp_path, monkeypatch):
    from axiom_agent import files
    (tmp_path / 'plugins').mkdir()
    def denied(*args, **kwargs):
        raise PermissionError('private error')
    monkeypatch.setattr(files.os, 'scandir', denied)
    states = module().read_states(Context({'tripwire'}), tmp_path)
    assert states['tripwire'].installed is True
    assert states['tripwire'].enabled is True
    assert states['standing'].installed is None
