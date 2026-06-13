# SKHU PC Management

Python + PySide6 rewrite scaffold for the legacy C# WPF `SKHU_PC_Management` app.

## Scope

This repository currently contains the initial architecture scaffold only. It does not perform real Windows configuration changes.

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

Real product keys must not be committed. Copy `secrets/product_keys.example.py` to `secrets/product_keys.py` locally if a real provider is needed.
