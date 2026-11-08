"""Axiom Agent: doctrine context and a read-only /doctrine report."""


def register(ctx):
    from hermes_constants import get_hermes_home
    from .axiom_agent.service import DoctrineService

    service = DoctrineService(ctx, get_hermes_home)
    ctx.register_hook('pre_llm_call', service.before)
    ctx.register_command('doctrine', service.command,
                         description='Show doctrine articles and which enforcers are enabled.',
                         args_hint='[status | show [n] | plugins]')
