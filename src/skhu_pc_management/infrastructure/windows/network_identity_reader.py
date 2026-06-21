from __future__ import annotations

from dataclasses import dataclass
import socket


IF_TYPE_ETHERNET_CSMACD = 6
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


def read_network_identity() -> tuple[str, str] | None:
    try:
        candidates = _get_adapters_addresses_candidates()
    except Exception:
        return None
    selected = select_network_identity_candidate(candidates)
    if selected is None:
        return "연결된 이더넷 없음", "알 수 없음"
    return selected.ip, normalize_mac_address(selected.mac) or "알 수 없음"


def select_network_identity_candidate(candidates: list[NetworkIdentityCandidate]) -> NetworkIdentityCandidate | None:
    filtered = [
        candidate
        for candidate in candidates
        if candidate.oper_status_up
        and candidate.if_type == IF_TYPE_ETHERNET_CSMACD
        and candidate.if_type != IF_TYPE_SOFTWARE_LOOPBACK
        and candidate.ip
        and not is_excluded_adapter_name(candidate.friendly_name)
    ]
    if not filtered:
        return None
    return sorted(
        filtered,
        key=lambda candidate: (
            not candidate.has_gateway,
            candidate.metric if candidate.metric not in (None, 0) else 2**31 - 1,
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
    GAA_FLAGS = 0x0002 | 0x0004 | 0x0008

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
    )

    class IP_ADAPTER_GATEWAY_ADDRESS(ctypes.Structure):
        pass

    IP_ADAPTER_GATEWAY_ADDRESS._fields_ = (
        ("Length", ULONG),
        ("Reserved", DWORD),
        ("Next", ctypes.POINTER(IP_ADAPTER_GATEWAY_ADDRESS)),
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
        ("FirstDnsServerAddress", ctypes.c_void_p),
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
        if ip:
            mac_bytes = bytes(item.PhysicalAddress[: item.PhysicalAddressLength])
            mac = "-".join(f"{byte:02X}" for byte in mac_bytes[:6]) if len(mac_bytes) >= 6 else ""
            candidates.append(
                NetworkIdentityCandidate(
                    ip=ip,
                    mac=mac,
                    friendly_name=item.FriendlyName or item.Description or "",
                    if_type=int(item.IfType),
                    oper_status_up=int(item.OperStatus) == 1,
                    has_gateway=bool(item.FirstGatewayAddress),
                    metric=int(item.Ipv4Metric),
                )
            )
        adapter = item.Next
    return candidates


def _first_ipv4_address(address, sockaddr_type, af_inet: int) -> str | None:
    current = address
    while current:
        socket_address = current.contents.Address
        if socket_address.lpSockaddr:
            sockaddr = ctypes_cast(socket_address.lpSockaddr, sockaddr_type)
            if int(sockaddr.sin_family) == af_inet:
                return socket.inet_ntoa(bytes(sockaddr.sin_addr))
        current = current.contents.Next
    return None


def ctypes_cast(pointer: object, target_type: object) -> object:
    import ctypes

    return ctypes.cast(pointer, ctypes.POINTER(target_type)).contents
