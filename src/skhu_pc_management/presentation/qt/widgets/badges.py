from __future__ import annotations

from PySide6.QtWidgets import QLabel

from skhu_pc_management.presentation.qt.widgets.buttons import repolish


class StatusBadge(QLabel):
    def __init__(self, text: str = "", tone: str = "neutral") -> None:
        super().__init__(text)
        self.setObjectName("statusBadge")
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        repolish(self)

    def set_status(self, text: str, tone: str | None = None) -> None:
        self.setText(text)
        self.set_tone(tone or badge_tone_from_status(text))


def status_badge(text: str, tone: str = "neutral") -> QLabel:
    return StatusBadge(text, tone)


def set_badge_tone(label: QLabel, tone: str) -> None:
    label.setProperty("tone", tone)
    repolish(label)


def tone_from_status_text(text: str) -> str:
    return badge_tone_from_status(text)


def badge_tone_from_status(text: str) -> str:
    normalized = text.lower()
    if any(keyword in text for keyword in ("정상", "적용됨", "설치됨", "완료", "최신")):
        return "success"
    if any(keyword in text for keyword in ("주의", "미적용", "미설정", "값 없음", "필요", "존재", "설치되지")):
        return "warning"
    if any(keyword in text for keyword in ("진행 중", "확인 중")):
        return "info"
    if any(keyword in text for keyword in ("확인 불가", "알 수 없음", "미구현")):
        return "neutral"
    if any(keyword in text for keyword in ("실패", "오류", "불가")):
        return "danger"
    if any(keyword in normalized for keyword in ("ok", "applied", "success")):
        return "success"
    if any(keyword in normalized for keyword in ("warning", "missing", "unknown")):
        return "warning"
    if any(keyword in normalized for keyword in ("error", "failed")):
        return "danger"
    return "neutral"
