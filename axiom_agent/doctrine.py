"""Read the shipped doctrine without maintaining a second wording source."""
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Article:
    number: str
    title: str
    text: str

    @property
    def heading(self) -> str:
        return f'{self.number}. {self.title}'

    @property
    def enforcers(self) -> tuple[str, ...]:
        line = next(line for line in self.text.splitlines() if line.startswith('*Enforced by:'))
        return tuple(re.findall(r'hermes-[a-z-]+|standing|tripwire|handydandy', line))

    @property
    def excerpt(self) -> str:
        body = self.text.split('\n', 1)[1].split('*Enforced by:', 1)[0]
        body = ' '.join(body.split())
        sentences = re.split(r'(?<=\.)\s+', body)
        # Sentence positions select rules, not introductory observations. All wording
        # remains in the shipped source; only the gate's bold action labels are joined.
        selection = {'I': (0, 3), 'II': (1,), 'III': (1,), 'IV': (0,),
                     'V': (1, 2), 'VI': (0,), 'VII': (1,), 'VIII': (0, 1), 'IX': (0, 1)}
        excerpt = ' '.join(sentences[i] for i in selection[self.number])
        if self.number == 'III':
            excerpt = '/'.join(re.findall(r'\*\*(.+?)\*\*', body)) + '. ' + excerpt
        return excerpt


@dataclass(frozen=True)
class Doctrine:
    text: str
    axiom: str
    articles: tuple[Article, ...]


def load_doctrine() -> Doctrine:
    text = Path(__file__).with_name('DOCTRINE.md').read_text(encoding='utf-8')
    matches = list(re.finditer(r'^## ([IVX]+)\. (.+)$', text, re.M))
    articles = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else text.index('\n---', match.end())
        articles.append(Article(match[1], match[2], text[match.start():end].rstrip()))
    axiom = re.search(r'^> (.+)$', text, re.M)[1]
    return Doctrine(text, axiom, tuple(articles))


FOOTER = 'This plugin enforces nothing itself; ENFORCED means an enforcer is loaded and enabled, not verified coverage.'
COMPACT_CAP = 1800
FULL_CAP = 4000


def article_state(article: Article, active: set[str]) -> str:
    names = [name for name in article.enforcers if name in active]
    return f"ENFORCED ({', '.join(names)})" if names else 'ADVISED'


def compact_context(doctrine: Doctrine, active: set[str]) -> str:
    lines = [doctrine.axiom]
    for article in doctrine.articles:
        lines.extend((f'{article.heading}: {article.excerpt}', article_state(article, active)))
    lines.append(FOOTER)
    return '\n'.join(lines)
