# Changelog

## 0.1.0

- Ship the nine-article Axiom Doctrine, with compact or full per-turn context.
- Add `/doctrine`, `/doctrine show [n]` and `/doctrine plugins`.
- Report loaded, enabled enforcers separately from advice-only articles.
- Read optional owner additions with a separate injection cap.
- Register no tools, approval hooks or middleware; perform no writes or external calls.
- Declare no Python dependencies; read only each plugin manifest's top-level `name:` line, never a full YAML document.
- Read files without following symlinks below HERMES_HOME (plugin directory symlinks excepted), check each read on the opened descriptor, close every descriptor on every path, and bound inventory work.
- Support macOS and Linux; where POSIX descriptor support is missing, report owner additions unavailable and installed state unknown.
