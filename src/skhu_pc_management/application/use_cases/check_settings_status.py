from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Iterable

from skhu_pc_management.domain.settings.definitions import (
    DEFAULT_SETTING_DEFINITIONS_BY_ID,
    RegistrySettingDefinition,
    SettingDefinition,
)
from skhu_pc_management.domain.settings.models import SettingStatus
from skhu_pc_management.ports.registry import Registry
from skhu_pc_management.ports.setting_status_provider import SettingStatusProvider


@dataclass(frozen=True)
class CheckSettingsStatus:
    registry: Registry
    setting_status_providers: Mapping[str, SettingStatusProvider] = field(default_factory=dict)
    definitions_by_id: dict[str, SettingDefinition] = field(
        default_factory=lambda: dict(DEFAULT_SETTING_DEFINITIONS_BY_ID)
    )

    def execute(self, setting_ids: Iterable[str]) -> list[SettingStatus]:
        statuses: list[SettingStatus] = []

        for setting_id in setting_ids:
            definition = self.definitions_by_id.get(setting_id)
            if definition is None:
                statuses.append(
                    SettingStatus(
                        setting_id=setting_id,
                        label=setting_id,
                        name=setting_id,
                        severity="error",
                        status_text=f"Unknown setting id: {setting_id}",
                    )
                )
                continue

            statuses.append(self._check_definition(definition))

        return statuses

    def _check_definition(self, definition: SettingDefinition) -> SettingStatus:
        provider = self.setting_status_providers.get(definition.setting_id)
        if provider is not None:
            return provider.check(definition.setting_id)

        if not definition.registry_values:
            return SettingStatus(
                setting_id=definition.setting_id,
                label=definition.name,
                name=definition.name,
                severity="unknown",
                status_text="status_provider_missing",
                detail="상태 확인 구현 필요",
                current_value="상태 확인 구현 필요",
            )

        checked_values: list[tuple[RegistrySettingDefinition, object | None, str]] = []
        for registry_value in definition.registry_values:
            try:
                actual_value = self.registry.read_value(
                    registry_value.root,
                    registry_value.path,
                    registry_value.value_name,
                )
            except Exception as exc:
                return self._build_status(
                    definition,
                    expected_value=self._expected_value(definition),
                    actual_value=None,
                    is_configured=False,
                    severity="unknown",
                    status_text="read_failed",
                    detail=f"레지스트리 값을 읽을 수 없습니다: {exc}",
                )

            if actual_value is None:
                checked_values.append((registry_value, actual_value, "missing"))
                continue

            state = "ok" if _values_match(actual_value, registry_value.expected_value) else "mismatch"
            checked_values.append((registry_value, actual_value, state))

        expected_value = self._expected_value(definition)
        actual_value = self._actual_value(checked_values)

        if all(state == "ok" for _, _, state in checked_values):
            return self._build_status(
                definition,
                expected_value=expected_value,
                actual_value=actual_value,
                is_configured=True,
                severity="ok",
                status_text="configured",
            )

        if any(state == "missing" for _, _, state in checked_values):
            return self._build_status(
                definition,
                expected_value=expected_value,
                actual_value=actual_value,
                is_configured=False,
                severity="unknown",
                status_text="missing",
            )

        return self._build_status(
            definition,
            expected_value=expected_value,
            actual_value=actual_value,
            is_configured=False,
            severity="warning",
            status_text="not_configured",
        )

    @staticmethod
    def _expected_value(definition: SettingDefinition) -> object:
        values = tuple(value.expected_value for value in definition.registry_values)
        return values[0] if len(values) == 1 else values

    @staticmethod
    def _actual_value(
        checked_values: list[tuple[RegistrySettingDefinition, object | None, str]]
    ) -> object | None:
        values = tuple(actual for _, actual, _ in checked_values)
        return values[0] if len(values) == 1 else values

    @staticmethod
    def _build_status(
        definition: SettingDefinition,
        expected_value: object | None,
        actual_value: object | None,
        is_configured: bool,
        severity: str,
        status_text: str,
        detail: str = "",
    ) -> SettingStatus:
        return SettingStatus(
            setting_id=definition.setting_id,
            label=definition.name,
            expected_value=expected_value,
            actual_value=actual_value,
            is_configured=is_configured,
            severity=severity,
            status_text=status_text,
            name=definition.name,
            is_applied=is_configured,
            current_value=None if actual_value is None else str(actual_value),
            detail=detail or (f"현재값: {actual_value}" if actual_value is not None else "현재값 없음"),
        )


def _values_match(actual_value: object, expected_value: object) -> bool:
    if isinstance(expected_value, int):
        try:
            return int(actual_value) == expected_value
        except (TypeError, ValueError):
            return False

    if isinstance(expected_value, str):
        return str(actual_value).lower() == expected_value.lower()

    return actual_value == expected_value
