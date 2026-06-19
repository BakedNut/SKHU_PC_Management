from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from skhu_pc_management.presentation.qt.widgets.badges import badge_tone_from_status
from skhu_pc_management.presentation.qt.widgets.buttons import repolish


class ReadOnlyField(QLabel):
    def __init__(self, value: str = "") -> None:
        super().__init__(value)
        self.setObjectName("readOnlyField")
        self.setWordWrap(True)
        self.setTextInteractionFlags(self.textInteractionFlags())
        self.setToolTip(value)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API override
        super().setText(text)
        self.setToolTip(text)


class StatusValueField(ReadOnlyField):
    def __init__(self, value: str = "", tone: str = "neutral") -> None:
        super().__init__(value)
        self.setObjectName("statusValueField")
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        repolish(self)

    def set_status(self, text: str, tone: str | None = None) -> None:
        self.setText(text)
        self.set_tone(tone or badge_tone_from_status(text))


class FieldRow(QWidget):
    def __init__(self, label: str, widget: QWidget, help_text: str | None = None) -> None:
        super().__init__()
        self.setObjectName("fieldRow")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label_widget = QLabel(label)
        label_widget.setObjectName("fieldLabel")
        layout.addWidget(label_widget)
        layout.addWidget(widget)
        if help_text:
            help_label = QLabel(help_text)
            help_label.setObjectName("mutedText")
            help_label.setWordWrap(True)
            layout.addWidget(help_label)


class FormGrid(QWidget):
    def __init__(self, columns: int = 2) -> None:
        super().__init__()
        self.setObjectName("formGrid")
        self.columns = max(1, columns)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(12)
        self._count = 0

    def add_field(self, label: str, widget: QWidget, help_text: str | None = None) -> None:
        row = self._count // self.columns
        column = self._count % self.columns
        self.grid.addWidget(FieldRow(label, widget, help_text), row, column)
        self._count += 1


def read_only_field(value: str = "") -> ReadOnlyField:
    return ReadOnlyField(value)


def field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    return label


def muted_text(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("mutedText")
    label.setWordWrap(True)
    return label


def add_field(
    grid: QGridLayout,
    row: int,
    label: str,
    widget: QWidget,
    column: int = 0,
    colspan: int = 1,
) -> None:
    grid.addWidget(FieldRow(label, widget), row, column, 1, colspan)
