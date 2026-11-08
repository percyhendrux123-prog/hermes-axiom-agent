"""The read-only /doctrine command and context callback."""
from .context import build_context, owner_additions
from .doctrine import FOOTER, article_state, load_doctrine
from .state import read_states


USAGE = 'Usage: /doctrine [status | show [1-9 or I-IX] | plugins]'


class DoctrineService:
    def __init__(self, ctx, home):
        self.ctx = ctx
        self.home = home
        self.doctrine = load_doctrine()

    def before(self, **kwargs):
        try:
            inject = self.ctx.get_config('inject', default=True)
            form = self.ctx.get_config('form', default='compact')
        except Exception:
            return None
        if inject is not True or form not in ('compact', 'full'):
            return None
        home = self.home()
        states = read_states(self.ctx, home)
        active = {name for name, state in states.items() if state.enabled is True}
        return {'context': build_context(self.doctrine, active, home, form)}

    def command(self, raw='', **kwargs) -> str:
        if not isinstance(raw, str):
            return USAGE
        args = raw.split()
        if not args:
            args = ['status']
        if args == ['show']:
            return self.doctrine.text + owner_additions(self.home())
        if len(args) == 2 and args[0] == 'show':
            for index, article in enumerate(self.doctrine.articles, 1):
                if args[1] in (str(index), article.number):
                    return article.text
            return USAGE
        if args not in (['status'], ['plugins']):
            return USAGE
        states = read_states(self.ctx, self.home())
        active = {name for name, state in states.items() if state.enabled is True}
        if args == ['status']:
            rows = ['No. | Article | Enforcer(s) | State']
            count = 0
            for article in self.doctrine.articles:
                names = ', '.join(article.enforcers) or 'none (doctrine only)'
                state = article_state(article, active)
                count += bool(set(article.enforcers) & active)
                rows.append(f'{article.number} | {article.title} | {names} | {state}')
            rows.extend((FOOTER, f'{count} of 9 enforced on this install'))
        else:
            rows = ['Plugin | Installed | Enabled']
            for name, state in states.items():
                installed = {True: 'yes', False: 'not found', None: 'unknown'}[state.installed]
                enabled = {True: 'yes', False: 'no', None: 'unknown'}[state.enabled]
                rows.append(f'{name} | {installed} | {enabled}')
                if state.installed is False:
                    rows.append(f'  hermes plugins install {name}')
            rows.extend(('Installed checks cover user-plugin manifests; inactive bundled/pip installs may not be found.', FOOTER))
        if any(state.enabled is None for state in states.values()):
            rows.insert(0, 'Runtime plugin state unavailable; unknown enforcers are treated as ADVISED.')
        return '\n'.join(rows)
