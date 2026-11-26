"""Punto de entrada de la API REST. Documentación Swagger en /docs."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from API.controllers.escenario_controller import router as escenarios_router


app = FastAPI(
    title="API de Distribución de Ayudas Humanitarias",
    description="Gestión, validación y optimización de escenarios de emergencia.",
    version="1.0.0",
)

# En desarrollo se permite conectar un frontend local. En producción se debe
# restringir allow_origins a la URL del frontend desplegado.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(escenarios_router)


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"estado": "ok", "servicio": "API ADA II"}
