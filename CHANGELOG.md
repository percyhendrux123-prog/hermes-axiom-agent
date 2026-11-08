# Changelog

## 0.1.0

- Ship the nine-article Axiom Doctrine, with compact or full per-turn context.
- Add `/doctrine`, `/doctrine show [n]` and `/doctrine plugins`.
- Report loaded, enabled enforcers separately from advice-only articles.
- Read optional owner additions with a separate injection cap.
- Register no tools, approval hooks or middleware; perform no writes or external calls.
- Declare no Python dependencies; inside Hermes, manifest metadata is parsed with the core `hermes_yaml` loader.
- Read files without following symlinks below HERMES_HOME (plugin directory symlinks excepted), check every read on the opened descriptor, refuse YAML anchors/aliases/merge keys before parsing, and bound inventory work.
- Close every directory descriptor on failure paths; count inventory entries while scanning; match YAML anchors only where a node can start; degrade to unknown on platforms without POSIX descriptor support (catalog: macOS, Linux).
