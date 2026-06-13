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
    status_message: str = "네트워크 어댑터를 불러오지 않았습니다."
    is_busy: bool = False

    def load_adapters(self) -> None:
        self.is_busy = True
        self.status_message = "네트워크 어댑터를 불러오는 중입니다..."
        try:
            self.adapters = self.list_network_adapters_use_case.execute()
            self.status_message = f"어댑터 {len(self.adapters)}개를 불러왔습니다."
        except Exception as exc:
            self.adapters = []
            self.status_message = f"어댑터 조회 실패: {exc}"
        finally:
            self.is_busy = False

    def apply_static_ip(
        self,
        adapter_name: str,
        ip_address: str,
        subnet_mask: str,
        gateway: str,
        dns1: str,
        dns2: str,
    ) -> None:
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
            result = self.apply_static_ip_use_case.execute(config)
            self.status_message = result.message if result.success else f"정적 IP 적용 실패: {result.message}"
        except Exception as exc:
            self.status_message = f"입력 오류: {exc}"
        finally:
            self.is_busy = False

    def set_dhcp(self, adapter_name: str) -> None:
        self.is_busy = True
        self.status_message = "DHCP로 전환하는 중입니다..."
        try:
            result = self.set_dhcp_use_case.execute(adapter_name)
            self.status_message = result.message if result.success else f"DHCP 전환 실패: {result.message}"
        except Exception as exc:
            self.status_message = f"DHCP 전환 실패: {exc}"
        finally:
            self.is_busy = False
