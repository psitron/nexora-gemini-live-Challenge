"""
Tests for execution/mouse_controller.py.

Uses mocks so the real mouse is never moved.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from execution.mouse_controller import (
    MouseActionResult,
    click_center_of_bbox,
    _parse_bbox,
)


def test_parse_bbox() -> None:
    x, y, w, h = _parse_bbox("100,200,50,60")
    assert x == 100 and y == 200 and w == 50 and h == 60


def test_parse_bbox_invalid_raises() -> None:
    with pytest.raises(ValueError):
        _parse_bbox("not,numbers")
    with pytest.raises(ValueError):
        _parse_bbox("1,2,3")  # need 4 values


def test_click_center_of_bbox_success() -> None:
    """With pyautogui mocked, click_center_of_bbox should call moveTo(center) and click()."""
    pa_mock = MagicMock()
    with patch.dict("sys.modules", {"pyautogui": pa_mock}):
        result = click_center_of_bbox("100,200,50,60")
    assert result.success is True
    assert "125" in result.message and "230" in result.message
    pa_mock.moveTo.assert_called_once_with(125, 230)  # 100+25, 200+30
    pa_mock.click.assert_called_once()


def test_click_center_of_bbox_invalid_bbox_fails() -> None:
    pa_mock = MagicMock()
    with patch.dict("sys.modules", {"pyautogui": pa_mock}):
        result = click_center_of_bbox("bad")
    assert result.success is False
    assert "Failed to click bbox" in result.message
    pa_mock.moveTo.assert_not_called()
    pa_mock.click.assert_not_called()


def test_click_center_of_bbox_missing_pyautogui_fails() -> None:
    """When pyautogui cannot be imported, return failure with clear message."""
    def raise_import(*args, **kwargs):
        if args and args[0] == "pyautogui":
            raise ImportError("No module named 'pyautogui'")
        return __import__(*args, **kwargs)

    with patch("builtins.__import__", side_effect=raise_import):
        result = click_center_of_bbox("10,20,30,40")
    assert result.success is False
    assert "pyautogui" in result.message.lower() or "not installed" in result.message.lower()
