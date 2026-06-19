from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skhu_pc_management.domain.network.models import NetworkAdapterInfo, StaticIpConfig


@dataclass
class NetworkViewModel:
    list_network_adapters_use_case: Any
    apply_static_ip_use_case: Any
    set_dhcp_use_case: Any
    adapters: list[NetworkAdapterInfo] = field(default_factory=list)
    selected_adapter: NetworkAdapterInfo | None = None
    current_network_info_rows: list[tuple[str, str]] = field(default_factory=list)
    ip_status_text: str = "알 수 없음"
    validation_message: str = ""
    status_message: str = "네트워크 어댑터를 불러오지 않았습니다."
    is_busy: bool = False

    def default_static_ip_fields(self) -> dict[str, str]:
        return {
            "ip_address": "192.168.",
            "subnet_mask": "255.255.255.0",
            "gateway": "192.168.",
            "dns1": "203.246.75.1",
            "dns2": "",
        }

    def gateway_for_ip_address(self, ip_address: str) -> str | None:
        text = ip_address.strip()
        if not text:
            return None

        last_dot_index = text.rfind(".")
        if last_dot_index <= 0:
            return None

        return f"{text[:last_dot_index + 1]}1"

    def load_adapters(self) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        self.is_busy = True
        self.status_message = "네트워크 어댑터를 불러오는 중입니다..."
        try:
            self.adapters = self.list_network_adapters_use_case.execute()
            if self.adapters:
                self.select_adapter_by_name(self.adapters[0].name)
                self.status_message = f"어댑터 {len(self.adapters)}개를 불러왔습니다."
            else:
                self.selected_adapter = None
                self.current_network_info_rows = []
                self.ip_status_text = "알 수 없음"
                self.status_message = (
                    "어댑터를 찾지 못했습니다. PowerShell/Get-NetAdapter 또는 netsh 조회 결과를 확인하세요."
                )
        except Exception as exc:
            self.adapters = []
            self.status_message = f"어댑터 조회 실패: {exc}"
        finally:
            self.is_busy = False

    def select_adapter_by_name(self, adapter_name: str) -> None:
        self.selected_adapter = next((adapter for adapter in self.adapters if adapter.name == adapter_name), None)
        self._update_current_network_info()

    def apply_static_ip(
        self,
        adapter_name: str,
        ip_address: str,
        subnet_mask: str,
        gateway: str,
        dns1: str,
        dns2: str,
    ) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        self.is_busy = True
        self.status_message = "정적 IP를 적용하는 중입니다..."
        try:
            config = StaticIpConfig(
                adapter_name=adapter_name,
                ip_address=ip_address,
                subnet_mask=subnet_mask,
                gateway=gateway,
                dns1=dns1,
                dns2=dns2,
            )
            self.validation_message = ""
            result = self.apply_static_ip_use_case.execute(config)
            self.status_message = result.message if result.success else f"정적 IP 적용 실패: {result.message}"
        except Exception as exc:
            self.validation_message = str(exc)
            self.status_message = f"입력 오류: {exc}"
        finally:
            self.is_busy = False

    def _update_current_network_info(self) -> None:
        adapter = self.selected_adapter
        if adapter is None:
            self.ip_status_text = "알 수 없음"
            self.current_network_info_rows = []
            return

        self.ip_status_text = _dhcp_text(adapter.is_dhcp_enabled)
        dns1 = adapter.dns_servers[0] if len(adapter.dns_servers) >= 1 else ""
        dns2 = adapter.dns_servers[1] if len(adapter.dns_servers) >= 2 else ""
        self.current_network_info_rows = [
            ("네트워크 어댑터", adapter.name),
            ("IP 할당 방식", self.ip_status_text),
            ("IP 주소", ", ".join(adapter.ip_addresses) or ""),
            ("서브넷 마스크", adapter.subnet_mask or ""),
            ("기본 게이트웨이", adapter.gateway or ""),
            ("기본 DNS", dns1),
            ("보조 DNS", dns2),
        ]

    def set_dhcp(self, adapter_name: str) -> None:
        if self.is_busy:
            self.status_message = "다른 작업이 진행 중입니다."
            return
        self.is_busy = True
        self.status_message = "DHCP로 전환하는 중입니다..."
        try:
            result = self.set_dhcp_use_case.execute(adapter_name)
            self.status_message = result.message if result.success else f"DHCP 전환 실패: {result.message}"
        except Exception as exc:
            self.status_message = f"DHCP 전환 실패: {exc}"
        finally:
            self.is_busy = False


def _dhcp_text(value: bool | None) -> str:
    if value is True:
        return "자동 IP(DHCP)"
    if value is False:
        return "수동 IP"
    return "알 수 없음"
