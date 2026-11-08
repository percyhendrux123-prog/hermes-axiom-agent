"""Runtime probes plus read-only user-plugin manifest inventory; no code imports."""
from dataclasses import dataclass
from pathlib import Path
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
# They can only start a node: at a line start, after "key:", "- " or "? ", or inside a flow
# collection. Quoted scalars and comments are blanked first so prose like *markdown* passes.
_QUOTED_OR_COMMENT = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\n]|\'\')*\'|(?:^|(?<=\s))#[^\n]*', re.M)
_EXPANSION = re.compile(r'(?:^[ \t]*|[:?-][ \t]+|[\[{,][ \t]*)(?:[&*]\S|<<[ \t]*:)', re.M)


class _OverBudget(Exception):
    pass


@dataclass(frozen=True)
class PluginState:
    installed: bool | None
    enabled: bool | None


def _within_budget(text: str) -> bool:
    plain = _QUOTED_OR_COMMENT.sub('""', text)
    return not _EXPANSION.search(plain) and plain.count('[') + plain.count('{') <= FLOW_CAP


def _manifest_name(folder: int) -> str | None:
    """Name from plugin.yaml/plugin.yml in *folder*; None when it has neither."""
    for filename in ('plugin.yaml', 'plugin.yml'):
        try:
            text = files.read_text(folder, filename, METADATA_CAP)
        except FileNotFoundError:
            continue
        if len(text) > METADATA_CAP:
            raise ValueError('Oversized metadata')
        if not _within_budget(text):
            raise ValueError('Metadata outside the parsing budget')
        data = yaml.safe_load(text)
        if not isinstance(data, dict) or not isinstance(data.get('name'), str):
            raise ValueError('Invalid metadata')
        return data['name']
    return None


def _installed(home: Path) -> tuple[set[str], bool]:
    """Directory symlinks are followed (a symlinked checkout is a normal plugin install);
    manifest files are never followed, and every read is checked on the opened descriptor.
    Every descriptor opened here is closed on every path, including failures."""
    found = set()
    complete = True
    budget = [ENTRY_CAP]

    def listing(fd: int) -> list[str]:
        names = files.entries(fd, budget[0])
        budget[0] -= len(names)
        if budget[0] < 0:
            raise _OverBudget
        return sorted(names)

    def subdir(name: str, parent: int) -> int | None:
        try:
            return files.open_dir(name, parent, follow=True)
        except (FileNotFoundError, files.NotRegular):
            return None  # stray files and dangling links are not plugins

    root = plugins = None
    try:
        try:
            root = files.open_dir(home, follow=True)
            plugins = files.open_dir('plugins', root, follow=True)
            names = listing(plugins)
        except FileNotFoundError:
            return found, True
        except (OSError, ValueError):
            return found, False
        for entry in names:
            try:
                folder = subdir(entry, plugins)
            except OSError:
                complete = False
                continue
            if folder is None:
                continue
            try:
                name = _manifest_name(folder)
                if name is not None:
                    found.add(name)
                    continue
                for child in listing(folder):  # one category level
                    nested = subdir(child, folder)
                    if nested is None:
                        continue
                    try:
                        name = _manifest_name(nested)
                    finally:
                        files.close(nested)
                    if name is not None:
                        found.add(name)
            except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError, OverflowError):
                complete = False
            finally:
                files.close(folder)
    except _OverBudget:
        return found, False
    finally:
        files.close(plugins)
        files.close(root)
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
