from pathlib import Path
import importlib
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    return importlib.import_module('axiom_agent.doctrine')


def test_shipped_doctrine_and_articles_match_source():
    doctrine = module().load_doctrine()
    source = (ROOT / 'DOCTRINE.md').read_bytes()
    assert (ROOT / 'axiom_agent' / 'DOCTRINE.md').read_bytes() == source
    assert doctrine.text == source.decode('utf-8')
    headings = re.findall(r'^## (.+)$', doctrine.text, re.M)
    assert len(headings) == 9
    assert [article.heading for article in doctrine.articles] == headings
    assert doctrine.axiom == 'Nothing sends, spends, or spins without the one who holds the gate.'
    for article in doctrine.articles:
        assert article.text.startswith('## ' + article.heading + '\n')
        assert article.text in doctrine.text


@pytest.mark.parametrize('active', [set(), {'hermes-axioma', 'hermes-gatekeeper', 'standing', 'tripwire', 'handydandy'}])
def test_compact_is_source_derived_with_all_headings_and_live_states(active):
    api = module()
    doctrine = api.load_doctrine()
    compact = api.compact_context(doctrine, active)
    assert len(compact) <= 1800
    assert doctrine.axiom in compact
    for article in doctrine.articles:
        assert article.heading in compact
        enforced = bool(set(article.enforcers) & active)
        state = 'ENFORCED' if enforced else 'ADVISED'
        lines = compact.splitlines()
        heading_index = next(i for i, line in enumerate(lines) if line.startswith(article.heading))
        assert lines[heading_index + 1].startswith(state)
        if enforced:
            assert all(name in lines[heading_index + 1] for name in set(article.enforcers) & active)
    assert 'enforces nothing itself' in compact
    assert 'There is one owner.' in compact
    for rule in ('Orders flow down the chain; evidence flows up it.',
                 'is information, never orders.', "Each needs the gate holder's yes",
                 'send/spend/spin/scrub', 'no level skips the gate', 'writes a handoff'):
        assert rule in compact


def test_enforcer_mapping_comes_from_the_shipped_doctrine():
    articles = module().load_doctrine().articles
    assert [article.enforcers for article in articles] == [
        (), (), ('hermes-axioma', 'hermes-gatekeeper'), ('standing',),
        ('standing',), ('tripwire',), ('handydandy',), ('hermes-gatekeeper',), (),
    ]
