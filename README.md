# Proyecto-ADA-2

| Integrante                 | Código de estudiante |
| -------------------------- | -------------------: |
| Juan David Quintero Garcia |              2559710 |
| Juan Jose Ospina           |              2559711 |
| Miguel Angel Arboleda      |              2160253 |

## Estado del proyecto

El repositorio separa el optimizador (carpeta `Modelo`) del backend REST
(carpeta `API`). La interfaz consume la API sin conocer los detalles internos
del solver o del almacenamiento.

## Parte 2: backend REST y gestión de datos

La parte 2 se organiza en capas. El frontend se comunicará con el backend por
HTTP/JSON y no accederá directamente a archivos ni importará el optimizador.

```text
Frontend (futuro)
   │ HTTP / JSON
   ▼
API/controllers       Rutas REST y códigos HTTP
   ▼
API/dto               Contratos y validación de forma de entrada/salida
   ▼
API/services          Reglas de negocio, validación y coordinación
   ├── domain          Reglas y estructura del escenario
   ├── Modelo          Solver existente (solo al optimizar)
   ▼
API/repositories      Lectura y escritura de archivos JSON
```

- `API/controllers/`: endpoints y traducción de errores a respuestas HTTP.
- `API/dto/`: contratos Pydantic de las peticiones y respuestas de escenario.
- `API/services/`: operaciones de escenarios y conexión con la validación y el
  optimizador.
- `API/services/escenario_service_interface.py`: contrato que consumen los
  controllers.
- `API/services/escenario_service.py`: implementación concreta
  `EscenarioServiceImpl`.
- `API/dependencies.py`: selecciona e inyecta la implementación en FastAPI.
- `API/repositories/`: persistencia local, un archivo JSON por escenario.
- `API/domain/`: estructura y reglas de validación del dominio.
- `API/services/importacion_service.py`: carga y validación de escenarios JSON/CSV.
- `API/repositories/archivo_json_repository.py`: operaciones de lectura y
  escritura de archivos JSON para importación/exportación.
- `API/resources/templates/`: archivos de ejemplo para importar.
- `API/main.py`: aplicación FastAPI y documentación OpenAPI automática.

Esta separación evita que los controladores contengan reglas o acceso a disco.
Los DTOs forman el contrato público y validan la forma y los tipos del JSON;
`domain` conserva las reglas propias del problema y las relaciones entre
centros, ayudas, zonas y rutas. El servicio coordina las operaciones y el
repositorio es el único que conoce dónde se guardan los archivos.

El controller depende de `EscenarioServiceInterface`; `API/dependencies.py`
inyecta `EscenarioServiceImpl` como implementación actual. Si luego se crea
otra implementación (por ejemplo, una de pruebas o una que use base de datos),
se puede cambiar desde ese proveedor sin reescribir las rutas.

No usamos una carpeta genérica `utils`: el importador es una operación de
aplicación en `services`, mientras que la plantilla es un recurso estático en
`resources/templates`. Así cada archivo queda en la capa que explica su función.

El contenido `datos` del escenario usa el mismo formato que recibe
`Modelo/optimizador.py`: las claves son `tipos_ayuda`, `prioridades`, `centros`,
`zonas` y `rutas`. Los registros aceptan reservas, capacidades, costos,
incompatibilidades y opciones como en `Modelo/escenario_conceptual.json`. La API
permite guardar borradores incompletos mientras el usuario diligencia los
formularios; el endpoint de validación informa si ya puede optimizarse.

### Ejecutar y explorar la API

Desde la carpeta del proyecto, instala dependencias e inicia el servidor:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn API.main:app --reload
```

Luego abre `http://127.0.0.1:8000/docs`. Swagger permite probar las rutas y ver
los formatos de petición y respuesta. El servidor guarda los escenarios en
`API/data/escenarios/`.

### Rutas REST principales

| Método | Ruta | Uso |
| --- | --- | --- |
| `GET` | `/api/escenarios` | Lista los escenarios |
| `POST` | `/api/escenarios` | Crea un borrador con `{"id":"emergencia-1","nombre":"Emergencia"}` |
| `GET` | `/api/escenarios/{id}` | Consulta el escenario |
| `PUT` | `/api/escenarios/{id}` | Reemplaza todo el contenido `datos` |
| `DELETE` | `/api/escenarios/{id}` | Elimina el archivo JSON del escenario |
| `GET` | `/api/escenarios/{id}/secciones/{seccion}` | Lista ayudas, centros, zonas o rutas |
| `POST` | `/api/escenarios/{id}/secciones/{seccion}` | Registra un centro, zona, tipo o ruta |
| `PUT` | `/api/escenarios/{id}/secciones/{seccion}/{ident}` | Actualiza un registro |
| `DELETE` | `/api/escenarios/{id}/secciones/{seccion}/{ident}` | Elimina un registro |
| `PUT` | `/api/escenarios/{id}/prioridades` | Define pesos, por ejemplo `{"Critica":4,"Alta":3}` |
| `POST` | `/api/escenarios/{id}/validar` | Devuelve `valido` y la lista de errores |
| `POST` | `/api/escenarios/{id}/optimizar` | Valida, ejecuta PuLP/CBC y entrega el resultado |

Las secciones administrables son `tipos_ayuda`, `centros`, `zonas` y `rutas`.
Para una ruta, la identidad usada en actualizar/eliminar es `origen->destino`
(por ejemplo, `C1-%3EZ1` codificado en la URL).

### Ejemplo de consumo desde el frontend

```javascript
const base = "http://127.0.0.1:8000/api";
const respuesta = await fetch(`${base}/escenarios`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ id: "emergencia-1", nombre: "Emergencia" })
});
const escenario = await respuesta.json();

// Luego de llenar formularios, la interfaz pide validar y optimizar:
const validacion = await fetch(`${base}/escenarios/emergencia-1/validar`, { method: "POST" });
const solucion = await fetch(`${base}/escenarios/emergencia-1/optimizar`, { method: "POST" });
```

### Uso desde Python

```python
from API.domain import GestorEscenarios
from API.repositories import AlmacenamientoJSON
from API.services import cargar_escenario

datos = cargar_escenario("Modelo/escenario_conceptual.json")
gestor = GestorEscenarios(datos)
gestor.agregar("centros", {
    "id": "C4", "activo": True, "cap_despacho": 80,
    "inventario": {"Agua": 40}, "reserva": {}
})
gestor.agregar("rutas", {
    "origen": "C4", "destino": "Z1", "disponible": True,
    "costo": 3, "capacidad": 40
})
escenario = gestor.obtener_escenario()  # valida antes de entregar
AlmacenamientoJSON().guardar(escenario, "datos/escenario.json")

# La interfaz pasa este mismo diccionario a la parte 1:
# from Modelo.optimizador import optimizar
# resultado = optimizar(escenario)
```

Las funciones Python `GestorEscenarios.agregar`, `actualizar`, `eliminar` y
`listar` siguen disponibles como lógica de dominio. `AlmacenamientoJSON` sirve
para importar/exportar archivos locales desde herramientas o scripts; la API
usa el repositorio por escenario para persistir borradores mientras se llenan.

### Formato CSV

Para mantener las estructuras internas (inventario y demanda) completas, cada
fila CSV lleva un objeto JSON en `datos`. `API/resources/templates/plantilla_escenario.csv`
muestra el formato: `seccion,id,datos`. Las secciones listadas admiten varias filas;
`prioridades` y `opciones` se suministran una vez cada una. La importación no
ejecuta el optimizador: solo transforma y valida los datos.
