"""Gestión de escenarios del proyecto ADA II.

La capa de gestión entrega diccionarios compatibles con ``Modelo/optimizador.py``.
No depende de la interfaz gráfica ni del solver.
"""

from .escenarios import (
    GestorEscenarios,
    validar_escenario,
    crear_escenario_vacio,
)

__all__ = [
    "GestorEscenarios",
    "validar_escenario",
    "crear_escenario_vacio",
]
