"""Acceso a disco. Cada escenario se almacena como un archivo JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class EscenarioRepository:
    def __init__(self, directorio: str | Path | None = None):
        self.directorio = Path(directorio) if directorio else Path(__file__).resolve().parents[1] / "data" / "escenarios"
        self.directorio.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validar_id(escenario_id: str) -> str:
        if not isinstance(escenario_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", escenario_id):
            raise ValueError("El id solo puede contener letras, números, guion y guion bajo (máximo 64 caracteres).")
        return escenario_id

    def listar(self) -> list[dict[str, Any]]:
        items = []
        for archivo in sorted(self.directorio.glob("*.json")):
            try:
                contenido = json.loads(archivo.read_text(encoding="utf-8"))
                items.append({"id": contenido["id"], "nombre": contenido.get("nombre", contenido["id"])})
            except (OSError, ValueError, KeyError, TypeError):
                # No se detiene la API si alguien dejó un archivo corrupto en la carpeta.
                continue
        return items

    def obtener(self, escenario_id: str) -> dict[str, Any]:
        ruta = self._ruta(escenario_id)
        if not ruta.exists():
            raise KeyError(f"No existe el escenario '{escenario_id}'.")
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"No se pudo leer el escenario '{escenario_id}': {exc}.") from exc

    def guardar(self, documento: dict[str, Any], crear: bool = False) -> dict[str, Any]:
        escenario_id = self.validar_id(documento.get("id", ""))
        ruta = self._ruta(escenario_id)
        if crear and ruta.exists():
            raise FileExistsError(f"Ya existe el escenario '{escenario_id}'.")
        ruta.write_text(json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8")
        return documento

    def eliminar(self, escenario_id: str) -> None:
        ruta = self._ruta(escenario_id)
        if not ruta.exists():
            raise KeyError(f"No existe el escenario '{escenario_id}'.")
        ruta.unlink()

    def _ruta(self, escenario_id: str) -> Path:
        return self.directorio / f"{self.validar_id(escenario_id)}.json"
