from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from skhu_pc_management.presentation.qt.widgets.badges import badge_tone_from_status


TONE_COLORS = {
    "neutral": ("#F3F4F6", "#4B5563"),
    "info": ("#EFF6FF", "#1D4ED8"),
    "success": ("#ECFDF5", "#16A34A"),
    "warning": ("#FFFBEB", "#D97706"),
    "danger": ("#FEF2F2", "#DC2626"),
}


def configure_table(table: QTableWidget, stretch_last: bool = True, compact: bool = False) -> None:
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setWordWrap(False)
    table.setShowGrid(False)
    table.horizontalHeader().setStretchLastSection(stretch_last)
    table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    table.verticalHeader().setDefaultSectionSize(30 if compact else 36)


def set_column_widths(table: QTableWidget, widths: tuple[int, ...], stretch_last: bool = True) -> None:
    header = table.horizontalHeader()
    for index, width in enumerate(widths):
        if index >= table.columnCount():
            break
        table.setColumnWidth(index, width)
        header.setSectionResizeMode(index, QHeaderView.Interactive)
    if stretch_last and table.columnCount():
        header.setSectionResizeMode(table.columnCount() - 1, QHeaderView.Stretch)


def table_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setToolTip(text)
    return item


def status_item(text: str) -> QTableWidgetItem:
    item = table_item(text)
    tone = badge_tone_from_status(text)
    background, foreground = TONE_COLORS.get(tone, TONE_COLORS["neutral"])
    item.setBackground(QColor(background))
    item.setForeground(QColor(foreground))
    item.setTextAlignment(Qt.AlignCenter)
    return item


def set_table_item(table: QTableWidget, row: int, column: int, text: str, tooltip: str | None = None) -> None:
    item = table_item(text)
    if tooltip is not None:
        item.setToolTip(tooltip)
    table.setItem(row, column, item)


def set_status_item(table: QTableWidget, row: int, column: int, text: str) -> None:
    table.setItem(row, column, status_item(text))
