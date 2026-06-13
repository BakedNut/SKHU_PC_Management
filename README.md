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

## Product Keys

Real product keys must not be committed. Copy `secrets/product_keys.example.py` to `secrets/product_keys.py` only on a local build or deployment machine if a real provider is needed. `secrets/product_keys.py` is ignored by Git.

Do not print product keys in logs, test output, README files, or build scripts.

## PyInstaller Build

The app is Windows-only and should run with administrator privileges because several features configure system settings. The build script requests UAC elevation metadata with PyInstaller's `--uac-admin` option and builds a GUI executable without a console window.

Install dependencies first:

```powershell
python -m pip install -e .
```

Default onedir build:

```powershell
.\scripts\build.ps1
```

Expected output:

```text
dist\SKHU_PC_Management\SKHU_PC_Management.exe
```

Optional onefile build:

```powershell
.\scripts\build.ps1 -OneFile
```

Equivalent onefile command:

```powershell
python -m PyInstaller --name SKHU_PC_Management --onefile --windowed --uac-admin --clean --noconfirm --paths .\src --add-data ".\resources;resources" .\src\skhu_pc_management\main.py
```

`resources/` is included with `--add-data ".\resources;resources"`. The runtime resolver checks PyInstaller extraction paths and development paths, so the same code can resolve packaged resources and local resources.

Generated `build/`, `dist/`, and `*.spec` files are ignored. The committed build entrypoint is `scripts/build.ps1`; regenerate PyInstaller spec files locally when needed.

Distribute the full `dist\SKHU_PC_Management\` directory for onedir builds. Do not include local-only secret files unless the deployment policy explicitly requires them on the target machine.
