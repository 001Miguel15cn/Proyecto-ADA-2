"""DTOs HTTP para validar y documentar el contrato REST de escenarios.

Los DTO validan la forma y tipos de la petición. Las reglas cruzadas del
problema (por ejemplo, que una ruta use centros existentes) siguen en domain.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel


class DTOBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class TipoAyudaDTO(DTOBase):
    id: str = Field(min_length=1)
    divisible: bool = True
    volumen: float = Field(default=1, gt=0)
    importancia: float = Field(default=1, ge=0)


class CentroDTO(DTOBase):
    id: str = Field(min_length=1)
    activo: bool = True
    cap_despacho: float = Field(default=0, ge=0)
    inventario: dict[str, float] = Field(default_factory=dict)
    reserva: dict[str, float] = Field(default_factory=dict)


class ZonaDTO(DTOBase):
    id: str = Field(min_length=1)
    poblacion: float = Field(default=0, ge=0)
    prioridad: str = Field(min_length=1)
    demanda: dict[str, float] = Field(default_factory=dict)
    cobertura_minima: float = Field(default=0, ge=0, le=1)


class RutaDTO(DTOBase):
    origen: str = Field(min_length=1)
    destino: str = Field(min_length=1)
    disponible: bool = True
    costo: float = Field(default=0, ge=0)
    capacidad: float = Field(default=0, ge=0)


class IncompatibilidadDTO(DTOBase):
    centro: str = Field(min_length=1)
    ayuda: str = Field(min_length=1)


class OpcionesDTO(DTOBase):
    ponderar_por_poblacion: bool = False


class EscenarioDatosDTO(DTOBase):
    tipos_ayuda: list[TipoAyudaDTO] = Field(default_factory=list)
    prioridades: dict[str, float] = Field(default_factory=dict)
    centros: list[CentroDTO] = Field(default_factory=list)
    zonas: list[ZonaDTO] = Field(default_factory=list)
    rutas: list[RutaDTO] = Field(default_factory=list)
    incompatibilidades: list[IncompatibilidadDTO] = Field(default_factory=list)
    opciones: OpcionesDTO = Field(default_factory=OpcionesDTO)


class EscenarioCreateDTO(DTOBase):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    nombre: str | None = Field(default=None, max_length=120)


class EscenarioDTO(DTOBase):
    id: str
    nombre: str
    datos: EscenarioDatosDTO


class EscenarioResumenDTO(BaseModel):
    id: str
    nombre: str


class PrioridadesDTO(RootModel[dict[str, float]]):
    """El body HTTP es directamente un objeto JSON de nombre a peso."""


class ValidacionDTO(BaseModel):
    valido: bool
    errores: list[str]


class ErrorDTO(BaseModel):
    detail: str
