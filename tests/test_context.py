import importlib
from pathlib import Path

import pytest


def module():
    return importlib.import_module('axiom_agent.context')


def test_owner_additions_are_optional_and_never_create_a_directory(tmp_path):
    assert module().owner_additions(tmp_path) == ''
    assert list(tmp_path.iterdir()) == []


def test_owner_additions_preserve_text_for_show_and_cap_context(tmp_path):
    path = tmp_path / 'axiom-agent' / 'doctrine.local.md'
    path.parent.mkdir()
    text = '## X. Local review\nShow evidence before sharing.\n'
    path.write_text(text, encoding='utf-8')
    assert module().owner_additions(tmp_path) == '\nOwner additions:\n' + text
    assert module().owner_additions(tmp_path, cap=800) == '\nOwner additions:\n' + text


@pytest.mark.parametrize('text', ['a' * 10000, '試' * 10000])
def test_oversized_owner_file_has_a_separate_cap_including_note(tmp_path, text):
    path = tmp_path / 'axiom-agent' / 'doctrine.local.md'
    path.parent.mkdir()
    path.write_text(text, encoding='utf-8')
    additions = module().owner_additions(tmp_path, cap=800)
    assert len(additions) == 800
    assert additions.endswith('[Owner additions truncated.]')


def test_unreadable_owner_file_does_not_echo_private_errors(tmp_path, monkeypatch):
    path = tmp_path / 'axiom-agent' / 'doctrine.local.md'
    path.parent.mkdir()
    path.write_text('local additions', encoding='utf-8')
    def denied(*args, **kwargs):
        raise PermissionError('sensitive diagnostic')
    monkeypatch.setattr(Path, 'open', denied)
    note = module().owner_additions(tmp_path, cap=800)
    assert 'unreadable' in note
    assert 'sensitive diagnostic' not in note


@pytest.mark.parametrize('form,cap', [('compact', 1800), ('full', 4000)])
def test_context_caps_canonical_and_owner_sections_separately(tmp_path, form, cap):
    from axiom_agent.doctrine import load_doctrine
    doctrine = load_doctrine()
    path = tmp_path / 'axiom-agent' / 'doctrine.local.md'
    path.parent.mkdir()
    path.write_text('## X. Extra\n' + 'x' * 10000, encoding='utf-8')
    context = module().build_context(doctrine, set(), tmp_path, form)
    base, owner = context.split('\nOwner additions:\n', 1)
    assert len(base) <= cap
    assert len('\nOwner additions:\n' + owner) <= 800
    assert context.endswith('[Owner additions truncated.]')
    assert all(article.heading in base for article in doctrine.articles)
    if form == 'full':
        assert doctrine.text in base
        assert 'I: ADVISED' in base


def test_full_form_is_hard_capped_with_a_note(tmp_path):
    from dataclasses import replace
    from axiom_agent.doctrine import load_doctrine
    doctrine = replace(load_doctrine(), text='d' * 10000)
    context = module().build_context(doctrine, set(), tmp_path, 'full')
    assert len(context) == 4000
    assert context.endswith('[Doctrine truncated; /doctrine show for full text.]')


@pytest.mark.parametrize('raw', [b'\xff\xfe', b'\x80'])
def test_owner_invalid_utf8_is_unreadable(tmp_path, raw):
    path = tmp_path / 'axiom-agent' / 'doctrine.local.md'
    path.parent.mkdir()
    path.write_bytes(raw)
    assert 'unreadable' in module().owner_additions(tmp_path)


@pytest.mark.parametrize('kind', ['directory', 'symlink', 'fifo'])
def test_owner_nonregular_file_is_unreadable_without_opening(tmp_path, monkeypatch, kind):
    import os
    path = tmp_path / 'axiom-agent' / 'doctrine.local.md'
    path.parent.mkdir()
    if kind == 'directory':
        path.mkdir()
    elif kind == 'symlink':
        target = tmp_path / 'unrelated.md'
        target.write_text('Never inject this file.', encoding='utf-8')
        path.symlink_to(target)
    else:
        os.mkfifo(path)
    def unexpected(*args, **kwargs):
        pytest.fail('must reject before opening a special file')
    monkeypatch.setattr(Path, 'open', unexpected)
    assert 'unreadable' in module().owner_additions(tmp_path, cap=800)
