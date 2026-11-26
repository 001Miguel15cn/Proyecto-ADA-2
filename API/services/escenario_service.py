"""Reglas de negocio entre la API, gestión de datos y optimizador."""

from __future__ import annotations

import copy
from typing import Any

from API.domain.escenarios import GestorEscenarios, crear_escenario_vacio, validar_escenario
from API.repositories import EscenarioRepository
from API.services.escenario_service_interface import EscenarioServiceInterface
from API.services.importacion_service import cargar_escenario_contenido


SECCIONES = {"tipos_ayuda", "centros", "zonas", "rutas"}


class EscenarioServiceImpl(EscenarioServiceInterface):
    def __init__(self, repositorio: EscenarioRepository | None = None):
        self.repositorio = repositorio or EscenarioRepository()

    def listar(self) -> list[dict[str, Any]]:
        return self.repositorio.listar()

    def crear(self, escenario_id: str, nombre: str | None = None) -> dict[str, Any]:
        documento = {"id": escenario_id, "nombre": nombre or escenario_id, "datos": crear_escenario_vacio()}
        self.repositorio.guardar(documento, crear=True)
        return documento

    def obtener(self, escenario_id: str) -> dict[str, Any]:
        return self.repositorio.obtener(escenario_id)

    def reemplazar_datos(self, escenario_id: str, datos: dict[str, Any]) -> dict[str, Any]:
        documento = self.obtener(escenario_id)
        documento["datos"] = copy.deepcopy(datos)
        return self.repositorio.guardar(documento)

    def importar_archivo(
        self, escenario_id: str, nombre_archivo: str, contenido: bytes
    ) -> dict[str, Any]:
        datos = cargar_escenario_contenido(nombre_archivo, contenido)
        return self.reemplazar_datos(escenario_id, datos)

    def agregar(self, escenario_id: str, seccion: str, registro: dict[str, Any]) -> dict[str, Any]:
        self._validar_seccion(seccion)
        documento = self.obtener(escenario_id)
        gestor = GestorEscenarios(documento["datos"], validar_inicial=False)
        gestor.agregar(seccion, registro)
        documento["datos"] = gestor.obtener_escenario(validar=False)
        return self.repositorio.guardar(documento)

    def actualizar(self, escenario_id: str, seccion: str, ident: str, cambios: dict[str, Any]) -> dict[str, Any]:
        self._validar_seccion(seccion)
        documento = self.obtener(escenario_id)
        gestor = GestorEscenarios(documento["datos"], validar_inicial=False)
        gestor.actualizar(seccion, ident, cambios)
        documento["datos"] = gestor.obtener_escenario(validar=False)
        return self.repositorio.guardar(documento)

    def eliminar(self, escenario_id: str, seccion: str, ident: str) -> dict[str, Any]:
        self._validar_seccion(seccion)
        documento = self.obtener(escenario_id)
        gestor = GestorEscenarios(documento["datos"], validar_inicial=False)
        gestor.eliminar(seccion, ident)
        documento["datos"] = gestor.obtener_escenario(validar=False)
        return self.repositorio.guardar(documento)

    def obtener_seccion(self, escenario_id: str, seccion: str) -> Any:
        documento = self.obtener(escenario_id)
        if seccion not in (*SECCIONES, "prioridades", "incompatibilidades", "opciones"):
            raise ValueError(f"Sección desconocida: '{seccion}'.")
        return copy.deepcopy(documento["datos"].get(seccion, [] if seccion in SECCIONES else {}))

    def definir_prioridades(self, escenario_id: str, prioridades: dict[str, float]) -> dict[str, Any]:
        documento = self.obtener(escenario_id)
        documento["datos"]["prioridades"] = copy.deepcopy(prioridades)
        return self.repositorio.guardar(documento)

    def validar(self, escenario_id: str) -> dict[str, Any]:
        errores = validar_escenario(self.obtener(escenario_id)["datos"])
        return {"valido": not errores, "errores": errores}

    def optimizar(self, escenario_id: str) -> dict[str, Any]:
        documento = self.obtener(escenario_id)
        errores = validar_escenario(documento["datos"])
        if errores:
            return {"estado": "Datos invalidos", "errores": errores}
        # Importación diferida: mantener accesible la API aunque PuLP no esté instalado.
        from Modelo.optimizador import optimizar
        resultado = optimizar(documento["datos"])
        return self._serializar_resultado(resultado)

    def eliminar_escenario(self, escenario_id: str) -> None:
        self.repositorio.eliminar(escenario_id)

    @staticmethod
    def _serializar_resultado(resultado: dict[str, Any]) -> dict[str, Any]:
        """Adapta las claves compuestas del modelo a estructuras JSON válidas."""
        serializado = dict(resultado)

        for campo, columnas in (
            ("envios", ("centro", "zona", "tipo_ayuda")),
            ("demanda_atendida", ("zona", "tipo_ayuda")),
            ("demanda_no_atendida", ("zona", "tipo_ayuda")),
        ):
            valores = resultado.get(campo)
            if isinstance(valores, dict) and any(isinstance(k, tuple) for k in valores):
                serializado[campo] = [
                    {**dict(zip(columnas, clave)), "cantidad": cantidad}
                    for clave, cantidad in valores.items()
                ]

        cobertura = resultado.get("cobertura_zona_tipo_pct")
        if isinstance(cobertura, dict) and any(isinstance(k, tuple) for k in cobertura):
            serializado["cobertura_zona_tipo_pct"] = [
                {"zona": clave[0], "tipo_ayuda": clave[1], "porcentaje": porcentaje}
                for clave, porcentaje in cobertura.items()
            ]

        rutas = resultado.get("rutas_usadas")
        if isinstance(rutas, dict) and any(isinstance(k, tuple) for k in rutas):
            serializado["rutas_usadas"] = [
                {"origen": clave[0], "destino": clave[1], **detalle}
                for clave, detalle in rutas.items()
            ]

        return serializado

    @staticmethod
    def _validar_seccion(seccion: str) -> None:
        if seccion not in SECCIONES:
            raise ValueError(f"Sección desconocida. Usa: {', '.join(sorted(SECCIONES))}.")
