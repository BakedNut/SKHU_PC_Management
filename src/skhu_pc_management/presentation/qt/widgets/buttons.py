from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_button_role(button: QWidget, role: str) -> None:
    button.setProperty("buttonRole", role)
    repolish(button)


def _button(text: str, role: str) -> QPushButton:
    button = QPushButton(text)
    set_button_role(button, role)
    return button


def primary_button(text: str) -> QPushButton:
    return _button(text, "primary")


def secondary_button(text: str) -> QPushButton:
    return _button(text, "secondary")


def subtle_button(text: str) -> QPushButton:
    return _button(text, "subtle")


def danger_button(text: str) -> QPushButton:
    return _button(text, "danger")


def warning_button(text: str) -> QPushButton:
    return _button(text, "warning")


def nav_button(text: str) -> QPushButton:
    return _button(text, "nav")
