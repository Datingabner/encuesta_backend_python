# Backend de Encuestas de Salud Mental

API REST desarrollada en Django para gestionar encuestas de salud mental (ansiedad y depresión) para empleados de una empresa.

## 📋 Tabla de Contenidos

- [Descripción](#descripción)
- [Tecnologías](#tecnologías)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Endpoints de la API](#endpoints-de-la-api)
- [Modelos de Datos](#modelos-de-datos)
- [Seguridad](#seguridad)
- [Despliegue a Producción](#despliegue-a-producción)

---

## 🏗️ Descripción

Este backend proporciona una API REST para:

- **Validación de empleados** mediante número de empleado
- **Gestión de encuestas** de salud mental (GAD-7 para ansiedad, PHQ-9 para depresión)
- **Registro de respuestas** y cálculo automático de puntajes
- **Notificaciones automáticas** a RRHH cuando se completan encuestas
- **Dashboard administrativo** para visualización de resultados

---

## 🛠️ Tecnologías

| Tecnología | Versión | Uso |
|------------|---------|-----|
| Python | 3.10+ | Lenguaje backend |
| Django | 4.2+ | Framework web |
| Django REST Framework | 3.14+ | API REST |
| PostgreSQL | 14+ | Base de datos |
| SimpleJWT | 5.3+ | Autenticación JWT |
| CORS Headers | 4.1+ | Control CORS |

---

## 📦 Requisitos

```bash
# Python 3.10+
python --version

# PostgreSQL 14+ (opcional para desarrollo local)
```

### Dependencias

Ver [`requirements.txt`](requirements.txt):

```
django>=4.2
djangorestframework>=3.14
djangorestframework-simplejwt>=5.3
psycopg2-binary>=2.9
python-dotenv>=1.0
django-cors-headers>=4.1
certifi>=2023.7.22
```

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone <repositorio>
cd encuesta_backend_python
```

### 2. Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
copy .env.example .env
# Editar .env con tus valores
```

### 5. Ejecutar migraciones

```bash
python manage.py migrate
```

### 6. Crear superusuario (opcional)

```bash
python manage.py createsuperuser
```

### 7. Iniciar servidor

```bash
# Desarrollo
python manage.py runserver

# Producción (ver sección de despliegue)
python manage.py runserver 0.0.0.0:8000
```

---

## ⚙️ Configuración

### Variables de Entorno (`.env`)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SECRET_KEY` | Clave secreta de Django (generar nueva) | `django-insecure-xxx...` |
| `DEBUG` | Modo depuración (`True` desarrollo, `False` producción) | `False` |
| `ALLOWED_HOSTS` | Hosts permitidos (separados por coma) | `localhost,127.0.0.1,tudominio.com` |
| `DB_NAME` | Nombre de la base de datos | `encuestas_salud` |
| `DB_USER` | Usuario de PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña de PostgreSQL | `tu_password` |
| `DB_HOST` | Host de la base de datos | `localhost` |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `JWT_SECRET_KEY` | Clave secreta para JWT | `jwt-secret-xxx` |
| `CORS_ALLOWED_ORIGINS` | Origins permitidos CORS | `http://localhost:3000` |
| `EMAIL_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `EMAIL_PORT` | Puerto SMTP | `587` |
| `EMAIL_USER` | Usuario de email | `tuemail@gmail.com` |
| `EMAIL_PASS` | Password de email (app password) | `xxxx xxxx xxxx xxxx` |
| `RRHH_EMAIL` | Email de RRHH para notificaciones | `rrhh@empresa.com` |
| `ADMIN_API_KEY` | API Key para endpoints admin | `admin-key-xxx` |

### Configuración de Gmail

Para usar Gmail como servidor de correo:

1. Habilitar **Verificación en dos pasos** en tu cuenta Google
2. Ir a **Google Account > Security > App passwords**
3. Generar una contraseña de aplicación de 16 caracteres
4. Usar esa contraseña en `EMAIL_PASS`

---

## 📡 Endpoints de la API

### Autenticación

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/validar-empleado` | Valida empleado y genera JWT | No |
| POST | `/api/auth/token/` | Obtiene token JWT | No |
| POST | `/api/auth/token/refresh/` | Refresca token JWT | JWT |

### Encuestas

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/api/encuestas` | Lista encuestas activas | API Key |
| POST | `/api/encuestas` | Crea encuesta | API Key |
| GET | `/api/encuestas/<id>` | Obtiene detalle de encuesta | API Key |
| PUT | `/api/encuestas/<id>` | Actualiza encuesta | API Key |
| DELETE | `/api/encuestas/<id>` | Elimina encuesta | API Key |
| GET | `/api/encuestas/<survey_id>` | Obtiene encuesta para empleado | JWT |
| POST | `/api/encuestas/<survey_id>/submit` | Envía respuestas de encuesta | JWT |

### Progreso del Empleado

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/api/empleado/progress` | Obtiene progreso del empleado | JWT |

### Administración

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET/POST | `/api/admin/validate-key` | Valida API Key admin | API Key |
| GET | `/api/admin/results` | Obtiene resultados de encuestas | API Key |

---

## Uso de la API

### 1. Validar Empleado

```bash
curl -X POST http://localhost:8000/api/auth/validar-empleado \
  -H "Content-Type: application/json" \
  -d '{"numero_empleado": "EMP001"}'
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Empleado validado exitosamente",
  "data": {
    "empleado": {
      "id": 1,
      "numero_empleado": "EMP001",
      "nombre": "Juan Pérez",
      "departamento": 1
    },
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": "24h"
  }
}
```

### 2. Obtener Encuesta

```bash
curl -X GET http://localhost:8000/api/encuestas/1 \
  -H "Authorization: Bearer <TOKEN_JWT>"
```

### 3. Enviar Respuestas

```bash
curl -X POST http://localhost:8000/api/encuestas/1/submit \
  -H "Authorization: Bearer <TOKEN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "responses": [
      {"preguntas": [1], "respuestas": [2]},
      {"preguntas": [2], "respuestas": [1]}
    ]
  }'
```

### 4. Validar API Key (Admin)

```bash
# Via GET
curl "http://localhost:8000/api/admin/validate-key?api_key=tu_api_key"

# Via POST
curl -X POST http://localhost:8000/api/admin/validate-key \
  -H "Content-Type: application/json" \
  -d '{"apiKey": "tu_api_key"}'
```

### 5. Obtener Resultados (Admin)

```bash
curl -X GET "http://localhost:8000/api/admin/results?departamento=1&tipo_encuesta=ansiedad" \
  -H "x-api-key: tu_api_key"
```

---

## 📊 Modelos de Datos

### Empleado
- `numero_empleado`: Código único del empleado
- `nombre_completo`: Nombre del empleado
- `email`: Correo electrónico
- `id_departamento`: ID del departamento
- `activo`: Estado del empleado

### Encuesta
- `tipo`: Tipo de encuesta (ansiedad, depresion, general)
- `descripcion`: Descripción de la encuesta
- `preguntas`: Array JSON con preguntas
- `activa`: Si la encuesta está activa

### ResultadoEncuestas
- `empleado`: Relación con empleado
- `encuesta`: Relación con encuesta
- `estado`: Estado (pendiente, en_progreso, completada, enviada)
- `puntaje_total`: Puntaje calculado
- `interpretacion`: Interpretación del resultado
- `nivel_riesgo`: Nivel de riesgo (bajo, medio, alto, critico)

### RespuestasEncuesta
- `empleado`: Relación con empleado
- `encuesta`: Relación con encuesta
- `preguntas`: Array de preguntas respondidas
- `respuestas`: Array de respuestas
- `sesion_id`: ID de sesión

### Notificacion
- `empleado`: Relación con empleado
- `encuesta`: Relación con encuesta
- `email_destino`: Email de destino
- `asunto`: Asunto del email
- `cuerpo`: Cuerpo del email
- `estado`: Estado (pendiente, enviado, fallido)

---

## 🔒 Seguridad

### Consideraciones importantes para producción:

1. **Cambiar `DEBUG=False`** en archivo `.env`
2. **Generar nuevas claves**:
   - `SECRET_KEY` (usar `django-admin startproject` para generar)
   - `JWT_SECRET_KEY` (generar cadena aleatoria larga)
3. **Configurar `ALLOWED_HOSTS`** con el dominio real
4. **Cambiar credenciales** de base de datos y email
5. **Usar HTTPS** (Django configura automáticamente cuando DEBUG=False)
6. **Eliminar prints()** del código en producción (exponen información)

---

## 🚀 Despliegue a Producción

### Preparación

1. Configurar todas las variables de entorno con valores de producción
2. Establecer `DEBUG=False`
3. Configurar `ALLOWED_HOSTS` con el dominio
4. Usar una base de datos PostgreSQL en producción
5. Configurar un servidor WSGI (Gunicorn, uWSGI)

### Con Gunicorn

```bash
# Instalar gunicorn
pip install gunicorn

# Ejecutar
gunicorn encuesta_backend.wsgi --bind 0.0.0.0:8000
```

### Con Docker (opcional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN python manage.py migrate

EXPOSE 8000

CMD ["gunicorn", "encuesta_backend.wsgi", "--bind", "0.0.0.0:8000"]
```

---

## 📝 Licencia

Copyright © 2024 DevCoder. Todos los derechos reservados.

---

## 🆘 Soporte

Para dudas o problemas:
- Revisar la documentación de Django REST Framework
- Verificar logs en `logs/encuestas.log`
- Contactar al equipo de desarrollo
