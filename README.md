# Bazaar — Microservice Template

Template base para microservicios Python / FastAPI del ecosistema **Bazaar**.

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic, SQLAlchemy |
| Base de datos | PostgreSQL (configurable por env vars) |
| Contenedor | Docker (multi-stage, non-root) |
| Orquestación | Kubernetes |
| CI/CD | GitHub Actions → GHCR |

## Estructura del proyecto

```
├── src/
│   ├── api/            # Routers de FastAPI
│   │   └── health.py   # /livez y /readyz
│   ├── core/           # Configuración, DB, logging
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   └── logging.py
│   ├── models/         # Entidades SQLAlchemy (vacío — extender aquí)
│   ├── schemas/        # Modelos Pydantic (vacío — extender aquí)
│   ├── services/       # Lógica de negocio (vacío — extender aquí)
│   └── main.py         # Punto de entrada
├── tests/
│   ├── conftest.py
│   └── test_health.py
├── scripts/
│   ├── run_tests.sh    # Wrapper para correr tests (Linux/macOS)
│   └── run_tests.ps1   # Wrapper para correr tests (Windows)
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── secret.yaml     # ⚠️ Template — NO commitear valores reales
├── .github/workflows/
│   └── deploy.yml
├── Dockerfile              # Imagen de producción
├── Dockerfile.test         # Imagen para correr tests
├── docker-compose.test.yml # Levanta PostgreSQL + test runner
├── requirements.txt
└── .env.example
```

## Setup local

```bash
# 1. Clonar y entrar al directorio
git clone <REPO_URL> && cd template-microservice

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con las credenciales de tu base de datos local

# 5. Levantar la aplicación
uvicorn src.main:app --reload
```

## Endpoints disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/livez` | Liveness probe — siempre 200 |
| GET | `/readyz` | Readiness probe — verifica conexión a DB |
| GET | `/docs` | Swagger UI (auto-generado) |
| GET | `/redoc` | ReDoc (auto-generado) |

## Tests

Los tests corren contra una **base de datos PostgreSQL real** usando Docker Compose. No se usa mocking.

El archivo `docker-compose.test.yml` levanta:
1. Un contenedor **PostgreSQL 16** como base de datos.
2. Un contenedor **test-runner** que ejecuta `pytest` contra esa base de datos.

### Correr los tests

```bash
# Linux / macOS
./scripts/run_tests.sh

# Windows (PowerShell)
.\scripts\run_tests.ps1

# O directamente con docker compose
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

> Los contenedores se limpian automáticamente al finalizar.

## Docker

```bash
docker build -t template-service .
docker run -p 8000:8000 --env-file .env template-service
```

## Kubernetes

```bash
# 1. Crear el secret (editar k8s/secret.yaml primero con valores reales)
kubectl apply -f k8s/secret.yaml

# 2. Desplegar
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Extender el template

Para agregar una nueva entidad al microservicio:

1. Crear el modelo SQLAlchemy en `src/models/`.
2. Crear los schemas Pydantic en `src/schemas/`.
3. Implementar la lógica de negocio en `src/services/`.
4. Crear el router en `src/api/` e incluirlo en `src/main.py`.
5. Agregar tests en `tests/`.
