from __future__ import annotations

from dataclasses import dataclass
import socket

from skhu_pc_management.domain.network.models import NetworkAdapterInfo
from skhu_pc_management.domain.pc.models import PcNetworkInfo


IF_TYPE_ETHERNET_CSMACD = 6
IF_TYPE_IEEE80211 = 71
IF_TYPE_SOFTWARE_LOOPBACK = 24


@dataclass(frozen=True)
class NetworkIdentityCandidate:
    ip: str
    mac: str
    friendly_name: str
    if_type: int
    oper_status_up: bool
    has_gateway: bool
    metric: int | None = None
    description: str = ""
    adapter_name: str = ""
    adapter_type: str = ""
    ip_addresses: tuple[str, ...] = ()
    gateway: str | None = None
    dns_servers: tuple[str, ...] = ()
    prefix_length: int | None = None


def read_network_identity() -> tuple[str, str] | None:
    try:
        candidates = _get_adapters_addresses_candidates()
    except Exception:
        return None
    selected = select_network_identity_candidate(candidates)
    if selected is None:
        return "연결된 이더넷 없음", "알 수 없음"
    return selected.ip, normalize_mac_address(selected.mac) or "알 수 없음"


def read_active_network_info() -> PcNetworkInfo | None:
    candidates = _get_adapters_addresses_candidates()
    selected = select_network_identity_candidate(candidates)
    if selected is None:
        return None
    return PcNetworkInfo(
        adapter_name=selected.adapter_name or selected.friendly_name,
        adapter_type=_candidate_adapter_type(selected),
        ip_address=selected.ip,
        mac_address=normalize_mac_address(selected.mac) or selected.mac or None,
        description=selected.description or selected.friendly_name,
    )


def read_network_adapters_fast() -> list[NetworkAdapterInfo]:
    candidates = _get_adapters_addresses_candidates()
    adapters = [
        _network_adapter_info_from_candidate(candidate)
        for candidate in candidates
        if candidate.if_type in {IF_TYPE_ETHERNET_CSMACD, IF_TYPE_IEEE80211}
        and not is_excluded_adapter_name(_candidate_name_text(candidate))
    ]
    return sorted(
        adapters,
        key=lambda adapter: (
            0 if _adapter_type_from_name(adapter.name, adapter.description) == "Ethernet" else 1,
            not adapter.is_enabled,
            not bool(adapter.gateway),
            _adapter_metric(adapter, candidates),
            adapter.name.lower(),
        ),
    )


def select_network_identity_candidate(candidates: list[NetworkIdentityCandidate]) -> NetworkIdentityCandidate | None:
    filtered = [
        candidate
        for candidate in candidates
        if candidate.oper_status_up
        and candidate.if_type in {IF_TYPE_ETHERNET_CSMACD, IF_TYPE_IEEE80211}
        and candidate.if_type != IF_TYPE_SOFTWARE_LOOPBACK
        and candidate.ip
        and candidate.has_gateway
        and not is_excluded_adapter_name(_candidate_name_text(candidate))
    ]
    if not filtered:
        return None
    return sorted(
        filtered,
        key=lambda candidate: (
            0 if candidate.if_type == IF_TYPE_ETHERNET_CSMACD else 1,
            candidate.metric if candidate.metric not in (None, 0) else 2**31 - 1,
            (candidate.adapter_name or candidate.friendly_name).lower(),
        ),
    )[0]


def is_excluded_adapter_name(name: str) -> bool:
    lower = name.lower()
    return any(
        token in lower
        for token in (
            "tailscale",
            "vpn",
            "tunnel",
            "virtual",
            "vethernet",
            "hyper-v",
            "vmware",
            "virtualbox",
            "loopback",
            "bluetooth",
            "docker",
            "wsl",
            "tap-",
            "tap windows",
            "wireguard",
        )
    )


def normalize_mac_address(value: str | None) -> str | None:
    if not value:
        return None
    hex_digits = "".join(char for char in value if char.isalnum())
    if len(hex_digits) != 12:
        return value.strip().upper() or None
    return "-".join(hex_digits[index : index + 2].upper() for index in range(0, 12, 2))


def _get_adapters_addresses_candidates() -> list[NetworkIdentityCandidate]:
    import ctypes
    from ctypes import wintypes

    ULONG = wintypes.ULONG
    DWORD = wintypes.DWORD
    PULONG = ctypes.POINTER(ULONG)
    AF_UNSPEC = 0
    AF_INET = 2
    NO_ERROR = 0
    GAA_FLAGS = 0x0002 | 0x0004

    class SOCKET_ADDRESS(ctypes.Structure):
        _fields_ = (("lpSockaddr", ctypes.c_void_p), ("iSockaddrLength", ctypes.c_int))

    class SOCKADDR_IN(ctypes.Structure):
        _fields_ = (
            ("sin_family", ctypes.c_ushort),
            ("sin_port", ctypes.c_ushort),
            ("sin_addr", ctypes.c_ubyte * 4),
            ("sin_zero", ctypes.c_ubyte * 8),
        )

    class IP_ADAPTER_UNICAST_ADDRESS(ctypes.Structure):
        pass

    IP_ADAPTER_UNICAST_ADDRESS._fields_ = (
        ("Length", ULONG),
        ("Flags", DWORD),
        ("Next", ctypes.POINTER(IP_ADAPTER_UNICAST_ADDRESS)),
        ("Address", SOCKET_ADDRESS),
        ("PrefixOrigin", ctypes.c_int),
        ("SuffixOrigin", ctypes.c_int),
        ("DadState", ctypes.c_int),
        ("ValidLifetime", ULONG),
        ("PreferredLifetime", ULONG),
        ("LeaseLifetime", ULONG),
        ("OnLinkPrefixLength", ctypes.c_ubyte),
    )

    class IP_ADAPTER_GATEWAY_ADDRESS(ctypes.Structure):
        pass

    IP_ADAPTER_GATEWAY_ADDRESS._fields_ = (
        ("Length", ULONG),
        ("Reserved", DWORD),
        ("Next", ctypes.POINTER(IP_ADAPTER_GATEWAY_ADDRESS)),
        ("Address", SOCKET_ADDRESS),
    )

    class IP_ADAPTER_DNS_SERVER_ADDRESS(ctypes.Structure):
        pass

    IP_ADAPTER_DNS_SERVER_ADDRESS._fields_ = (
        ("Length", ULONG),
        ("Reserved", DWORD),
        ("Next", ctypes.POINTER(IP_ADAPTER_DNS_SERVER_ADDRESS)),
        ("Address", SOCKET_ADDRESS),
    )

    class IP_ADAPTER_ADDRESSES(ctypes.Structure):
        pass

    IP_ADAPTER_ADDRESSES._fields_ = (
        ("Length", ULONG),
        ("IfIndex", DWORD),
        ("Next", ctypes.POINTER(IP_ADAPTER_ADDRESSES)),
        ("AdapterName", ctypes.c_char_p),
        ("FirstUnicastAddress", ctypes.POINTER(IP_ADAPTER_UNICAST_ADDRESS)),
        ("FirstAnycastAddress", ctypes.c_void_p),
        ("FirstMulticastAddress", ctypes.c_void_p),
        ("FirstDnsServerAddress", ctypes.POINTER(IP_ADAPTER_DNS_SERVER_ADDRESS)),
        ("DnsSuffix", wintypes.LPWSTR),
        ("Description", wintypes.LPWSTR),
        ("FriendlyName", wintypes.LPWSTR),
        ("PhysicalAddress", ctypes.c_ubyte * 8),
        ("PhysicalAddressLength", DWORD),
        ("Flags", DWORD),
        ("Mtu", DWORD),
        ("IfType", DWORD),
        ("OperStatus", ctypes.c_int),
        ("Ipv6IfIndex", DWORD),
        ("ZoneIndices", DWORD * 16),
        ("FirstPrefix", ctypes.c_void_p),
        ("TransmitLinkSpeed", ctypes.c_ulonglong),
        ("ReceiveLinkSpeed", ctypes.c_ulonglong),
        ("FirstWinsServerAddress", ctypes.c_void_p),
        ("FirstGatewayAddress", ctypes.POINTER(IP_ADAPTER_GATEWAY_ADDRESS)),
        ("Ipv4Metric", ULONG),
    )

    get_adapters_addresses = ctypes.windll.iphlpapi.GetAdaptersAddresses
    get_adapters_addresses.argtypes = (ULONG, ULONG, ctypes.c_void_p, ctypes.c_void_p, PULONG)
    get_adapters_addresses.restype = ULONG

    size = ULONG(0)
    get_adapters_addresses(AF_UNSPEC, GAA_FLAGS, None, None, ctypes.byref(size))
    if size.value <= 0:
        return []
    buffer = ctypes.create_string_buffer(size.value)
    result = get_adapters_addresses(AF_UNSPEC, GAA_FLAGS, None, buffer, ctypes.byref(size))
    if result != NO_ERROR:
        return []

    candidates: list[NetworkIdentityCandidate] = []
    adapter = ctypes.cast(buffer, ctypes.POINTER(IP_ADAPTER_ADDRESSES))
    while adapter:
        item = adapter.contents
        ip = _first_ipv4_address(item.FirstUnicastAddress, SOCKADDR_IN, AF_INET)
        ipv4_addresses = _ipv4_addresses(item.FirstUnicastAddress, SOCKADDR_IN, AF_INET)
        ip = ipv4_addresses[0] if ipv4_addresses else None
        if ip:
            mac_bytes = bytes(item.PhysicalAddress[: item.PhysicalAddressLength])
            mac = "-".join(f"{byte:02X}" for byte in mac_bytes[:6]) if len(mac_bytes) >= 6 else ""
            gateways = _socket_ipv4_addresses(item.FirstGatewayAddress, SOCKADDR_IN, AF_INET)
            dns_servers = _socket_ipv4_addresses(item.FirstDnsServerAddress, SOCKADDR_IN, AF_INET)
            prefix_length = _first_ipv4_prefix_length(item.FirstUnicastAddress, SOCKADDR_IN, AF_INET)
            candidates.append(
                NetworkIdentityCandidate(
                    ip=ip,
                    mac=mac,
                    friendly_name=item.FriendlyName or item.Description or "",
                    if_type=int(item.IfType),
                    oper_status_up=int(item.OperStatus) == 1,
                    has_gateway=bool(item.FirstGatewayAddress),
                    metric=int(item.Ipv4Metric),
                    description=item.Description or "",
                    adapter_name=(item.AdapterName or b"").decode(errors="ignore"),
                    adapter_type=_adapter_type_from_if_type(int(item.IfType)),
                    ip_addresses=tuple(ipv4_addresses),
                    gateway=gateways[0] if gateways else None,
                    dns_servers=tuple(dns_servers),
                    prefix_length=prefix_length,
                )
            )
        adapter = item.Next
    return candidates


def _candidate_name_text(candidate: NetworkIdentityCandidate) -> str:
    return " ".join(
        value
        for value in (candidate.friendly_name, candidate.description, candidate.adapter_name)
        if value
    )


def _candidate_adapter_type(candidate: NetworkIdentityCandidate) -> str:
    if candidate.adapter_type:
        return candidate.adapter_type
    return _adapter_type_from_if_type(candidate.if_type)


def _adapter_type_from_if_type(if_type: int) -> str:
    if if_type == IF_TYPE_ETHERNET_CSMACD:
        return "Ethernet"
    if if_type == IF_TYPE_IEEE80211:
        return "Wi-Fi"
    return "Unknown"


def _network_adapter_info_from_candidate(candidate: NetworkIdentityCandidate) -> NetworkAdapterInfo:
    return NetworkAdapterInfo(
        name=candidate.friendly_name or candidate.adapter_name or candidate.description or "Unknown",
        description=candidate.description or candidate.friendly_name,
        is_enabled=candidate.oper_status_up,
        mac_address=normalize_mac_address(candidate.mac) or candidate.mac or None,
        ip_addresses=candidate.ip_addresses or ((candidate.ip,) if candidate.ip else ()),
        subnet_mask=_prefix_length_to_subnet_mask(candidate.prefix_length) if candidate.prefix_length is not None else None,
        gateway=candidate.gateway,
        dns_servers=candidate.dns_servers,
        is_dhcp_enabled=None,
    )


def _adapter_type_from_name(name: str, description: str) -> str:
    lower = f"{name} {description}".lower()
    if any(token in lower for token in ("wi-fi", "wifi", "wireless", "wlan", "802.11", "무선")):
        return "Wi-Fi"
    return "Ethernet"


def _adapter_metric(adapter: NetworkAdapterInfo, candidates: list[NetworkIdentityCandidate]) -> int:
    for candidate in candidates:
        if adapter.name in {candidate.friendly_name, candidate.adapter_name, candidate.description}:
            return candidate.metric if candidate.metric not in (None, 0) else 2**31 - 1
    return 2**31 - 1


def _prefix_length_to_subnet_mask(prefix_length: int) -> str | None:
    if not 0 <= prefix_length <= 32:
        return None
    mask = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF
    return ".".join(str((mask >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def _first_ipv4_address(address, sockaddr_type, af_inet: int) -> str | None:
    addresses = _ipv4_addresses(address, sockaddr_type, af_inet)
    return addresses[0] if addresses else None


def _ipv4_addresses(address, sockaddr_type, af_inet: int) -> list[str]:
    addresses: list[str] = []
    current = address
    while current:
        socket_address = current.contents.Address
        if socket_address.lpSockaddr:
            sockaddr = ctypes_cast(socket_address.lpSockaddr, sockaddr_type)
            if int(sockaddr.sin_family) == af_inet:
                addresses.append(socket.inet_ntoa(bytes(sockaddr.sin_addr)))
        current = current.contents.Next
    return addresses


def _socket_ipv4_addresses(address, sockaddr_type, af_inet: int) -> list[str]:
    return _ipv4_addresses(address, sockaddr_type, af_inet)


def _first_ipv4_prefix_length(address, sockaddr_type, af_inet: int) -> int | None:
    current = address
    while current:
        socket_address = current.contents.Address
        if socket_address.lpSockaddr:
            sockaddr = ctypes_cast(socket_address.lpSockaddr, sockaddr_type)
            if int(sockaddr.sin_family) == af_inet:
                return int(getattr(current.contents, "OnLinkPrefixLength", 0))
        current = current.contents.Next
    return None


def ctypes_cast(pointer: object, target_type: object) -> object:
    import ctypes

    return ctypes.cast(pointer, ctypes.POINTER(target_type)).contents
