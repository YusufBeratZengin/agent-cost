# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Reject non-finite prices and report numeric conversion overflow as a price error.
- Treat non-finite token counts as zero so remaining log records can still be reported.

## [0.1.0] - 2026-10-23

### Added
- CLI and library that turn local agent session logs (JSONL) into token and estimated cost reports.
- Readers: Claude Code project sessions and generic OpenAI-style usage lines, with a small plugin registry.
- Grouping by day, session, project and model (combinable); `--since`, `--until`, `--project` and `--model` filters.
- User supplied price tables in TOML or JSON; the built-in table holds example values only.
- Table, CSV and JSON output.

[Unreleased]: https://github.com/YusufBeratZengin/agent-cost/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YusufBeratZengin/agent-cost/releases/tag/v0.1.0
