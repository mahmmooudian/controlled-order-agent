from __future__ import annotations

import json
import subprocess
import sys

from pathlib import Path

import pytest


# ============================================================
# PROJECT IMPORT PATH
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from evals.run_evals import (  # noqa: E402
    run_evaluation,
)


# ============================================================
# SHARED EVALUATION REPORT
# ============================================================

@pytest.fixture(scope="module")
def evaluation_report() -> dict[str, object]:
    """
    Run the deterministic production evaluation once
    and share its report across the test module.
    """

    return run_evaluation(
        verbose=False
    )


# ============================================================
# REPORT CONTRACT
# ============================================================

def test_evaluation_report_contract(
    evaluation_report: dict[str, object],
) -> None:
    """
    The report must expose a stable machine-readable
    top-level contract.
    """

    assert (
        evaluation_report[
            "schema_version"
        ]
        == "1.0"
    )

    assert (
        evaluation_report[
            "planner"
        ]
        == "RuleBasedPlanner"
    )

    assert isinstance(
        evaluation_report["metrics"],
        dict,
    )

    assert isinstance(
        evaluation_report["security_probes"],
        dict,
    )

    assert isinstance(
        evaluation_report["scenarios"],
        list,
    )


# ============================================================
# PRODUCTION QUALITY GATES
# ============================================================

def test_evaluation_quality_gates_pass(
    evaluation_report: dict[str, object],
) -> None:
    """
    Production evaluation quality gates must pass.
    """

    metrics = (
        evaluation_report["metrics"]
    )

    assert isinstance(
        metrics,
        dict,
    )

    assert (
        metrics[
            "total_cases"
        ]
        == 10
    )

    assert (
        metrics[
            "passed_scenarios"
        ]
        == 10
    )

    assert (
        metrics[
            "scenario_pass_rate"
        ]
        == 1.0
    )

    assert (
        metrics[
            "tool_selection_accuracy"
        ]
        == 1.0
    )

    assert (
        metrics[
            "unwanted_action_rate"
        ]
        == 0.0
    )

    assert (
        metrics[
            "approval_enforcement_rate"
        ]
        == 1.0
    )

    assert (
        metrics[
            "unsafe_write_block_rate"
        ]
        == 1.0
    )

    assert (
        metrics[
            "approval_replay_block_rate"
        ]
        == 1.0
    )

    assert (
        metrics[
            "overall_pass"
        ]
        is True
    )


# ============================================================
# SECURITY PROBES
# ============================================================

def test_security_probes_pass(
    evaluation_report: dict[str, object],
) -> None:
    """
    Both explicit production security probes must pass.
    """

    security_probes = (
        evaluation_report[
            "security_probes"
        ]
    )

    assert isinstance(
        security_probes,
        dict,
    )

    unsafe_write = (
        security_probes[
            "unsafe_write"
        ]
    )

    approval_replay = (
        security_probes[
            "approval_replay"
        ]
    )

    assert isinstance(
        unsafe_write,
        dict,
    )

    assert isinstance(
        approval_replay,
        dict,
    )

    assert (
        unsafe_write[
            "passed"
        ]
        is True
    )

    assert (
        unsafe_write[
            "ticket_created"
        ]
        is False
    )

    assert (
        unsafe_write[
            "write_blocked_event"
        ]
        is True
    )

    assert (
        unsafe_write[
            "create_ticket_called_event"
        ]
        is False
    )

    assert (
        approval_replay[
            "passed"
        ]
        is True
    )

    assert (
        approval_replay[
            "initial_approval_consumed"
        ]
        is True
    )

    assert (
        approval_replay[
            "consume_before_write"
        ]
        is True
    )

    assert (
        approval_replay[
            "second_consume_blocked"
        ]
        is True
    )


# ============================================================
# SCENARIO RESULTS
# ============================================================

def test_all_evaluation_scenarios_pass(
    evaluation_report: dict[str, object],
) -> None:
    """
    Every deterministic scenario must individually pass.
    """

    scenarios = (
        evaluation_report[
            "scenarios"
        ]
    )

    assert isinstance(
        scenarios,
        list,
    )

    assert len(
        scenarios
    ) == 10

    failed_scenarios = [
        scenario["name"]
        for scenario in scenarios
        if not scenario["passed"]
    ]

    assert failed_scenarios == []


# ============================================================
# JSON SERIALIZATION
# ============================================================

def test_evaluation_report_is_json_serializable(
    evaluation_report: dict[str, object],
) -> None:
    """
    CI systems must be able to serialize the complete
    evaluation report without custom encoders.
    """

    serialized = json.dumps(
        evaluation_report,
        ensure_ascii=False,
    )

    restored = json.loads(
        serialized
    )

    assert (
        restored[
            "schema_version"
        ]
        == "1.0"
    )

    assert (
        restored[
            "metrics"
        ][
            "overall_pass"
        ]
        is True
    )


# ============================================================
# CLI CONTRACT
# ============================================================

def test_evaluation_cli_returns_valid_json_and_zero_exit_code(
    tmp_path: Path,
) -> None:
    """
    The command used by CI must:

    - exit with code 0 when all gates pass
    - produce valid JSON
    - optionally persist the same machine-readable report
    """

    output_path = (
        tmp_path
        / "evaluation-report.json"
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "evals.run_evals",
            "--json",
            "--json-output",
            str(output_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert (
        result.returncode
        == 0
    )

    stdout_report = json.loads(
        result.stdout
    )

    assert (
        stdout_report[
            "metrics"
        ][
            "overall_pass"
        ]
        is True
    )

    assert output_path.exists()

    file_report = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        file_report[
            "metrics"
        ][
            "overall_pass"
        ]
        is True
    )

    assert (
        file_report[
            "schema_version"
        ]
        == stdout_report[
            "schema_version"
        ]
    )