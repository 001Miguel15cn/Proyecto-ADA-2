"""Estructura, validación y operaciones sobre escenarios de emergencia."""

from __future__ import annotations

import copy
import math
from typing import Any


SECCIONES_LISTA = ("tipos_ayuda", "centros", "zonas", "rutas")


def crear_escenario_vacio() -> dict[str, Any]:
    """Crea un escenario inicial con todas las secciones requeridas."""
    return {
        "tipos_ayuda": [],
        "prioridades": {},
        "centros": [],
        "zonas": [],
        "rutas": [],
        "incompatibilidades": [],
        "opciones": {"ponderar_por_poblacion": False},
    }


def validar_escenario(escenario: Any) -> list[str]:
    """Valida estructura y relaciones y devuelve errores legibles en español."""
    errores: list[str] = []
    if not isinstance(escenario, dict):
        return ["El escenario debe ser un objeto JSON (un diccionario)."]

    for clave in (*SECCIONES_LISTA, "prioridades"):
        if clave not in escenario:
            errores.append(f"Falta la sección obligatoria '{clave}'.")
    if errores:
        return errores

    for clave in SECCIONES_LISTA:
        if not isinstance(escenario[clave], list):
            errores.append(f"La sección '{clave}' debe ser una lista.")
    if not isinstance(escenario["prioridades"], dict):
        errores.append("La sección 'prioridades' debe ser un objeto con pesos numéricos.")
    if errores:
        return errores

    def numero(valor: Any, nombre: str, minimo: float = 0) -> bool:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            errores.append(f"{nombre}: debe ser un número.")
            return False
        if not math.isfinite(valor):
            errores.append(f"{nombre}: debe ser un número finito.")
            return False
        if valor < minimo:
            errores.append(f"{nombre}: no puede ser menor que {minimo}.")
            return False
        return True

    def registros(clave: str) -> list[dict]:
        resultado = []
        for pos, item in enumerate(escenario[clave], start=1):
            if not isinstance(item, dict):
                errores.append(f"'{clave}', elemento {pos}: debe ser un objeto.")
            else:
                resultado.append(item)
        return resultado

    tipos = registros("tipos_ayuda")
    centros = registros("centros")
    zonas = registros("zonas")
    rutas = registros("rutas")

    def indexar(items: list[dict], etiqueta: str) -> dict[str, dict]:
        indice: dict[str, dict] = {}
        for pos, item in enumerate(items, start=1):
            ident = item.get("id")
            if not isinstance(ident, str) or not ident.strip():
                errores.append(f"{etiqueta}, elemento {pos}: el campo 'id' es obligatorio.")
            elif ident in indice:
                errores.append(f"{etiqueta}: el identificador '{ident}' está repetido.")
            else:
                indice[ident] = item
        return indice

    tipos_por_id = indexar(tipos, "Tipos de ayuda")
    centros_por_id = indexar(centros, "Centros")
    zonas_por_id = indexar(zonas, "Zonas")
    if not tipos:
        errores.append("Debe registrar al menos un tipo de ayuda.")
    if not centros:
        errores.append("Debe registrar al menos un centro de almacenamiento.")
    if not zonas:
        errores.append("Debe registrar al menos una zona afectada.")
    if centros and not any(c.get("activo", True) is True for c in centros):
        errores.append("Debe existir al menos un centro activo.")

    for nombre, peso in escenario["prioridades"].items():
        numero(peso, f"Peso de prioridad '{nombre}'", 0)
        if isinstance(peso, (int, float)) and not isinstance(peso, bool) and peso <= 0:
            errores.append(f"Peso de prioridad '{nombre}': debe ser mayor que cero.")
    if not escenario["prioridades"]:
        errores.append("Debe definir al menos una prioridad.")

    for tipo in tipos:
        ident = tipo.get("id", "?")
        volumen = tipo.get("volumen", 1)
        if numero(volumen, f"Volumen de '{ident}'") and volumen == 0:
            errores.append(f"Volumen de '{ident}': debe ser mayor que cero.")
        numero(tipo.get("importancia", 1), f"Importancia de '{ident}'")
        if "divisible" in tipo and not isinstance(tipo["divisible"], bool):
            errores.append(f"Tipo '{ident}': 'divisible' debe ser verdadero o falso.")

    def mapa_cantidades(mapa: Any, nombre: str, llaves_validas: set[str]) -> None:
        if not isinstance(mapa, dict):
            errores.append(f"{nombre}: debe ser un objeto por tipo de ayuda.")
            return
        for ident, cantidad in mapa.items():
            if ident not in llaves_validas:
                errores.append(f"{nombre}: el tipo de ayuda '{ident}' no está registrado.")
            numero(cantidad, f"{nombre}, '{ident}'")

    for centro in centros:
        ident = centro.get("id", "?")
        if not isinstance(centro.get("activo", True), bool):
            errores.append(f"Centro '{ident}': 'activo' debe ser verdadero o falso.")
        numero(centro.get("cap_despacho", 0), f"Capacidad de despacho de '{ident}'")
        inventario = centro.get("inventario", {})
        reserva = centro.get("reserva", {})
        mapa_cantidades(inventario, f"Inventario del centro '{ident}'", set(tipos_por_id))
        mapa_cantidades(reserva, f"Reserva del centro '{ident}'", set(tipos_por_id))
        if isinstance(inventario, dict) and isinstance(reserva, dict):
            for tipo, cantidad in reserva.items():
                if isinstance(cantidad, (int, float)) and not isinstance(cantidad, bool):
                    if cantidad > inventario.get(tipo, 0):
                        errores.append(f"Centro '{ident}': la reserva de '{tipo}' supera el inventario.")

    for zona in zonas:
        ident = zona.get("id", "?")
        if zona.get("prioridad") not in escenario["prioridades"]:
            errores.append(f"Zona '{ident}': la prioridad no está definida.")
        numero(zona.get("poblacion", 0), f"Población de '{ident}'")
        mapa_cantidades(zona.get("demanda", {}), f"Demanda de la zona '{ident}'", set(tipos_por_id))
        cobertura = zona.get("cobertura_minima", 0)
        if numero(cobertura, f"Cobertura mínima de '{ident}") and cobertura > 1:
            errores.append(f"Zona '{ident}': la cobertura mínima debe estar entre 0 y 1.")

    rutas_vistas: set[tuple[str, str]] = set()
    for pos, ruta in enumerate(rutas, start=1):
        origen, destino = ruta.get("origen"), ruta.get("destino")
        etiqueta = f"Ruta {origen}->{destino} (elemento {pos})"
        if origen not in centros_por_id:
            errores.append(f"{etiqueta}: el centro de origen no existe.")
        if destino not in zonas_por_id:
            errores.append(f"{etiqueta}: la zona de destino no existe.")
        par = (origen, destino)
        if par in rutas_vistas:
            errores.append(f"Ruta {origen}->{destino}: está definida más de una vez.")
        rutas_vistas.add(par)
        if not isinstance(ruta.get("disponible", True), bool):
            errores.append(f"{etiqueta}: 'disponible' debe ser verdadero o falso.")
        numero(ruta.get("costo", 0), f"Costo de {origen}->{destino}")
        numero(ruta.get("capacidad", 0), f"Capacidad de {origen}->{destino}")

    incompatibilidades = escenario.get("incompatibilidades", [])
    if not isinstance(incompatibilidades, list):
        errores.append("La sección 'incompatibilidades' debe ser una lista.")
        incompatibilidades = []
    for incompatibilidad in incompatibilidades:
        if not isinstance(incompatibilidad, dict):
            errores.append("Cada incompatibilidad debe ser un objeto.")
            continue
        if incompatibilidad.get("centro") not in centros_por_id or incompatibilidad.get("ayuda") not in tipos_por_id:
            errores.append(f"Incompatibilidad inválida: {incompatibilidad}.")
    opciones = escenario.get("opciones", {})
    if not isinstance(opciones, dict):
        errores.append("La sección 'opciones' debe ser un objeto.")
    elif "ponderar_por_poblacion" in opciones and not isinstance(opciones["ponderar_por_poblacion"], bool):
        errores.append("La opción 'ponderar_por_poblacion' debe ser verdadera o falsa.")
    return errores


class GestorEscenarios:
    """Operaciones CRUD sencillas sobre las secciones de un escenario."""

    def __init__(self, escenario: dict[str, Any] | None = None, validar_inicial: bool = True):
        self.escenario = copy.deepcopy(escenario) if escenario is not None else crear_escenario_vacio()
        errores = validar_escenario(self.escenario) if validar_inicial else []
        if errores:
            raise ValueError("Escenario inválido:\n- " + "\n- ".join(errores))

    def agregar(self, seccion: str, registro: dict[str, Any]) -> None:
        if seccion not in SECCIONES_LISTA:
            raise ValueError(f"Sección no administrable: {seccion}.")
        self._guardar_registro(seccion, registro, reemplazar=False)

    def actualizar(self, seccion: str, ident: str, cambios: dict[str, Any]) -> None:
        if seccion not in SECCIONES_LISTA:
            raise ValueError(f"Sección no administrable: {seccion}.")
        for item in self.escenario[seccion]:
            if self._identidad(seccion, item) == ident:
                item.update(copy.deepcopy(cambios))
                if seccion != "rutas":
                    item["id"] = ident
                return
        raise KeyError(f"No existe '{ident}' en la sección '{seccion}'.")

    def eliminar(self, seccion: str, ident: str) -> None:
        if seccion not in SECCIONES_LISTA:
            raise ValueError(f"Sección no administrable: {seccion}.")
        anterior = len(self.escenario[seccion])
        self.escenario[seccion] = [x for x in self.escenario[seccion] if self._identidad(seccion, x) != ident]
        if len(self.escenario[seccion]) == anterior:
            raise KeyError(f"No existe '{ident}' en la sección '{seccion}'.")

    def listar(self, seccion: str) -> list[dict[str, Any]]:
        if seccion not in SECCIONES_LISTA:
            raise ValueError(f"Sección no administrable: {seccion}.")
        return copy.deepcopy(self.escenario[seccion])

    def definir_prioridades(self, prioridades: dict[str, float]) -> None:
        self.escenario["prioridades"] = copy.deepcopy(prioridades)

    def _guardar_registro(self, seccion: str, registro: dict[str, Any], reemplazar: bool) -> None:
        if not isinstance(registro, dict) or not self._identidad(seccion, registro):
            requerido = "'origen' y 'destino'" if seccion == "rutas" else "'id'"
            raise ValueError(f"El registro debe ser un objeto con {requerido}.")
        lista = self.escenario[seccion]
        ident = self._identidad(seccion, registro)
        encontrado = next((x for x in lista if self._identidad(seccion, x) == ident), None)
        if encontrado and not reemplazar:
            raise ValueError(f"Ya existe '{ident}' en '{seccion}'.")
        if encontrado:
            lista[lista.index(encontrado)] = copy.deepcopy(registro)
        else:
            lista.append(copy.deepcopy(registro))

    @staticmethod
    def _identidad(seccion: str, registro: dict[str, Any]) -> str | None:
        if seccion == "rutas":
            origen, destino = registro.get("origen"), registro.get("destino")
            return f"{origen}->{destino}" if origen and destino else None
        return registro.get("id")

    def obtener_escenario(self, validar: bool = True) -> dict[str, Any]:
        if validar:
            errores = validar_escenario(self.escenario)
            if errores:
                raise ValueError("Escenario inválido:\n- " + "\n- ".join(errores))
        return copy.deepcopy(self.escenario)
