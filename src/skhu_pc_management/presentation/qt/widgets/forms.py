from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QLineEdit, QVBoxLayout, QWidget


class ReadOnlyField(QLabel):
    def __init__(self, value: str = "") -> None:
        super().__init__(value)
        self.setObjectName("readOnlyField")
        self.setWordWrap(True)
        self.setTextInteractionFlags(self.textInteractionFlags())


class FieldRow(QWidget):
    def __init__(self, label: str, widget: QWidget, help_text: str | None = None) -> None:
        super().__init__()
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


def read_only_field(value: str = "") -> QLineEdit:
    widget = QLineEdit(value)
    widget.setReadOnly(True)
    return widget


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
