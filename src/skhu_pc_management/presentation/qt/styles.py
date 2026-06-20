from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget


APP_QSS = """
QMainWindow {
    background: #F6F7F9;
}
QWidget {
    color: #111827;
    font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif;
    font-size: 13px;
}
QWidget#appShell {
    background: #F6F7F9;
}
QWidget#panelContent,
QWidget#formGrid,
QWidget#fieldRow,
QWidget#scrollContent,
QWidget#transparentContainer {
    background: transparent;
}
QFrame#topBar {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
QFrame#sideNav {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
QFrame#contentSurface {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
QFrame#card, QFrame#sectionCard, QFrame#summaryCard {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
}
QFrame#sectionCard {
    background: #FFFFFF;
    border: 1px solid #EEF0F3;
    border-radius: 10px;
}
QFrame#actionRow {
    background: #FFFFFF;
    border: 1px solid #EEF0F3;
    border-radius: 10px;
}
QFrame#summaryCard {
    background: #FFFFFF;
}
QFrame#summaryCard[tone="success"] {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
}
QFrame#summaryCard[tone="danger"] {
    background: #FEF2F2;
    border: 1px solid #FECACA;
}
QFrame#summaryCard[tone="warning"] {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
}
QFrame#summaryCard[tone="neutral"] {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
}
QFrame#infoBanner {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 10px;
}
QFrame#warningBanner {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 10px;
}
QFrame#comboShell {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
}
QLabel#appTitle {
    color: #111827;
    font-size: 20px;
    font-weight: 700;
}
QLabel#appSubtitle, QLabel#pageSubtitle, QLabel#mutedText {
    color: #6B7280;
}
QLabel#pageTitle {
    color: #111827;
    font-size: 24px;
    font-weight: 700;
}
QLabel#sectionTitle, QLabel#cardTitle {
    color: #111827;
    font-size: 15px;
    font-weight: 650;
}
QLabel#actionTitle {
    color: #111827;
    font-weight: 700;
}
QLabel#actionDescription {
    color: #6B7280;
}
QLabel#compactStatusText {
    color: #374151;
    font-weight: 650;
}
QLabel#summaryTitle {
    color: #6B7280;
    font-size: 12px;
    font-weight: 650;
}
QLabel#summaryValue {
    color: #111827;
    font-size: 18px;
    font-weight: 700;
}
QLabel#fieldLabel {
    color: #4B5563;
    font-weight: 650;
}
QLabel#readOnlyField {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 7px 10px;
    color: #111827;
    font-weight: 600;
    min-height: 26px;
}
QLabel#statusValueField {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-left: 3px solid #D1D5DB;
    border-radius: 6px;
    padding: 7px 10px;
    color: #111827;
    font-weight: 600;
    min-height: 26px;
}
QLabel#statusValueField[tone="success"] {
    border-left-color: #16A34A;
    color: #166534;
}
QLabel#statusValueField[tone="warning"] {
    border-left-color: #D97706;
    color: #92400E;
}
QLabel#statusValueField[tone="danger"] {
    border-left-color: #DC2626;
    color: #991B1B;
}
QLabel#statusValueField[tone="neutral"] {
    border-left-color: #D1D5DB;
    color: #374151;
}
QLabel#statusValueField[tone="info"] {
    border-left-color: #0EA5E9;
    color: #075985;
}
QLabel#inlineHint {
    background: transparent;
    border: 0;
    padding: 2px 0;
    color: #4B5563;
}
QLabel#statusBadge {
    border-radius: 999px;
    padding: 4px 10px;
    font-weight: 650;
}
QLabel#statusBadge[tone="neutral"] {
    background: #F3F4F6;
    color: #4B5563;
    border: 1px solid #E5E7EB;
}
QLabel#statusBadge[tone="info"] {
    background: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
}
QLabel#statusBadge[tone="success"] {
    background: #ECFDF5;
    color: #16A34A;
    border: 1px solid #BBF7D0;
}
QLabel#statusBadge[tone="warning"] {
    background: #FFFBEB;
    color: #D97706;
    border: 1px solid #FDE68A;
}
QLabel#statusBadge[tone="danger"] {
    background: #FEF2F2;
    color: #DC2626;
    border: 1px solid #FECACA;
}
QPushButton {
    min-height: 34px;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 650;
}
QPushButton[buttonRole="primary"] {
    background: #2563EB;
    border: 1px solid #2563EB;
    color: #FFFFFF;
}
QPushButton[buttonRole="primary"]:hover {
    background: #1D4ED8;
    border-color: #1D4ED8;
}
QPushButton[buttonRole="secondary"] {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    color: #111827;
}
QPushButton[buttonRole="secondary"]:hover {
    background: #F9FAFB;
    border-color: #9CA3AF;
}
QPushButton[buttonRole="subtle"] {
    background: transparent;
    border: 1px solid transparent;
    color: #2563EB;
}
QPushButton[buttonRole="subtle"]:hover {
    background: #EFF6FF;
}
QPushButton[buttonRole="danger"] {
    background: #FEF2F2;
    border: 1px solid #FECACA;
    color: #DC2626;
}
QPushButton[buttonRole="danger"]:hover {
    background: #FEE2E2;
}
QPushButton[buttonRole="warning"] {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    color: #B45309;
}
QPushButton[buttonRole="nav"] {
    background: transparent;
    border: 1px solid transparent;
    color: #374151;
    text-align: left;
    padding: 10px 12px;
}
QPushButton[buttonRole="nav"]:hover {
    background: #F3F4F6;
}
QPushButton[buttonRole="nav"][selected="true"] {
    background: #EFF6FF;
    border-color: #BFDBFE;
    color: #1D4ED8;
}
QPushButton:pressed {
    padding-top: 8px;
    padding-bottom: 6px;
}
QPushButton:disabled {
    background: #F3F4F6;
    border-color: #E5E7EB;
    color: #9CA3AF;
}
QPushButton#activationActionButton {
    min-width: 190px;
    max-width: 240px;
}
QLineEdit, QTextEdit, QComboBox {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 7px 9px;
    min-height: 32px;
}
QComboBox {
    padding-right: 32px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #2563EB;
}
QLineEdit:read-only {
    background: #FAFAFA;
    color: #4B5563;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left: 1px solid #E5E7EB;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background: #F9FAFB;
}
QComboBox::down-arrow {
    image: none;
    border: 0;
    width: 0;
    height: 0;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    selection-background-color: #EFF6FF;
    selection-color: #111827;
    outline: 0;
}
QComboBox#comboInShell {
    background: transparent;
    border: 0;
    border-radius: 8px;
    padding: 7px 8px;
    min-height: 32px;
}
QComboBox#comboInShell::drop-down {
    border: 0;
    width: 0;
}
QComboBox#comboInShell::down-arrow {
    image: none;
    border: 0;
    width: 0;
    height: 0;
}
QLabel#comboArrow {
    background: transparent;
    color: #64748B;
    font-size: 14px;
    font-weight: 700;
    padding: 0 10px 0 4px;
}
QCheckBox, QRadioButton {
    color: #111827;
    spacing: 8px;
}
QTableWidget {
    background: #FFFFFF;
    alternate-background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    gridline-color: #F8FAFC;
    selection-background-color: #EFF6FF;
    selection-color: #111827;
}
QTableWidget[compact="true"] {
    font-size: 12px;
}
QTableWidget[compact="true"]::item {
    padding: 4px 8px;
}
QHeaderView::section {
    background: #F9FAFB;
    border: 0;
    border-bottom: 1px solid #E5E7EB;
    color: #4B5563;
    padding: 8px;
    font-weight: 650;
}
QScrollArea {
    border: 0;
    background: transparent;
}
QScrollArea QWidget#qt_scrollarea_viewport {
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    background: transparent;
    border: 0;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 5px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
    background: transparent;
    border: 0;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""


def make_card(title: str | None = None, object_name: str = "card") -> tuple[QFrame, QVBoxLayout]:
    from skhu_pc_management.presentation.qt.widgets.surfaces import Card

    frame = Card(title)
    frame.setObjectName(object_name)
    return frame, frame.body_layout


def set_button_role(button: QWidget, role: str) -> None:
    from skhu_pc_management.presentation.qt.widgets.buttons import set_button_role as _set_button_role

    _set_button_role(button, role)
