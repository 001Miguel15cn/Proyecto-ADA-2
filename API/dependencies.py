"""Composición de dependencias para la aplicación FastAPI."""

from API.services import EscenarioServiceImpl, EscenarioServiceInterface


def obtener_servicio_escenario() -> EscenarioServiceInterface:
    """Selecciona la implementación concreta detrás del contrato del servicio."""
    return EscenarioServiceImpl()
