"""Verifier (diff, outcome) tests."""

from __future__ import annotations

from verifier.diff_engine import DiffResult, diff_states
from verifier.pre_state import PreStateSnapshot
from verifier.post_state import PostStateSnapshot
from verifier.outcome_classifier import OutcomeLabel, classify_outcome, Outcome


def test_diff_result_has_changes() -> None:
    pre = PreStateSnapshot(environment=None, dirty=True)
    post = PostStateSnapshot(environment=None, dirty=False)
    diff = diff_states(pre, post)
    assert isinstance(diff, DiffResult)
    assert diff.has_changes is True


def test_diff_result_no_changes() -> None:
    pre = PreStateSnapshot(environment=None, dirty=False)
    post = PostStateSnapshot(environment=None, dirty=False)
    diff = diff_states(pre, post)
    assert diff.has_changes is False


def test_classify_outcome_pass() -> None:
    diff = DiffResult(raw={"dirty": {"old_value": True, "new_value": False}})
    outcome = classify_outcome(diff, expected_satisfied=True)
    assert outcome.label == OutcomeLabel.PASS


def test_classify_outcome_no_op() -> None:
    diff = DiffResult(raw={})
    outcome = classify_outcome(diff, expected_satisfied=False)
    assert outcome.label == OutcomeLabel.NO_OP


def test_classify_outcome_timeout() -> None:
    diff = DiffResult(raw={})
    outcome = classify_outcome(diff, expected_satisfied=False, timed_out=True)
    assert outcome.label == OutcomeLabel.TIMEOUT
