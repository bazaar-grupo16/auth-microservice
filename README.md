# Bazaar — Authentication Service

Microservicio de autenticación y autorización basado en Python / FastAPI del ecosistema **Bazaar**. Proporciona generación, validación y rotación de tokens JWT para proteger otros microservicios.

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic, SQLAlchemy |
| Base de datos | PostgreSQL (configurable por env vars) |
| Contenedor | Docker (multi-stage, non-root) |
| Orquestación | Kubernetes (DigitalOcean) |
| CI/CD | GitHub Actions → GHCR → DOKS |

## Estructura del proyecto

```
├── src/
│   ├── api/
│   │   ├── controllers/    # Lógica de manejo de requests
│   │   ├── routers/        # Definición de rutas FastAPI
│   │   └── health.py       # /livez y /readyz
│   ├── core/           # Configuración, DB, logging
│   │   ├── config.py
│   │   ├── database.py  # Engine, sesión, base, y retry de conexión
│   │   ├── dependencies.py
│   │   ├── logging.py
│   │   └── utils.py    # Utilidades compartidas
│   ├── exceptions/     # Tipos de excepción de dominio
│   ├── models/         # Entidades SQLAlchemy
│   ├── repositories/   # Acceso a datos
│   ├── schemas/        # Modelos Pydantic
│   ├── services/       # Lógica de negocio
│   └── main.py         # Punto de entrada
├── tests/
│   ├── conftest.py
│   └── test_health.py
├── scripts/
│   ├── run_tests.sh    # Wrapper para correr tests (Linux/macOS)
│   └── run_tests.ps1   # Wrapper para correr tests (Windows)
├── k8s/
│   ├── app-deployment.yaml   # Deployment del microservicio
│   ├── app-service.yaml      # Service (ClusterIP) del microservicio
│   ├── db-deployment.yaml    # Deployment de PostgreSQL
│   ├── db-service.yaml       # Service (ClusterIP) de PostgreSQL
│   ├── db-pvc.yaml           # PersistentVolumeClaim para la BD
│   └── secret.yaml           # ⚠️ Template — NO commitear valores reales
├── .github/workflows/
│   ├── ci-dev.yml      # Pipeline CI para la rama dev (lint, SAST, test)
│   └── deploy.yml
├── Dockerfile              # Imagen de producción
├── Dockerfile.test         # Imagen para correr tests
├── docker-compose.test.yml # Levanta PostgreSQL + test runner
├── requirements.txt
└── .env.example
```

## Descripción del servicio

Este Authentication Service es responsable de:
- **Generar tokens JWT** para autenticar usuarios
- **Validar tokens** desde otros microservicios
- **Rotar refresh tokens** de forma segura
- Actuar como **Authorization Server** centralizado para el ecosistema Bazaar

## Setup local

```bash
# 1. Clonar y entrar al directorio
git clone <REPO_URL> && cd auth-microservice

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

## Conectarse al cluster de DigitalOcean

Requisitos:
- Tener instalado [doctl](https://docs.digitalocean.com/reference/doctl/)
- Tener instalado [kubectl](https://kubernetes.io/docs/tasks/tools/)

```bash
# 1. Iniciar sesión en doctl
doctl auth init --context <NAME>
doctl auth switch --context <NAME>

# 2. Obtener credenciales del cluster
doctl kubernetes cluster kubeconfig save <CLUSTER_ID>
```

## Endpoints disponibles

### Health Checks
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/livez` | Liveness probe — verifica que el proceso está vivo (siempre 200) |
| GET | `/readyz` | Readiness probe — verifica conexión a la base de datos |

### Autenticación (Auth Service)
| Método | Ruta | Descripción | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/token` | Genera un par de tokens JWT (acceso + refresh) | `{"user_id": "uuid"}` | `{"access_token": "...", "refresh_token": "...", "expires_in": 3600, "refresh_expires_in": 604800}` |
| POST | `/token/refresh` | Rota el refresh token e emite nuevos tokens | `{"refresh_token": "..."}` | `{"access_token": "...", "refresh_token": "...", "expires_in": 3600, "refresh_expires_in": 604800}` |
| GET | `/validate` | Valida un access token desde el header Authorization | Header: `Authorization: Bearer <token>` | `{"status": "valid", "user_id": "uuid"}` + header `X-User-ID` |

**Documentación interactiva:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

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
docker build -t auth-service .
docker run -p 8000:8000 --env-file .env auth-service
```

## Variables de entorno

Las variables de entorno se deben configurar en el archivo `.env` (copia de `.env.example`).

### Variables requeridas (Aplicación)

| Variable | Tipo | Descripción | Ejemplo |
|----------|------|-------------|---------|
| `APP_NAME` | string | Nombre de la aplicación | `auth-service` |
| `LOG_LEVEL` | string | Nivel de logging (debug, info, warning, error) | `info` |
| `DB_HOST` | string | Host de la base de datos PostgreSQL | `localhost` |
| `DB_PORT` | int | Puerto de la base de datos | `5432` |
| `DB_USER` | string | Usuario de la base de datos | `your_db_user` |
| `DB_PASSWORD` | string | Contraseña de la base de datos | `your_db_password` |
| `DB_NAME` | string | Nombre de la base de datos | `bazaar_auth` |
| `SECRET_KEY` | string | Clave secreta para firmar JWTs | `your-secret-key-here` |
| `JWT_ALGORITHM` | string | Algoritmo de firma JWT | `HS256` |
| `JWT_EXPIRE_MINUTES` | int | Tiempo de expiración del access token (minutos) | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | Tiempo de expiración del refresh token (días) | `7` |

## Kubernetes

Los manifiestos en `k8s/` despliegan el microservicio junto con su propia base de datos PostgreSQL dentro del cluster.

### Variables de entorno para GitHub Secrets

Estas variables se configuran en GitHub y se usan en los workflows de CI/CD:

| Secret | Descripción |
|--------|-------------|
| `DIGITALOCEAN_ACCESS_TOKEN` | Personal Access Token de DigitalOcean |
| `DB_USER` | Usuario de la base de datos |
| `DB_PASSWORD` | Contraseña de la base de datos |
| `DB_NAME` | Nombre de la base de datos |
| `SECRET_KEY` | Clave secreta para firmar JWTs |
| `JWT_ALGORITHM` | Algoritmo de firma JWT |
| `JWT_EXPIRE_MINUTES` | Tiempo de expiración del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Tiempo de expiración del refresh token |

> **Nota:** `DB_HOST` y `DB_PORT` están fijos en `k8s/secret.yaml` (`bazaar-db:5432`) ya que la BD corre dentro del cluster.
> Si se utilizase una base de datos externa, se deberían agregar las variables de entorno correspondientes.

### Deploy manual

```bash
# Crear el namespace (solo la primera vez)
kubectl create namespace bazaar-dev

# Aplicar todos los manifiestos en orden
kubectl apply -f k8s/db-pvc.yaml       -n bazaar-dev
kubectl apply -f k8s/db-deployment.yaml -n bazaar-dev
kubectl apply -f k8s/db-service.yaml    -n bazaar-dev
kubectl apply -f k8s/secret.yaml        -n bazaar-dev
kubectl apply -f k8s/app-deployment.yaml -n bazaar-dev
kubectl apply -f k8s/app-service.yaml   -n bazaar-dev
```

### CI/CD automático

Hay dos pipelines de GitHub Actions:

**`ci-dev.yml`** — corre en cada push/PR a `dev`:

| Job | Descripción |
|-----|-------------|
| `lint` | Ruff sobre `src/` y `tests/` |
| `sast` | Bandit (análisis estático de seguridad) sobre `src/` |
| `test` | Tests contra PostgreSQL real vía Docker Compose |

**`deploy.yml`** — corre en cada push a `main`:

| Job | Se ejecuta cuando cambia... |
|-----|----------------------------|
| `lint` | `src/`, `tests/`, archivos de build |
| `test` | `src/`, `tests/`, archivos de build |
| `build` | `src/`, `tests/`, archivos de build (solo push a main) |
| `deploy` | `src/` **o** `k8s/` (solo push a main) |

## Conexión a la base de datos

Al iniciar, la aplicación espera a que la base de datos esté disponible usando **backoff exponencial** (1s → 2s → 4s → … hasta 30s por intento, máximo 5 minutos en total) antes de ejecutar las migraciones y aceptar tráfico. Esto evita crasheos durante el arranque del pod cuando la BD aún está inicializándose.

## Extender el template

Para agregar una nueva entidad al microservicio:

1. Crear el modelo SQLAlchemy en `src/models/`.
2. Crear los schemas Pydantic en `src/schemas/`.
3. Implementar el repositorio de acceso a datos en `src/repositories/`.
4. Definir las excepciones de dominio en `src/exceptions/`.
5. Implementar la lógica de negocio en `src/services/`.
6. Crear el controller en `src/api/controllers/` y el router en `src/api/routers/`; incluir el router en `src/main.py`.
7. Agregar tests en `tests/`.
