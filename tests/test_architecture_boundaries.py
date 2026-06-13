from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _python_files_under(relative_path: str) -> list[Path]:
    return list((PROJECT_ROOT / relative_path).rglob("*.py"))


def test_domain_and_application_do_not_import_gui_or_windows_apis() -> None:
    forbidden_tokens = (
        "PySide6",
        "winreg",
        "subprocess",
        "wmi",
        "WMI",
        "netsh",
        "powercfg",
    )

    for relative_path in ("src/skhu_pc_management/domain", "src/skhu_pc_management/application"):
        for path in _python_files_under(relative_path):
            source = path.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                assert token not in source, f"{token} must not appear in {path}"
