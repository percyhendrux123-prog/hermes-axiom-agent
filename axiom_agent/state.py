"""Runtime probes plus read-only user-plugin manifest inventory; no code imports."""
from dataclasses import dataclass
from pathlib import Path
import stat

import yaml


ENFORCERS = ('standing', 'hermes-axioma', 'tripwire', 'handydandy', 'hermes-gatekeeper')
ALIASES = {'standing': ('standing', 'hermes-standing')}
METADATA_CAP = 65536


@dataclass(frozen=True)
class PluginState:
    installed: bool | None
    enabled: bool | None


def _manifest(folder: Path) -> Path | None:
    for filename in ('plugin.yaml', 'plugin.yml'):
        path = folder / filename
        try:
            mode = path.stat().st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(mode):
            raise ValueError('Non-regular metadata')
        return path
    return None


def _installed(home: Path) -> tuple[set[str], bool]:
    found = set()
    complete = True
    try:
        folders = list((home / 'plugins').iterdir())
    except FileNotFoundError:
        return found, True
    except OSError:
        return found, False
    for folder in folders:
        try:
            if not folder.is_dir():
                continue
            manifest = _manifest(folder)
            paths = [manifest] if manifest else [
                path for child in folder.iterdir() if child.is_dir()
                if (path := _manifest(child)) is not None
            ]
            for path in paths:
                with path.open(encoding='utf-8') as source:
                    text = source.read(METADATA_CAP + 1)
                if len(text) > METADATA_CAP:
                    raise ValueError('Oversized metadata')
                data = yaml.safe_load(text)
                if not isinstance(data, dict) or not isinstance(data.get('name'), str):
                    raise ValueError('Invalid metadata')
                found.add(data['name'])
        except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError, OverflowError):
            complete = False
    return found, complete


def read_states(ctx, home: Path) -> dict[str, PluginState]:
    installed, complete = _installed(home)
    states = {}
    for name in ENFORCERS:
        aliases = ALIASES.get(name, (name,))
        try:
            enabled = any(ctx.has_plugin(alias) is True for alias in aliases)
        except Exception:
            enabled = None
        present = True if enabled or any(alias in installed for alias in aliases) else (False if complete else None)
        states[name] = PluginState(present, enabled)
    return states
