from skhu_pc_management.application.use_cases.activate_windows import ActivateWindows
from skhu_pc_management.application.use_cases.load_pc_info import LoadPcInfo
from skhu_pc_management.domain.pc.models import PcInfo
from skhu_pc_management.infrastructure.license.null_product_key_provider import NullProductKeyProvider
from skhu_pc_management.ports.admin_privilege_checker import AdminPrivilegeChecker
from skhu_pc_management.ports.product_key_provider import ProductKeyProvider


class FakePcInfoReader:
    def read(self) -> PcInfo:
        return PcInfo(
            computer_name="PC01",
            user_name="student",
            os_name="Windows",
            cpu_name="CPU",
            memory_gb=16.0,
        )


class FakeProductKeyProvider:
    def get_windows_product_key(self, edition: str | None = None) -> str | None:
        return "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"

    def get_office_product_key(self, version: str | None = None) -> str | None:
        return "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"


class FakeClipboard:
    def set_text(self, text: str) -> None:
        pass


class FakeProcessLauncher:
    def launch(self, executable, args=()) -> None:
        pass


def test_product_key_provider_protocol_exists() -> None:
    assert hasattr(ProductKeyProvider, "get_windows_product_key")
    assert hasattr(ProductKeyProvider, "get_office_product_key")


def test_admin_privilege_checker_protocol_exists() -> None:
    assert hasattr(AdminPrivilegeChecker, "is_running_as_admin")


def test_fake_port_can_create_use_case() -> None:
    use_case = LoadPcInfo(FakePcInfoReader())

    result = use_case.execute()

    assert result.computer_name == "PC01"


def test_activate_windows_with_fake_provider_does_not_execute_activation() -> None:
    use_case = ActivateWindows(FakeProductKeyProvider(), FakeClipboard(), FakeProcessLauncher())

    result = use_case.execute()

    assert result.success is True
    assert result.action == "windows_activation"


def test_null_product_key_provider_returns_none() -> None:
    assert NullProductKeyProvider().get_windows_product_key() is None
