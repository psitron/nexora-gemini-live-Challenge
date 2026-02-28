"""GoalSpec compiler and validator tests."""

from __future__ import annotations

from goal_spec.compiler import GoalSpecCompiler, GoalSpec
from goal_spec.validator import GoalSpecValidator, ValidationResult


def test_compile_summary() -> None:
    compiler = GoalSpecCompiler()
    spec = compiler.compile("Open the Python website and list the sessions folder.")
    assert spec.raw_text
    assert spec.summary
    assert isinstance(spec.constraints, list)


def test_compile_extracts_read_only() -> None:
    compiler = GoalSpecCompiler()
    spec = compiler.compile("In read-only mode, list files in E:\\data.")
    types = [c.type for c in spec.constraints]
    assert "safety" in types


def test_validate_ok() -> None:
    validator = GoalSpecValidator()
    spec = GoalSpec(raw_text="Do something", summary="Do something", constraints=[])
    result = validator.validate(spec)
    assert isinstance(result, ValidationResult)
    assert result.ok is True


def test_validate_empty_goal_fails() -> None:
    validator = GoalSpecValidator()
    spec = GoalSpec(raw_text="   ", summary="", constraints=[])
    result = validator.validate(spec)
    assert result.ok is False
    assert any("empty" in i.message.lower() for i in result.issues)
