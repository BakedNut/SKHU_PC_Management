from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class Card(QFrame):
    def __init__(self, title: str | None = None, subtitle: str | None = None, object_name: str = "card") -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.body_layout = QVBoxLayout(self)
        self.body_layout.setContentsMargins(18, 18, 18, 18)
        self.body_layout.setSpacing(12)
        if title:
            title_label = QLabel(title)
            title_label.setObjectName("cardTitle")
            self.body_layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("mutedText")
            subtitle_label.setWordWrap(True)
            self.body_layout.addWidget(subtitle_label)


class SectionCard(Card):
    def __init__(self, title: str, subtitle: str | None = None) -> None:
        super().__init__(title, subtitle, object_name="sectionCard")


class SummaryCard(Card):
    def __init__(self, title: str, value: str, subtitle: str | None = None, accent: str | None = None) -> None:
        super().__init__(object_name="summaryCard")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("summaryTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("summaryValue")
        self.body_layout.addWidget(self.title_label)
        self.body_layout.addWidget(self.value_label)
        self.subtitle_label: QLabel | None = None
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setObjectName("mutedText")
            self.subtitle_label.setWordWrap(True)
            self.body_layout.addWidget(self.subtitle_label)
        if accent:
            self.setProperty("accent", accent)

    def set_value(self, value: str, subtitle: str | None = None) -> None:
        self.value_label.setText(value)
        if subtitle is not None:
            if self.subtitle_label is None:
                self.subtitle_label = QLabel()
                self.subtitle_label.setObjectName("mutedText")
                self.subtitle_label.setWordWrap(True)
                self.body_layout.addWidget(self.subtitle_label)
            self.subtitle_label.setText(subtitle)


def card(title: str | None = None, subtitle: str | None = None, object_name: str = "card") -> tuple[QFrame, QVBoxLayout]:
    frame = Card(title, subtitle, object_name)
    return frame, frame.body_layout


def summary_card(title: str, value: str, subtitle: str | None = None, tone: str = "neutral") -> QFrame:
    frame = SummaryCard(title, value, subtitle)
    frame.setProperty("tone", tone)
    return frame


def info_banner(message: str, tone: str = "info") -> QFrame:
    frame = QFrame()
    frame.setObjectName("warningBanner" if tone == "warning" else "infoBanner")
    frame.setProperty("tone", tone)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 8, 12, 8)
    label = QLabel(message)
    label.setObjectName("mutedText")
    label.setWordWrap(True)
    layout.addWidget(label)
    return frame
