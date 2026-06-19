from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget


APP_QSS = """
QMainWindow, QWidget {
    background: #F3F4F6;
    color: #111827;
    font-size: 13px;
}
QFrame#card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
}
QFrame#headerCard {
    background: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 10px;
}
QFrame#busyCard {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 10px;
}
QFrame#startPointCard {
    background: #EFF6FF;
    border: 1px solid #93C5FD;
    border-radius: 10px;
}
QLabel#cardTitle {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
    margin-bottom: 6px;
}
QLabel#fieldLabel, QLabel#sectionTitle {
    color: #6B7280;
    font-weight: 600;
}
QLabel#headerTitle {
    color: white;
    font-size: 22px;
    font-weight: 700;
}
QLabel#windowsBadge {
    background: #1D4ED8;
    color: white;
    font-weight: 600;
    border-radius: 10px;
    padding: 3px 8px;
}
QLabel#pcBadge {
    background: #0EA5E9;
    color: white;
    font-weight: 600;
    border-radius: 10px;
    padding: 3px 8px;
}
QLabel#busyLabel {
    color: #1E3A8A;
    font-weight: 700;
}
QLineEdit, QTextEdit, QComboBox {
    background: #F9FAFB;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 6px 8px;
}
QPushButton {
    background: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 4px;
    color: #1E3A8A;
    font-weight: 600;
    padding: 7px 12px;
}
QPushButton[buttonRole="primary"] {
    background: #2563EB;
    border-color: #2563EB;
    color: white;
}
QPushButton[buttonRole="danger"] {
    background: #DC2626;
    border-color: #DC2626;
    color: white;
}
QPushButton:disabled {
    background: #E5E7EB;
    border-color: #D1D5DB;
    color: #9CA3AF;
}
QTableWidget {
    background: white;
    alternate-background-color: #F9FAFB;
    border: 1px solid #D1D5DB;
    gridline-color: #E5E7EB;
}
QHeaderView::section {
    background: #F9FAFB;
    border: 0;
    border-bottom: 1px solid #D1D5DB;
    padding: 6px;
    font-weight: 600;
}
QTabWidget::pane {
    border: 0;
    top: -1px;
}
QTabBar::tab {
    background: #E5E7EB;
    color: #6B7280;
    font-weight: 600;
    padding: 10px 18px;
    margin-right: 6px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background: white;
    color: #111827;
    border: 1px solid #E5E7EB;
    border-bottom: 0;
}
"""


def make_card(title: str | None = None, object_name: str = "card") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(object_name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)
    if title:
        from PySide6.QtWidgets import QLabel

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label)
    return frame, layout


def set_button_role(button: QWidget, role: str) -> None:
    button.setProperty("buttonRole", role)
    button.style().unpolish(button)
    button.style().polish(button)
