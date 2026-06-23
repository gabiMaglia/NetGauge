# Contribuir a NetGauge

¡Gracias por el interés! Es un proyecto chico y se agradecen issues y PRs.

## Setup

```powershell
git clone https://github.com/gabiMaglia/NetGauge
cd NetGauge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
```

Para el desglose por aplicación (ETW) hay que ejecutar **como Administrador**.

## Arquitectura

El proyecto sigue **Clean Architecture** (ver [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)).
La regla de oro: **el dominio (`src/domain/`) no importa nada de afuera**. La UI,
SQLite, ETW, etc. son detalles en `infrastructure/` y `presentation/` que
implementan los puertos de `domain/ports.py`.

## Estilo

- **Conventional commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `ci:`).
- Tests con `pytest` para lógica de dominio/aplicación.
- Build y empaquetado: ver [`docs/BUILD.md`](docs/BUILD.md).

## Antes de abrir un PR

- Que `pytest` pase.
- Mantené el cambio enfocado; si toca UI, probá en claro y oscuro.
- Actualizá `CHANGELOG.md` si el cambio es visible para el usuario.
