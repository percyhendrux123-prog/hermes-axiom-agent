"""Runtime probes plus read-only user-plugin manifest inventory; no code imports."""
from dataclasses import dataclass
from pathlib import Path
import os
import re

try:  # Hermes core ships a safe YAML loader; the plugin needs no extra dependency inside Hermes.
    import hermes_yaml as yaml
except ImportError:  # outside Hermes (tests, tooling)
    import yaml

from . import files


ENFORCERS = ('standing', 'hermes-axioma', 'tripwire', 'handydandy', 'hermes-gatekeeper')
ALIASES = {'standing': ('standing', 'hermes-standing')}
METADATA_CAP = 65536
ENTRY_CAP = 1024  # directory entries inspected per inventory, across both levels
FLOW_CAP = 256  # flow-collection openers allowed in one manifest
# Anchors, aliases and merge keys are the YAML features whose cost can exceed the input size.
_EXPANSION = re.compile(r'(?:^|[\s\[\]{},:])[&*][^\s,\[\]{}]|<<')


@dataclass(frozen=True)
class PluginState:
    installed: bool | None
    enabled: bool | None


def _manifest_name(folder: int) -> str | None:
    """Name from plugin.yaml/plugin.yml in *folder*; None when it has neither."""
    for filename in ('plugin.yaml', 'plugin.yml'):
        try:
            text = files.read_text(folder, filename, METADATA_CAP)
        except FileNotFoundError:
            continue
        if len(text) > METADATA_CAP:
            raise ValueError('Oversized metadata')
        if _EXPANSION.search(text) or text.count('[') + text.count('{') > FLOW_CAP:
            raise ValueError('Metadata outside the parsing budget')
        data = yaml.safe_load(text)
        if not isinstance(data, dict) or not isinstance(data.get('name'), str):
            raise ValueError('Invalid metadata')
        return data['name']
    return None


def _installed(home: Path) -> tuple[set[str], bool]:
    """Directory symlinks are followed (a symlinked checkout is a normal plugin install);
    manifest files are never followed, and every read is checked on the opened descriptor."""
    found = set()
    complete = True
    budget = ENTRY_CAP
    root = plugins = None
    try:
        root = files.open_dir(home, follow=True)
        plugins = files.open_dir('plugins', root, follow=True)
        entries = sorted(os.listdir(plugins))
    except FileNotFoundError:
        return found, True
    except (OSError, ValueError):
        return found, False
    finally:
        files.close(root)
    try:
        for entry in entries:
            budget -= 1
            if budget < 0:
                return found, False
            folder = None
            try:
                try:
                    folder = files.open_dir(entry, plugins, follow=True)
                except (FileNotFoundError, files.NotRegular):
                    continue  # stray files and dangling links are not plugins
                name = _manifest_name(folder)
                if name is not None:
                    found.add(name)
                    continue
                for child in sorted(os.listdir(folder)):  # one category level
                    budget -= 1
                    if budget < 0:
                        return found, False
                    nested = None
                    try:
                        try:
                            nested = files.open_dir(child, folder, follow=True)
                        except (FileNotFoundError, files.NotRegular):
                            continue
                        name = _manifest_name(nested)
                        if name is not None:
                            found.add(name)
                    finally:
                        files.close(nested)
            except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError, OverflowError):
                complete = False
            finally:
                files.close(folder)
    finally:
        files.close(plugins)
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
