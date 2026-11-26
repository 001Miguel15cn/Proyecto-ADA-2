"""Importación de escenarios completos en JSON o CSV normalizado.

El CSV usa un registro JSON por fila en la columna ``datos``. Esto permite
mantener inventarios y demandas anidados sin perder la sencillez de CSV.
Columnas requeridas: ``seccion,id,datos``. Secciones: tipos_ayuda, centros,
zonas, rutas, incompatibilidades. Prioridades/opciones se especifican una vez
como filas ``prioridades`` y ``opciones`` con ``id`` vacío.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from API.repositories.archivo_json_repository import AlmacenamientoJSON
from API.domain.escenarios import crear_escenario_vacio, validar_escenario


def importar_csv(ruta: str | Path) -> dict[str, Any]:
    origen = Path(ruta)
    try:
        texto = origen.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ValueError(f"No se pudo leer '{origen}': {exc.strerror or exc}.") from exc
    return importar_csv_texto(texto)


def importar_csv_texto(texto: str) -> dict[str, Any]:
    """Interpreta texto CSV sin escribirlo temporalmente en disco."""
    escenario = crear_escenario_vacio()
    lector = csv.DictReader(io.StringIO(texto, newline=""))
    requeridas = {"seccion", "id", "datos"}
    if not lector.fieldnames or not requeridas.issubset(lector.fieldnames):
        raise ValueError("El CSV debe tener las columnas: seccion,id,datos.")
    for fila_num, fila in enumerate(lector, start=2):
        seccion = (fila.get("seccion") or "").strip()
        try:
            datos = json.loads(fila.get("datos") or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Fila {fila_num}: la columna 'datos' debe contener JSON válido.") from exc
        if seccion in ("tipos_ayuda", "centros", "zonas", "rutas", "incompatibilidades"):
            if not isinstance(datos, dict):
                raise ValueError(f"Fila {fila_num}: 'datos' debe ser un objeto JSON.")
            if fila.get("id") and "id" not in datos:
                datos["id"] = fila["id"].strip()
            escenario.setdefault(seccion, []).append(datos)
        elif seccion in ("prioridades", "opciones"):
            if not isinstance(datos, dict):
                raise ValueError(f"Fila {fila_num}: 'datos' debe ser un objeto JSON.")
            escenario[seccion] = datos
        else:
            raise ValueError(f"Fila {fila_num}: sección desconocida '{seccion}'.")
    errores = validar_escenario(escenario)
    if errores:
        raise ValueError("El CSV tiene datos inválidos:\n- " + "\n- ".join(errores))
    return escenario


def cargar_escenario_contenido(nombre_archivo: str, contenido: bytes) -> dict[str, Any]:
    """Carga y valida un JSON o CSV recibido en memoria por HTTP."""
    extension = Path(nombre_archivo).suffix.lower()
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("El archivo debe estar codificado como UTF-8.") from exc
    if extension == ".csv":
        return importar_csv_texto(texto)
    if extension == ".json":
        try:
            escenario = json.loads(texto)
        except json.JSONDecodeError as exc:
            raise ValueError(f"El JSON no es válido (línea {exc.lineno}, columna {exc.colno}).") from exc
        errores = validar_escenario(escenario)
        if errores:
            raise ValueError("El archivo tiene datos inválidos:\n- " + "\n- ".join(errores))
        return escenario
    raise ValueError("Formato no admitido. Sube un archivo .json o .csv.")


def cargar_escenario(ruta: str | Path) -> dict[str, Any]:
    """Detecta formato por extensión y carga un escenario validado."""
    origen = Path(ruta)
    extension = origen.suffix.lower()
    if extension == ".json":
        return AlmacenamientoJSON().cargar(origen)
    if extension == ".csv":
        return importar_csv(origen)
    raise ValueError("Formato no admitido. Usa un archivo .json o .csv.")
