"""Persistencia local de escenarios en JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from API.domain.escenarios import validar_escenario


class AlmacenamientoJSON:
    """Guarda y carga escenarios completos en archivos JSON UTF-8."""

    def guardar(self, escenario: dict[str, Any], ruta: str | Path) -> Path:
        errores = validar_escenario(escenario)
        if errores:
            raise ValueError("No se guardó el escenario:\n- " + "\n- ".join(errores))
        destino = Path(ruta)
        if destino.suffix.lower() != ".json":
            destino = destino.with_suffix(".json")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(escenario, ensure_ascii=False, indent=2), encoding="utf-8")
        return destino

    def cargar(self, ruta: str | Path) -> dict[str, Any]:
        origen = Path(ruta)
        try:
            escenario = json.loads(origen.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"El archivo '{origen.name}' no contiene JSON válido (línea {exc.lineno}).") from exc
        except OSError as exc:
            raise ValueError(f"No se pudo leer '{origen}': {exc.strerror or exc}.") from exc
        errores = validar_escenario(escenario)
        if errores:
            raise ValueError("El archivo tiene datos inválidos:\n- " + "\n- ".join(errores))
        return escenario
