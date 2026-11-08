import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[1]


class Context:
    def __init__(self):
        self.hooks = {}
        self.commands = {}
        self.settings = {}
        self.active = set()

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def register_command(self, name, handler, **metadata):
        self.commands[name] = handler

    def get_config(self, name, default=None):
        return self.settings.get(name, default)

    def has_plugin(self, name):
        return name in self.active


def load_plugin(monkeypatch, home):
    # Host shim lives in tests only; production always uses the canonical helper.
    constants = ModuleType('hermes_constants')
    constants.get_hermes_home = home
    monkeypatch.setitem(sys.modules, 'hermes_constants', constants)
    spec = importlib.util.spec_from_file_location('sample_plugin', ROOT / '__init__.py',
                                                 submodule_search_locations=[str(ROOT)])
    plugin = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, 'sample_plugin', plugin)
    spec.loader.exec_module(plugin)
    ctx = Context()
    plugin.register(ctx)
    return ctx


def test_register_declares_only_context_hook_and_read_only_command(tmp_path, monkeypatch):
    ctx = load_plugin(monkeypatch, lambda: tmp_path)
    manifest = yaml.safe_load((ROOT / 'plugin.yaml').read_text(encoding='utf-8'))
    assert manifest['name'] == 'hermes-axiom-agent'
    assert manifest['title'] == 'Axiom Agent'
    assert manifest['version'] == '0.1.0'
    assert manifest['provides_tools'] == []
    assert manifest['provides_hooks'] == list(ctx.hooks) == ['pre_llm_call']
    assert list(ctx.commands) == ['doctrine']
    assert manifest['config_schema']['inject']['default'] is True
    assert manifest['config_schema']['form']['default'] == 'compact'
    assert set(ctx.hooks['pre_llm_call'](future_field=True)) == {'context'}
    assert ctx.commands['doctrine']('', future_field=True).endswith('0 of 9 enforced on this install')
    assert list(tmp_path.iterdir()) == []


def test_canonical_home_is_dynamic_and_not_an_environment_guess(tmp_path, monkeypatch):
    selected = [tmp_path / 'first']
    second = tmp_path / 'second'
    path = second / 'axiom-agent' / 'doctrine.local.md'
    path.parent.mkdir(parents=True)
    path.write_text('## X. Review\nOwner-added rule.\n', encoding='utf-8')
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'unrelated'))
    ctx = load_plugin(monkeypatch, lambda: selected[0])
    assert 'Owner-added rule.' not in ctx.commands['doctrine']('show')
    selected[0] = second
    assert 'Owner-added rule.' in ctx.commands['doctrine']('show')
    assert 'Owner-added rule.' in ctx.hooks['pre_llm_call']()['context']
    monkeypatch.delenv('HERMES_HOME')
    assert 'Owner-added rule.' in ctx.commands['doctrine']('show')


def test_public_runtime_state_is_refreshed_for_each_turn(tmp_path, monkeypatch):
    ctx = load_plugin(monkeypatch, lambda: tmp_path)
    assert 'ENFORCED' not in ctx.hooks['pre_llm_call']()['context'].split('This plugin')[0]
    ctx.active.add('hermes-standing')
    assert ctx.commands['doctrine']('').endswith('2 of 9 enforced on this install')
    assert 'ENFORCED (standing)' in ctx.hooks['pre_llm_call']()['context']
    ctx.active.clear()
    assert ctx.commands['doctrine']('').endswith('0 of 9 enforced on this install')
