# SKHU PC Management

Python + PySide6 rewrite scaffold for the legacy C# WPF `SKHU_PC_Management` app.

## Scope

This repository contains the Python + PySide6 rewrite of the legacy desktop tool. Windows-changing operations are isolated behind ports/adapters and should be tested with fakes unless explicitly running an integration scenario on a Windows machine.

## Architecture

- `domain`: dataclass models and definitions with no framework or Windows dependencies.
- `application`: small dependency-injected use cases.
- `ports`: `typing.Protocol` contracts for external systems.
- `infrastructure`: Windows and license adapters.
- `presentation`: thin PySide6 GUI.

## Development

```powershell
python -m pip install -e .
python -m pytest
python -m skhu_pc_management.main
```

`python` must point to Python 3.12 or newer. Run tests before every release candidate, and keep Windows-changing checks behind fakes unless you are intentionally running a manual integration test on a Windows test PC.

## Safe UI Test Mode

Set `SKHU_PC_MANAGEMENT_TEST_MODE=1` before launching the app when using Computer Use, UI automation, or exploratory testing on a real PC. In this mode, read-only checks remain available, but buttons that can change Windows state are disabled.

PowerShell:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
python -m skhu_pc_management.main
```

For a packaged exe:

```powershell
$env:SKHU_PC_MANAGEMENT_TEST_MODE = "1"
.\dist\SKHU_PC_Management\SKHU_PC_Management.exe
```

Disabled in test mode:

- Basic settings apply.
- Static IP apply.
- DHCP switch.
- Windows activation preparation.
- Office activation preparation.
- Taskbar layout apply.

Allowed in test mode:

- PC information loading.
- Settings status check.
- Network adapter loading.
- PC checks, including browser history, power settings, and scheduled shutdown status.
- Resource validation and taskbar dry-run checks.

The UI displays `테스트 모드에서는 실제 설정 변경 기능이 비활성화됩니다.` and the guarded use cases return the same message if called directly.

## Product Keys

Real product keys must not be committed. Copy `src/skhu_pc_management/infrastructure/license/local_product_keys.example.py` to `src/skhu_pc_management/infrastructure/license/local_product_keys.py` only on a local build or deployment machine if a real provider is needed. `local_product_keys.py` is ignored by Git.

The activation tab reads version-specific constants first: `WINDOWS_11_PRODUCT_KEY`, `WINDOWS_10_PRODUCT_KEY`, `OFFICE_2024_PRODUCT_KEY`, and `OFFICE_2021_PRODUCT_KEY`. `WINDOWS_PRODUCT_KEY` and `OFFICE_PRODUCT_KEY` remain fallback values.

The old `secrets/product_keys.py` layout is no longer used because it can conflict with Python's standard library `secrets` module.

Do not print product keys in logs, test output, README files, or build scripts.

## PyInstaller Build

The app is Windows-only and should run with administrator privileges because several features configure system settings. The build script requests UAC elevation metadata with PyInstaller's `--uac-admin` option and builds a GUI executable without a console window.

Install dependencies first:

```powershell
python -m pip install -e .
python -m PyInstaller --version
```

If `python -m PyInstaller --version` fails, the packaging environment is not ready. Install the project dependencies before running the build script.

Default onedir build:

```powershell
.\scripts\build.ps1
```

Equivalent command when using a checked-in spec file:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller SKHU_PC_Management.spec --noconfirm
```

Expected output:

```text
dist\SKHU_PC_Management\
  SKHU_PC_Management.exe
  _internal\
    resources\
      images\skhu_logo.ico
      TaskBar.reg
      TaskBar\*.lnk
  README_RELEASE.txt
```

`scripts/build.ps1` is the official build entrypoint. The default onedir build uses the committed `SKHU_PC_Management.spec` file so hidden imports, UAC metadata, and resource inclusion stay stable.

After a build, verify the distribution folder:

```powershell
.\scripts\check_dist.ps1
```

Optional onefile build:

```powershell
.\scripts\build.ps1 -OneFile
```

Equivalent onefile command:

```powershell
python -m PyInstaller --name SKHU_PC_Management --onefile --windowed --uac-admin --clean --noconfirm --icon ".\resources\images\skhu_logo.ico" --paths .\src --add-data ".\resources;resources" --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --hidden-import wmi --hidden-import win32com --hidden-import win32com.client --hidden-import pythoncom --hidden-import pywintypes .\src\skhu_pc_management\main.py
```

`resources/` is included with `--add-data ".\resources;resources"`. In PyInstaller onedir builds, data files are usually placed under `_internal\resources`. The runtime resolver checks PyInstaller extraction paths, `_internal`, executable paths, and development paths, so the same code can resolve packaged resources and local resources.

`resources/images/skhu_logo.ico` is used for the PySide6 window icon and header logo. `resources/TaskBar.reg` and `resources/TaskBar/*.lnk` are validated by the taskbar resource checker and are included in the packaged resources directory.

The taskbar layout button currently performs a dry-run plan by default. It validates `TaskBar.reg`, lists `.lnk` shortcuts that would be copied, and shows the registry/import and Explorer-restart steps that would be required. It does not delete pinned taskbar files, run `regedit`, or restart Explorer unless a future explicit implementation adds that behavior behind a confirmation flow.

If the executable must include embedded product keys, create `src/skhu_pc_management/infrastructure/license/local_product_keys.py` on the local build machine before running `scripts/build.ps1`. Copy `local_product_keys.example.py` to `local_product_keys.py`, fill in real keys locally, and do not commit that file. The build script and spec add the hidden import for that local module only when the file exists.

Generated `build/`, `dist/`, and ad hoc `*.spec` files are ignored. `SKHU_PC_Management.spec` is intentionally committed as the fixed onedir packaging configuration.

Distribute the full `dist\SKHU_PC_Management\` directory for onedir builds. Do not include local-only secret files unless the deployment policy explicitly requires them on the target machine.

## Windows Test PC Procedure

Use this sequence on a real Windows test PC after copying the full onedir folder:

1. Run `SKHU_PC_Management.exe` and confirm the UAC prompt appears.
2. Check startup initialization: admin warning, PC info, settings status, and PC checks should load without crashing the app.
3. Confirm PC info displays CPU, RAM, OS, disk actual/rated size, BusType, TPM, Secure Boot, and boot mode.
4. Confirm settings status can be checked and settings application asks for confirmation before changing anything.
5. Confirm network adapters load and physical Ethernet/Wi-Fi adapters appear before disconnected or less relevant adapters.
6. Test DHCP/static IP only on a disposable test network profile.
7. Confirm PC checks show Korean messages for browser history, power settings, scheduled shutdown, and program versions.
8. Confirm activation buttons never display the product key. If `local_product_keys.py` is absent, the Korean missing-file message should appear.
9. Confirm taskbar resource validation/dry-run shows what would happen and does not modify the taskbar.
10. Close and reopen the app to verify repeat startup behavior.

## Release Checklist

Use `RELEASE_CHECKLIST.md` before packaging or handing the app to a test PC. The checklist covers startup initialization, settings, network, PC info, PC checks, activation, resources/taskbar behavior, busy-state guards, pytest, and PyInstaller.

The following operations require a real Windows test PC and must not be exercised by default unit tests:

- Registry writes for default settings.
- IP/DHCP changes through netsh.
- Clipboard/process launch for activation.
- powercfg and ScheduledTasks integration behavior.
- Taskbar layout changes, regedit, and Explorer restart.

Taskbar layout support currently validates resources and returns a dry-run plan. Actual taskbar modification remains a TODO and must be implemented only with an explicit user confirmation and rollback/backup policy.

## Repository Visibility

`legacy/csharp/` is read-only reference material for migration decisions and must not be modified during Python work. Keep `AGENTS.md` in Git so Codex and GitHub tooling can see the repository rules. If a local `.git/info/exclude` hides `legacy/` or `AGENTS.md`, those files will not appear as untracked files locally; remove those local-only exclude entries before staging them intentionally.
