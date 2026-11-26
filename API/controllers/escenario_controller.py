"""Endpoints REST. Aquí solo se traducen HTTP y errores; reglas en services."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from API.dto import (
    EscenarioCreateDTO,
    EscenarioDTO,
    EscenarioDatosDTO,
    EscenarioResumenDTO,
    PrioridadesDTO,
    ValidacionDTO,
)
from API.services import EscenarioService


router = APIRouter(prefix="/api/escenarios", tags=["Escenarios"])
service = EscenarioService()


def _llamar(funcion, *args, **kwargs):
    try:
        return funcion(*args, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'")) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[EscenarioResumenDTO])
def listar_escenarios():
    return service.listar()


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_escenario(body: EscenarioCreateDTO) -> EscenarioDTO:
    return _llamar(service.crear, body.id, body.nombre)


@router.get("/{escenario_id}", response_model=EscenarioDTO)
def obtener_escenario(escenario_id: str) -> EscenarioDTO:
    return _llamar(service.obtener, escenario_id)


@router.put("/{escenario_id}", response_model=EscenarioDTO)
def reemplazar_escenario(escenario_id: str, body: EscenarioDatosDTO) -> EscenarioDTO:
    datos = body.model_dump(mode="json")
    return _llamar(service.reemplazar_datos, escenario_id, datos)


@router.delete("/{escenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_escenario(escenario_id: str):
    _llamar(service.eliminar_escenario, escenario_id)


@router.get("/{escenario_id}/secciones/{seccion}")
def obtener_seccion(escenario_id: str, seccion: str):
    return _llamar(service.obtener_seccion, escenario_id, seccion)


@router.post("/{escenario_id}/secciones/{seccion}")
def agregar_registro(escenario_id: str, seccion: str, body: dict[str, Any]):
    return _llamar(service.agregar, escenario_id, seccion, body)


@router.put("/{escenario_id}/secciones/{seccion}/{ident}")
def actualizar_registro(escenario_id: str, seccion: str, ident: str, body: dict[str, Any]):
    return _llamar(service.actualizar, escenario_id, seccion, ident, body)


@router.delete("/{escenario_id}/secciones/{seccion}/{ident}")
def eliminar_registro(escenario_id: str, seccion: str, ident: str):
    return _llamar(service.eliminar, escenario_id, seccion, ident)


@router.put("/{escenario_id}/prioridades")
def definir_prioridades(escenario_id: str, body: PrioridadesDTO) -> EscenarioDTO:
    return _llamar(service.definir_prioridades, escenario_id, body.root)


@router.post("/{escenario_id}/validar")
def validar_escenario(escenario_id: str) -> ValidacionDTO:
    return _llamar(service.validar, escenario_id)


@router.post("/{escenario_id}/optimizar")
def optimizar_escenario(escenario_id: str):
    return _llamar(service.optimizar, escenario_id)
