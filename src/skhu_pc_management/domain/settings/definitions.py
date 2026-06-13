from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistrySettingDefinition:
    name: str
    root: str
    path: str
    value_name: str
    expected_value: object
    value_type: str
