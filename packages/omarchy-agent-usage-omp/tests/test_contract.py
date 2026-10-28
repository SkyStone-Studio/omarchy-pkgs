#!/usr/bin/env python3
"""Smoke test for the omp collector.

Runs the collector with --force against the real ~/.omp tree, parses the
JSON, and asserts the record matches the contract the omarchy.agents panel
expects. A second pass with --limits-only exercises the cached fast path.
A third pass against a non-existent session dir verifies the empty-state
fallback (ready: false, no crash).

Exits 0 on pass, non-zero on the first failed assertion with a diff that
names the field that broke.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTOR = REPO_ROOT / "omarchy-agent-usage-omp"

# Fields the panel reads from every record. Mirrors the omarchy-agent-usage-*
# contract: missing fields would leave sections blank, extra fields would be
# silently dropped. Both directions matter for forward compatibility.
REQUIRED_FIELDS = {
    "schemaVersion",
    "id",
    "name",
    "updatedAt",
    "ready",
    "hasLocalStats",
    "tierLabel",
    "usageStatusText",
    "authHelpText",
    "limits",
    "todayPrompts",
    "todaySessions",
    "todayTotalTokens",
    "todayTokensByModel",
    "recentDays",
    "totalPrompts",
    "totalSessions",
    "activeDays",
    "activeDates",
    "modelUsage",
}


def run(args: list[str], env: dict | None = None) -> dict:
    """Invoke the collector and return the parsed record.

    Raises AssertionError with the stderr text if the run fails or stdout
    is not valid JSON.
    """
    proc = subprocess.run(
        [str(COLLECTOR), *args],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    assert proc.returncode == 0, (
        f"collector exited {proc.returncode}\n"
        f"args={args}\nstderr={proc.stderr}"
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"collector produced non-JSON output\nargs={args}\nstdout={proc.stdout!r}\nstderr={proc.stderr}"
        ) from exc


def assert_contract(record: dict, *, expected_ready: bool) -> None:
    missing = REQUIRED_FIELDS - record.keys()
    assert not missing, f"missing required fields: {sorted(missing)}"
    assert record["id"] == "omp", f"id must be 'omp', got {record['id']!r}"
    assert record["schemaVersion"] == 1, f"schemaVersion must be 1, got {record['schemaVersion']!r}"
    assert record["ready"] is expected_ready, (
        f"ready must be {expected_ready} (data present), got {record['ready']}"
    )
    assert record["hasLocalStats"] is True
    assert record["limits"] == [], "omp has no subscription of its own; limits must be empty"
    assert isinstance(record["todayPrompts"], int)
    assert isinstance(record["todaySessions"], int)
    assert isinstance(record["todayTotalTokens"], int)
    assert isinstance(record["totalPrompts"], int)
    assert isinstance(record["totalSessions"], int)
    assert isinstance(record["activeDays"], int)
    assert isinstance(record["activeDates"], list)
    assert isinstance(record["todayTokensByModel"], dict)
    assert isinstance(record["modelUsage"], dict)
    assert all(isinstance(v, int) for v in record["todayTokensByModel"].values())
    for model, bucket in record["modelUsage"].items():
        assert isinstance(model, str) and model
        assert isinstance(bucket, dict)
        for key in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"):
            assert isinstance(bucket.get(key, 0), int), (
                f"model {model!r} bucket {key!r} must be int, got {bucket.get(key)!r}"
            )
    assert isinstance(record["recentDays"], list)
    assert record["recentDays"], "recentDays must be non-empty (panel renders nothing without it)"
    for day in record["recentDays"]:
        assert set(day.keys()) == {"date", "messageCount"}, f"recentDays entry keys: {sorted(day.keys())}"
        assert isinstance(day["date"], str)
        assert isinstance(day["messageCount"], int)


def test_real_data() -> None:
    """The real ~/.omp tree should produce a populated record."""
    record = run(["--force"])
    assert_contract(record, expected_ready=True)
    assert record["totalPrompts"] > 0
    assert record["totalSessions"] > 0
    assert record["activeDays"] > 0
    assert record["modelUsage"], "expected at least one model in modelUsage"


def test_limits_only_cached_path() -> None:
    """--limits-only reuses a recent scan; output must still satisfy the contract."""
    record = run(["--limits-only"])
    assert_contract(record, expected_ready=True)


def test_empty_state() -> None:
    """Pointing at a non-existent session dir must produce a clean empty record."""
    record = run(["--force", "--session-dir", "/nonexistent/omp-root-for-test"])
    assert_contract(record, expected_ready=False)
    assert record["totalPrompts"] == 0
    assert record["totalSessions"] == 0
    assert record["activeDays"] == 0
    assert record["todayTotalTokens"] == 0
    assert record["modelUsage"] == {}


def main() -> int:
    tests = [test_real_data, test_limits_only_cached_path, test_empty_state]
    failures = []
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as exc:
            failures.append((test.__name__, exc))
            print(f"FAIL  {test.__name__}: {exc}")
    if failures:
        print(f"\n{len(failures)}/{len(tests)} failed")
        return 1
    print(f"\n{len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())