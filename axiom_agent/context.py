"""Bounded context and optional, owner-authored additions."""
from pathlib import Path
import stat

from .doctrine import COMPACT_CAP, FULL_CAP, FOOTER, Doctrine, article_state, compact_context


OWNER_CAP = 800


def capped(text: str, cap: int, note: str) -> str:
    if len(text) <= cap:
        return text
    return text[:cap - len(note)] + note


def owner_additions(home: Path, cap: int | None = None) -> str:
    path = home / 'axiom-agent' / 'doctrine.local.md'
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('Non-regular additions')
        with path.open(encoding='utf-8') as source:
            text = source.read(cap + 1) if cap is not None else source.read()
    except FileNotFoundError:
        return ''
    except (OSError, UnicodeError, ValueError):
        return '\n[Owner additions unavailable: unreadable file.]'
    if not text:
        return ''
    text = '\nOwner additions:\n' + text
    return capped(text, cap, '\n[Owner additions truncated.]') if cap is not None else text


def build_context(doctrine: Doctrine, active: set[str], home: Path, form: str) -> str:
    if form == 'full':
        states = '\n'.join(f'{article.number}: {article_state(article, active)}'
                           for article in doctrine.articles)
        base = doctrine.text + '\nInstall state:\n' + states + '\n' + FOOTER
        cap = FULL_CAP
    else:
        base, cap = compact_context(doctrine, active), COMPACT_CAP
    base = capped(base, cap, '\n[Doctrine truncated; /doctrine show for full text.]')
    return base + owner_additions(home, cap=OWNER_CAP)
