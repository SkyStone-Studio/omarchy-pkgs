# omp-collector

An [omarchy](https://omarchy.org/) usage collector for [omp (Oh My Pi)](https://omp.sh).
Lets the `omarchy.agents` bar widget display token usage, per-day spend, and
per-model breakdowns for everything routed through omp — without depending on
the upstream provider.

## Why

omarchy's `omarchy.agents` panel picks up `omarchy-agent-usage-<id>` collectors
from `$OMARCHY_PATH/bin/` and renders one tab per JSON record in
`~/.local/state/omarchy/agents/usage/`. Out of the box only `claude`, `codex`,
and `fireworks` ship collectors. omp is a multi-provider harness — it can drive
Anthropic, OpenAI, OpenRouter, Fireworks, or any local model — so a single
"omp" record that aggregates every assistant message across providers is the
right shape for it.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Panel.Main.qml (omarchy.agents)                                 │
│   watches ~/.local/state/omarchy/agents/usage/*.json            │
└────────────────────────────┬────────────────────────────────────┘
                             │ one JSON per agent
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ omarchy-agent-usage-update (bash)                               │
│   glob $OMARCHY_PATH/bin/omarchy-agent-usage-* → fork collectors │
│   pipe stdout → jq -e . → atomic write to <id>.json             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ omarchy-agent-usage-omp  (this project)                         │
│                                                                 │
│   1. ~/.omp/agent/agent.db  →  client_usage table (preferred)    │
│      one row per (recorded_at, model) with token totals          │
│      already aggregated by omp itself                            │
│                                                                 │
│   2. ~/.omp/agent/sessions/**/*.jsonl  (fallback)               │
│      walk every assistant message, sum input/output/cacheRead/   │
│      cacheWrite, bucket by local day and model                   │
│                                                                 │
│   3. cache at $XDG_CACHE_HOME/omarchy/agent-usage/omp-scan-*.json│
│      scanDate-gated; --force or stale → rescan                  │
└─────────────────────────────────────────────────────────────────┘
```

Output is one JSON record on stdout matching the panel's contract (see
[`tests/test_contract.py`](tests/test_contract.py) for the field list).

## Repository layout

```
omp-collector/
├── README.md
├── LICENSE
├── Makefile
├── omarchy-agent-usage-omp    # the script (source of truth)
└── tests/
    └── test_contract.py       # panel-contract smoke test
```

The collector is a single executable Python 3 script with no third-party
dependencies. It carries its own `pyproject.toml`-equivalent metadata in the
shebang-line comments (`omarchy:summary`, `omarchy:args`, `omarchy:hidden`),
which is what `omarchy commands --markdown` parses to render the docs.

## Install

The collector ships as the `omarchy-agent-usage-omp` pacman package from the
[omarchy-pkgs](https://skystone-studio.github.io/omarchy-pkgs) repository. It
installs `/usr/bin/omarchy-agent-usage-omp` plus the
`/usr/share/omarchy/bin/omarchy-agent-usage-omp` symlink that
`omarchy-agent-usage-update` globs, matching the claude, codex, and fireworks
collectors.

```bash
sudo pacman -S omarchy-agent-usage-omp
omarchy agent usage-update --force omp  # regenerate ~/.local/state/omarchy/agents/usage/omp.json
omarchy restart shell                   # optional — forces the panel to rescan
```

If the script was previously copied into `/usr/share/omarchy/bin/` by hand,
remove that unowned file first (`sudo rm /usr/share/omarchy/bin/omarchy-agent-usage-omp`);
pacman will not replace it, or pass `--overwrite` once.

After the panel rescan, the bar shows an "omp" tab alongside claude / codex /
fireworks. The widget's subscription switch (`h`/`l`) appears only when more
than one enabled agent has recorded usage.

### Disabling other collectors

The widget renders every enabled provider whose record file exists. To hide
e.g. claude so the omp tab is the only one shown:

```bash
omarchy bar set omarchy.agents providers \
  '{"claude":{"enabled":false},"codex":{"enabled":false},"fireworks":{"enabled":false},"omp":{"enabled":true}}' \
  --json
```

## Test

```bash
make test
```

The contract test runs the collector three ways:

1. `--force` against the real `~/.omp` tree — asserts a populated record with
   non-empty `modelUsage` and `activeDates`.
2. `--limits-only` — exercises the cache fast path (the second run within 15
   minutes reads from `~/.cache/omarchy/agent-usage/omp-scan-*.json`).
3. `--force --session-dir /nonexistent/...` — verifies the empty-state
   fallback: `ready: false`, zero counts, no crash.

Every assertion enforces a field that the panel reads off the record. Adding
a field to the collector without updating the test means the test does not
catch drift; updating the test without the matching panel change means the
widget breaks. Keep them in sync.

## Develop

The collector is short enough to read end-to-end. Sections, in order:

| Section | What it does |
|---|---|
| `empty_stats` / `add_message` | One-shot aggregation: a session message becomes a stats row |
| `scan_sessions` | Walk `~/.omp/agent/sessions/**/*.jsonl`, hand each assistant message to `add_message` |
| `read_client_usage` | Pull pre-aggregated `(day, model)` rows from `agent.db.client_usage` if present |
| `merge_stats` | Combine session scan + DB rollups; union active dates, sum tokens |
| `finalize` | Convert internal sets/counters to JSON-safe ints and lists |
| `collect` | Cache-then-scan orchestration |
| `main` | CLI: `--force`, `--limits-only`, `--session-dir`, then print the record |

Common edits:

- **New field in the record.** Add it to `finalize()` and to the
  `REQUIRED_FIELDS` set in `tests/test_contract.py`. The panel will not see
  it until `Main.qml` / `Panel.qml` reads it; the widget's source lives in
  `/usr/share/omarchy/shell/plugins/agents/` (read-only reference).
- **Different cache TTL.** The constants `SCAN_REUSE_SECONDS` and
  `LIMITS_ONLY_REUSE_SECONDS` mirror what the claude and codex collectors use.
- **Different session root.** The collector resolves the omp root from
  `--session-dir`, then `OMP_SESSION_DIR`, then `PI_SESSION_DIR`, then
  `~/.omp`. Adjust `config_dir()` if omp's default location moves.
- **Rate limits.** Not implemented yet — omp has no single subscription, so
  `limits` is intentionally `[]`. If a future omp version exposes per-provider
  rate limits via `agent.db.usage_history`, populate the limits array in
  `main()` like the claude/codex collectors do.

## Surviving `omarchy update`

Every collector ships as a pacman package and lives in `/usr/share/omarchy/bin/`
as a symlink to `/usr/bin/omarchy-agent-usage-<id>`. This package owns that
symlink, so `omarchy update` no longer replaces the collector with a stale copy
and upgrades arrive with `pacman -Syu`.

`make install` still copies the working tree script into
`/usr/share/omarchy/bin/` for development; reinstall the package afterwards to
restore the packaged symlink.

## Adding new agents

omp is not the only one. To add another agent (say, `hermes`):

1. Copy `omarchy-agent-usage-omp` to `omarchy-agent-usage-<agent>` and edit:
   - `AGENT_ID` and `AGENT_NAME`
   - the `config_dir()` resolver
   - the scan / DB source paths
   - any provider-specific token fields
2. Update `REQUIRED_FIELDS` in `tests/test_contract.py` only if the new agent
   reports fields the others don't (the contract is shared across collectors).
3. Run `make test install record`.

The panel discovers collectors by glob, so no manifest edit is required.
Drop an `assets/<agent>.svg` into `/usr/share/omarchy/shell/plugins/agents/assets/`
if you want a custom mark; otherwise the widget uses its fallback glyph.

## License

MIT — see [`LICENSE`](LICENSE).