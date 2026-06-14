from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from skhu_pc_management.ports.admin_privilege_checker import AdminPrivilegeChecker


@dataclass(frozen=True)
class StartupStepResult:
    name: str
    success: bool
    message: str = ""


@dataclass
class StartupResult:
    is_admin: bool
    step_results: list[StartupStepResult] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(not result.success for result in self.step_results)


@dataclass
class StartupCoordinator:
    admin_privilege_checker: AdminPrivilegeChecker
    pc_info_view_model: Any
    settings_view_model: Any
    pc_check_view_model: Any
    is_busy: bool = False
    has_initialized: bool = False

    def initialize(self) -> StartupResult:
        if self.is_busy:
            return StartupResult(
                is_admin=self.admin_privilege_checker.is_running_as_admin(),
                step_results=[StartupStepResult("startup", False, "초기화가 이미 진행 중입니다.")],
            )

        if self.has_initialized:
            return StartupResult(
                is_admin=self.admin_privilege_checker.is_running_as_admin(),
                step_results=[StartupStepResult("startup", True, "이미 초기화되었습니다.")],
            )

        self.is_busy = True
        try:
            is_admin = self.admin_privilege_checker.is_running_as_admin()
            results = [
                self._run_step("pc_info", self.pc_info_view_model.refresh),
                self._run_step(
                    "settings_status",
                    lambda: self.settings_view_model.check_status(self.settings_view_model.all_setting_ids()),
                ),
                self._run_step("pc_checks", self.pc_check_view_model.run_checks),
            ]
            self.has_initialized = True
            return StartupResult(is_admin=is_admin, step_results=results)
        finally:
            self.is_busy = False

    @staticmethod
    def _run_step(name: str, action: Callable[[], None]) -> StartupStepResult:
        try:
            action()
        except Exception as exc:
            return StartupStepResult(name, False, str(exc))
        return StartupStepResult(name, True)
