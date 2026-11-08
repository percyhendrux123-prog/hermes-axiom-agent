"""Regression gates for the plugin's narrow runtime surface and public package."""
import ast
from itertools import product
from pathlib import Path
import re

import yaml

from axiom_agent.context import build_context
from axiom_agent.doctrine import load_doctrine

ROOT = Path(__file__).resolve().parents[1]


def test_context_caps_and_article_parity_for_every_runtime_combination(tmp_path):
    doctrine = load_doctrine()
    enforcers = sorted({name for article in doctrine.articles for name in article.enforcers})
    for flags in product((False, True), repeat=len(enforcers)):
        active = {name for name, enabled in zip(enforcers, flags) if enabled}
        for form, cap in (('compact', 1800), ('full', 4000)):
            text = build_context(doctrine, active, tmp_path, form)
            assert len(text) <= cap
            assert all(article.heading in text for article in doctrine.articles)
            assert text.count('ENFORCED (') == sum(bool(set(article.enforcers) & active)
                                                  for article in doctrine.articles)


def test_runtime_imports_and_operations_stay_read_only():
    allowed_imports = {'dataclasses', 'pathlib', 're', 'stat', 'yaml', 'hermes_constants'}
    forbidden_calls = {'write_text', 'write_bytes', 'mkdir', 'unlink', 'rename', 'replace',
                       'register_tool', 'register_middleware', 'set_config', 'dispatch_tool',
                       'system', 'popen', 'eval', 'exec'}
    files = [ROOT / '__init__.py', *sorted((ROOT / 'axiom_agent').glob('*.py'))]
    for path in files:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(name.name in allowed_imports for name in node.names), path.name
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                assert node.module in allowed_imports, path.name
            elif isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
                assert name not in forbidden_calls, (path.name, name)
                if name == 'open':
                    assert all(keyword.arg != 'mode' or keyword.value.value == 'r' for keyword in node.keywords)


def test_catalog_is_a_draft_with_only_the_registered_capabilities():
    entry = yaml.safe_load((ROOT / 'CATALOG-ENTRY.yaml').read_text(encoding='utf-8'))
    manifest = yaml.safe_load((ROOT / 'plugin.yaml').read_text(encoding='utf-8'))
    assert entry['sha'] == 'TBD' or re.fullmatch('[0-9a-f]{40}', entry['sha'])
    assert entry['maintainer'] == 'percyhendrux123-prog'
    assert entry['name'] == manifest['name']
    assert entry['version'] == manifest['version'] == '0.1.0'
    assert 'enforces nothing itself' in entry['description'].lower()
    assert entry['capabilities'] == {'provides_tools': [], 'provides_hooks': ['pre_llm_call'],
                                     'provides_middleware': [], 'requires_env': []}


def test_readme_sample_is_the_real_zero_enforcer_report(tmp_path):
    from axiom_agent.service import DoctrineService
    class Context:
        def has_plugin(self, name):
            return False
    sample = re.search(r'```text\n(.+?)\n```', (ROOT / 'README.md').read_text(encoding='utf-8'), re.S)[1]
    assert sample == DoctrineService(Context(), lambda: tmp_path).command('')


def test_public_tree_does_not_include_build_scaffold():
    assert not (ROOT / 'SPEC.md').exists()
    assert not (ROOT / 'hermes-ref').exists()
