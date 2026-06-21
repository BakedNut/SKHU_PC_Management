from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DxgiGpuInfo:
    name: str
    dedicated_memory_bytes: int | None
    shared_memory_bytes: int | None = None
    vendor_id: int | None = None
    flags: int = 0
    is_integrated: bool = False
    is_basic_display: bool = False
    is_virtual: bool = False


DXGI_ADAPTER_FLAG_SOFTWARE = 2
INTEL_VENDOR_ID = 0x8086
INTEGRATED_DEDICATED_THRESHOLD_BYTES = 512 * 1024**2


def read_dxgi_gpu_info() -> tuple[str, str, list[str]] | None:
    try:
        adapters = _enumerate_dxgi_adapters()
    except Exception:
        return None

    selected = select_representative_dxgi_gpu(adapters)
    if selected is None:
        return None
    return selected.name, format_dxgi_gpu_memory(selected), [selected.name]


def select_representative_dxgi_gpu(adapters: list[DxgiGpuInfo]) -> DxgiGpuInfo | None:
    best_physical: DxgiGpuInfo | None = None
    virtual_fallback: DxgiGpuInfo | None = None
    has_basic_display = False

    for adapter in adapters:
        if adapter.is_basic_display:
            has_basic_display = True
            continue
        if adapter.flags & DXGI_ADAPTER_FLAG_SOFTWARE:
            continue
        if adapter.is_virtual:
            if virtual_fallback is None:
                virtual_fallback = adapter
            continue
        if best_physical is None or (adapter.dedicated_memory_bytes or 0) > (best_physical.dedicated_memory_bytes or 0):
            best_physical = adapter

    if best_physical is not None:
        return best_physical
    if virtual_fallback is not None:
        return virtual_fallback
    if has_basic_display:
        return DxgiGpuInfo("드라이버 없음", None, is_basic_display=True)
    return None


def normalize_dxgi_adapter(raw: DxgiGpuInfo) -> DxgiGpuInfo:
    is_basic = is_basic_display_adapter_name(raw.name)
    is_virtual = is_virtual_display_adapter_name(raw.name)
    is_integrated = is_integrated_dxgi_gpu(
        vendor_id=raw.vendor_id,
        dedicated_memory_bytes=raw.dedicated_memory_bytes,
        shared_memory_bytes=raw.shared_memory_bytes,
    )
    return DxgiGpuInfo(
        name=raw.name.strip(),
        dedicated_memory_bytes=raw.dedicated_memory_bytes,
        shared_memory_bytes=raw.shared_memory_bytes,
        vendor_id=raw.vendor_id,
        flags=raw.flags,
        is_integrated=is_integrated,
        is_basic_display=is_basic,
        is_virtual=is_virtual,
    )


def is_basic_display_adapter_name(name: str) -> bool:
    lower = name.lower()
    return any(
        token in lower
        for token in (
            "microsoft basic display adapter",
            "microsoft 기본 디스플레이 어댑터",
            "기본 디스플레이 어댑터",
        )
    )


def is_virtual_display_adapter_name(name: str) -> bool:
    lower = name.lower()
    return any(
        token in lower
        for token in (
            "virtual",
            "vmware",
            "virtualbox",
            "vbox",
            "hyper-v",
            "parallels",
            "citrix",
            "remote display",
            "rdp",
            "indirect display",
            "mirror",
            "basic render",
        )
    )


def is_integrated_dxgi_gpu(
    *,
    vendor_id: int | None,
    dedicated_memory_bytes: int | None,
    shared_memory_bytes: int | None,
) -> bool:
    dedicated = dedicated_memory_bytes or 0
    shared = shared_memory_bytes or 0
    if dedicated <= 0:
        return True
    return vendor_id == INTEL_VENDOR_ID and dedicated <= INTEGRATED_DEDICATED_THRESHOLD_BYTES and shared > dedicated


def format_dxgi_gpu_memory(adapter: DxgiGpuInfo | None) -> str:
    if adapter is None:
        return "알 수 없음"
    if adapter.is_basic_display:
        return "알 수 없음"
    if adapter.is_integrated:
        return "없음(내장그래픽)"
    if not adapter.dedicated_memory_bytes:
        return "알 수 없음"
    gb = max(1, round(adapter.dedicated_memory_bytes / 1024**3))
    return f"{gb}GB"


def _enumerate_dxgi_adapters() -> list[DxgiGpuInfo]:
    import ctypes
    from ctypes import wintypes

    HRESULT = ctypes.c_long

    class GUID(ctypes.Structure):
        _fields_ = (
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        )

    class LUID(ctypes.Structure):
        _fields_ = (("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG))

    class DXGI_ADAPTER_DESC1(ctypes.Structure):
        _fields_ = (
            ("Description", wintypes.WCHAR * 128),
            ("VendorId", wintypes.UINT),
            ("DeviceId", wintypes.UINT),
            ("SubSysId", wintypes.UINT),
            ("Revision", wintypes.UINT),
            ("DedicatedVideoMemory", ctypes.c_size_t),
            ("DedicatedSystemMemory", ctypes.c_size_t),
            ("SharedSystemMemory", ctypes.c_size_t),
            ("AdapterLuid", LUID),
            ("Flags", wintypes.UINT),
        )

    def method(ptr: ctypes.c_void_p, index: int, restype: object, *argtypes: object) -> object:
        vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        prototype = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
        return prototype(vtable[index])

    factory_iid = GUID(
        0x770AAE78,
        0xF26F,
        0x4DBA,
        (ctypes.c_ubyte * 8)(0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87),
    )
    factory = ctypes.c_void_p()
    create_factory = ctypes.windll.dxgi.CreateDXGIFactory1
    create_factory.argtypes = (ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))
    create_factory.restype = HRESULT
    hr = create_factory(ctypes.byref(factory_iid), ctypes.byref(factory))
    if hr < 0 or not factory.value:
        return []

    adapters: list[DxgiGpuInfo] = []
    enum_adapters1 = method(factory, 12, HRESULT, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p))
    release_factory = method(factory, 2, wintypes.ULONG)
    try:
        index = 0
        while True:
            adapter = ctypes.c_void_p()
            hr = enum_adapters1(factory, index, ctypes.byref(adapter))
            if hr != 0 or not adapter.value:
                break
            get_desc1 = method(adapter, 10, HRESULT, ctypes.POINTER(DXGI_ADAPTER_DESC1))
            release_adapter = method(adapter, 2, wintypes.ULONG)
            try:
                desc = DXGI_ADAPTER_DESC1()
                if get_desc1(adapter, ctypes.byref(desc)) >= 0:
                    adapters.append(
                        normalize_dxgi_adapter(
                            DxgiGpuInfo(
                                name=str(desc.Description).strip(),
                                dedicated_memory_bytes=int(desc.DedicatedVideoMemory),
                                shared_memory_bytes=int(desc.SharedSystemMemory),
                                vendor_id=int(desc.VendorId),
                                flags=int(desc.Flags),
                            )
                        )
                    )
            finally:
                release_adapter(adapter)
            index += 1
    finally:
        release_factory(factory)
    return adapters
