import importlib
from itertools import product
from types import SimpleNamespace

import pytest

NAMES = ('standing', 'hermes-axioma', 'tripwire', 'handydandy', 'hermes-gatekeeper')
EXPECTED = ((), (), ('hermes-axioma', 'hermes-gatekeeper'), ('standing',),
            ('standing',), ('tripwire',), ('handydandy',), ('hermes-gatekeeper',), ())


def module():
    return importlib.import_module('axiom_agent.service')


class Context:
    def __init__(self, **settings):
        self.settings = settings

    def get_config(self, key, default=None):
        return self.settings.get(key, default)


def service(tmp_path, monkeypatch, active=(), **settings):
    api = module()
    states = {name: SimpleNamespace(installed=name in active, enabled=name in active) for name in NAMES}
    monkeypatch.setattr(api, 'read_states', lambda ctx, home: states)
    return api.DoctrineService(Context(**settings), lambda: tmp_path)


@pytest.mark.parametrize('flags', list(product((False, True), repeat=5)))
def test_status_table_for_every_enforcer_combination(tmp_path, monkeypatch, flags):
    active = {name for name, enabled in zip(NAMES, flags) if enabled}
    report = service(tmp_path, monkeypatch, active).command('')
    rows = [line for line in report.splitlines() if ' | ' in line][1:]
    assert len(rows) == 9
    count = 0
    for row, enforcers in zip(rows, EXPECTED):
        state = row.split(' | ')[-1]
        available = set(enforcers) & active
        assert state.startswith('ENFORCED' if available else 'ADVISED')
        assert all(name in state for name in available)
        count += bool(available)
    assert report.endswith(f'{count} of 9 enforced on this install')
    assert 'enforces nothing itself' in report


def test_gate_lists_only_the_enabled_enforcer_in_the_state(tmp_path, monkeypatch):
    report = service(tmp_path, monkeypatch, {'hermes-gatekeeper'}).command('status')
    row = next(line for line in report.splitlines() if line.startswith('III |'))
    assert row.endswith('ENFORCED (hermes-gatekeeper)')
    assert 'hermes-axioma' in row.split(' | ')[2]


@pytest.mark.parametrize('number', range(1, 10))
def test_show_one_article_accepts_number_and_roman(tmp_path, monkeypatch, number):
    from axiom_agent.doctrine import load_doctrine
    selected = load_doctrine().articles[number - 1]
    app = service(tmp_path, monkeypatch)
    assert app.command(f'show {number}') == selected.text
    assert app.command(f'show {selected.number}') == selected.text


def test_show_full_includes_unchanged_source_and_owner_additions(tmp_path, monkeypatch):
    from axiom_agent.doctrine import load_doctrine
    path = tmp_path / 'axiom-agent' / 'doctrine.local.md'
    path.parent.mkdir()
    owner = '## X. Review\nCheck the result.\n'
    path.write_text(owner, encoding='utf-8')
    output = service(tmp_path, monkeypatch).command('show')
    assert output.startswith(load_doctrine().text)
    assert owner in output


@pytest.mark.parametrize('raw', ['bad', 'status extra', 'plugins extra', 'show 0', 'show 10',
                                 'show -1', 'show 1.0', 'show ../x', 'show II extra', 'show "2"', None, 12])
def test_bad_args_return_usage_without_reading_state(tmp_path, monkeypatch, raw):
    app = service(tmp_path, monkeypatch)
    monkeypatch.setattr(module(), 'read_states', lambda *args: pytest.fail('unexpected state read'))
    assert app.command(raw).startswith('Usage: /doctrine')


def test_plugins_lists_state_and_install_line_for_missing_only(tmp_path, monkeypatch):
    app = service(tmp_path, monkeypatch, {'standing', 'tripwire'})
    report = app.command('plugins')
    for name in NAMES:
        assert name in report
        if name not in {'standing', 'tripwire'}:
            assert f'hermes plugins install {name}' in report
        else:
            assert f'hermes plugins install {name}' not in report
    assert 'enforces nothing itself' in report


def test_inject_off_does_not_read_home_state_or_owner_file(tmp_path, monkeypatch):
    app = service(tmp_path, monkeypatch, inject=False)
    app.home = lambda: pytest.fail('unexpected home lookup')
    monkeypatch.setattr(module(), 'read_states', lambda *args: pytest.fail('unexpected read'))
    assert app.before(session_id='demo', future_field=True) is None


@pytest.mark.parametrize('form,cap', [('compact', 1800), ('full', 4000)])
def test_injection_uses_current_settings_and_runtime_states(tmp_path, monkeypatch, form, cap):
    app = service(tmp_path, monkeypatch, {'standing'}, form=form)
    result = app.before(user_message='untrusted content', future_field=True)
    assert set(result) == {'context'}
    assert len(result['context']) <= cap
    assert 'ENFORCED (standing)' in result['context']
    assert 'untrusted content' not in result['context']
    app.ctx.settings['inject'] = False
    assert app.before() is None


@pytest.mark.parametrize('settings', [{'inject': 'false'}, {'inject': 0}, {'form': 'other'}, {'form': None}])
def test_invalid_settings_disable_injection_without_blocking(tmp_path, monkeypatch, settings):
    assert service(tmp_path, monkeypatch, **settings).before() is None


def test_config_read_failure_skips_injection(tmp_path, monkeypatch):
    app = service(tmp_path, monkeypatch)
    def broken(*args, **kwargs):
        raise RuntimeError('private diagnostic')
    app.ctx.get_config = broken
    assert app.before() is None


def test_injection_default_is_compact_and_enabled(tmp_path, monkeypatch):
    app = service(tmp_path, monkeypatch)
    assert app.before()['context'].startswith(app.doctrine.axiom)
    assert not app.before()['context'].startswith('#')


def test_unknown_state_never_counts_as_enforced(tmp_path, monkeypatch):
    app = service(tmp_path, monkeypatch)
    monkeypatch.setattr(module(), 'read_states', lambda *args: {
        name: SimpleNamespace(installed=None, enabled=None) for name in NAMES})
    assert app.command('status').endswith('0 of 9 enforced on this install')
    assert 'ADVISED' in app.command('status')
    report = app.command('plugins')
    assert 'standing | unknown | unknown' in report
    assert 'hermes plugins install' not in report
