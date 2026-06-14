from __future__ import annotations

from pathlib import Path

from skhu_pc_management.infrastructure.windows.browser_data_reader import WindowsBrowserDataReader


def test_chrome_user_data_root_missing_is_treated_as_clean(tmp_path: Path) -> None:
    status = WindowsBrowserDataReader(tmp_path).get_browser_data_status("chrome")

    assert status.path_exists is False
    assert status.size_bytes == 0
    assert status.has_history is False


def test_chrome_profile_history_is_checked_without_default_profile(tmp_path: Path) -> None:
    profile = tmp_path / "Google" / "Chrome" / "User Data" / "Profile 1"
    profile.mkdir(parents=True)
    (profile / "History").write_bytes(b"x")

    status = WindowsBrowserDataReader(tmp_path).get_browser_data_status("chrome")

    assert status.path_exists is True
    assert status.additional_profiles == ("Profile 1",)
    assert status.has_history is True


def test_edge_guest_profile_is_checked(tmp_path: Path) -> None:
    profile = tmp_path / "Microsoft" / "Edge" / "User Data" / "Guest Profile"
    profile.mkdir(parents=True)
    (profile / "Cache").mkdir()
    (profile / "Cache" / "data.bin").write_bytes(b"x")

    status = WindowsBrowserDataReader(tmp_path).get_browser_data_status("edge")

    assert status.path_exists is True
    assert status.additional_profiles == ("Guest Profile",)
    assert status.has_history is True


def test_browser_data_reader_stops_after_threshold(tmp_path: Path) -> None:
    default = tmp_path / "Google" / "Chrome" / "User Data" / "Default"
    default.mkdir(parents=True)
    (default / "History").write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    cache = default / "Cache"
    cache.mkdir()
    (cache / "ignored.bin").write_bytes(b"y" * 1024)

    status = WindowsBrowserDataReader(tmp_path).get_browser_data_status("chrome")

    assert status.has_history is True
    assert status.size_bytes == 5 * 1024 * 1024 + 1


def test_browser_data_reader_ignores_inaccessible_files(tmp_path: Path, monkeypatch) -> None:
    default = tmp_path / "Google" / "Chrome" / "User Data" / "Default"
    default.mkdir(parents=True)
    history = default / "History"
    history.write_bytes(b"x")
    original_stat = Path.stat

    def fake_stat(self: Path, *args, **kwargs):
        if self == history:
            raise OSError("locked")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    status = WindowsBrowserDataReader(tmp_path).get_browser_data_status("chrome")

    assert status.has_history is False
    assert status.skipped_inaccessible_count == 1


def test_browser_data_reader_checks_edge_default_profile(tmp_path: Path) -> None:
    default = tmp_path / "Microsoft" / "Edge" / "User Data" / "Default"
    default.mkdir(parents=True)
    (default / "History").write_bytes(b"x" * (5 * 1024 * 1024 + 1))

    status = WindowsBrowserDataReader(tmp_path).get_browser_data_status("edge")

    assert status.path_exists is True
    assert status.has_history is True
