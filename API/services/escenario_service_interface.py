"""Contrato de la capa de aplicación para gestionar escenarios."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EscenarioServiceInterface(ABC):
    """Operaciones disponibles para los controllers, independientes de la implementación."""

    @abstractmethod
    def listar(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def crear(self, escenario_id: str, nombre: str | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def obtener(self, escenario_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def reemplazar_datos(self, escenario_id: str, datos: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def importar_archivo(
        self, escenario_id: str, nombre_archivo: str, contenido: bytes
    ) -> dict[str, Any]: ...

    @abstractmethod
    def agregar(self, escenario_id: str, seccion: str, registro: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def actualizar(
        self, escenario_id: str, seccion: str, ident: str, cambios: dict[str, Any]
    ) -> dict[str, Any]: ...

    @abstractmethod
    def eliminar(self, escenario_id: str, seccion: str, ident: str) -> dict[str, Any]: ...

    @abstractmethod
    def obtener_seccion(self, escenario_id: str, seccion: str) -> Any: ...

    @abstractmethod
    def definir_prioridades(self, escenario_id: str, prioridades: dict[str, float]) -> dict[str, Any]: ...

    @abstractmethod
    def validar(self, escenario_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def optimizar(self, escenario_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def eliminar_escenario(self, escenario_id: str) -> None: ...
