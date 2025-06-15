# Lunance IA - Personal Finance Management API

Lunance IA es una API REST completa para la gestión de finanzas personales construida con FastAPI y Python. Proporciona un backend robusto para el seguimiento de ingresos, gastos, presupuestos, suscripciones, metas de ahorro y recordatorios financieros.

## 🚀 Características Principales

### 💰 Gestión Financiera Completa
- **Seguimiento de Transacciones**: Registro detallado de ingresos y gastos
- **Gestión de Cuentas**: Soporte para múltiples tipos de cuenta (efectivo, débito, crédito, ahorros, inversión)
- **Presupuestos Inteligentes**: Configuración de límites de gasto por categoría con alertas automáticas
- **Metas de Ahorro**: Establecimiento y seguimiento de objetivos financieros
- **Suscripciones**: Control de pagos recurrentes con generación automática de cargos

### 🔐 Seguridad y Autenticación
- **Autenticación JWT**: Sistema seguro basen tokens
- **Encriptación de Contraseñas**: Usando Passlib para máxima seguridad
- **Autenticación OAuth2**: Estándar de la industria para APIs

### 🎯 Organización y Personalización
- **Sistema de Categorías**: Clasificación flexible de transacciones
- **Etiquetas Personalizadas**: Organización custom con colores
- **Recordatorios**: Sistema de notificaciones para pagos y revisiones
- **Soporte Multi-moneda**: Configuración por defecto en MXN

## 🛠️ Stack Tecnológico

- **Framework**: FastAPI (Python)
- **Base de Datos**: MySQL con SQLAlchemy ORM
- **Migraciones**: Alembic
- **Autenticación**: JWT + OAuth2
- **Validación**: Pydantic
- **Seguridad**: Passlib, python-jose

## 📁 Estructura del Proyecto

```
src/
├── main.py                 # Aplicación principal FastAPI
├── config.py              # Configuración de la aplicación
├── models/                # Modelos de base de datos
│   ├── user.py           # Usuario y autenticación
│   ├── account.py        # Cuentas financieras
│   ├── transaction.py    # Transacciones
│   ├── budget.py         # Presupuestos
│   ├── subscription.py   # Suscripciones
│   └── ...
├── api/v1/               # Endpoints API v1
│   ├── endpoints/        # Rutas específicas
│   │   ├── auth.py      # Autenticación
│   │   ├── transactions.py
│   │   ├── users.py
│   │   └── ...
│   └── api.py           # Router principal
├── core/                # Funcionalidades core
│   ├── security.py      # Manejo de JWT y passwords
│   └── database.py      # Configuración de BD
└── schemas/             # Schemas Pydantic
    └── ...
```

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.8+
- MySQL
- pip o uv (recomendado)

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd Lunance
```

### 2. Instalar dependencias
```bash
# Con uv (recomendado)
uv sync

# O con pip
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crear un archivo `.env` en la raíz del proyecto:
```env
DATABASE_URL=mysql+pymysql://usuario:password@localhost:3306/lunance
SECRET_KEY=tu_clave_secreta_muy_segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. Ejecutar migraciones
```bash
alembic upgrade head
```

### 5. Iniciar el servidor
```bash
# Desarrollo
uvicorn src.main:app --reload

# Producción
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## 📖 Uso de la API

### Autenticación
```bash
# Obtener token de acceso
curl -X POST "http://localhost:8000/api/v1/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=tu_email@ejemplo.com&password=tu_password"
```

### Endpoints Principales

- **Autenticación**: `/api/v1/login`
- **Usuarios**: `/api/v1/users/`
- **Transacciones**: `/api/v1/transactions/`
- **Presupuestos**: `/api/v1/budgets/`
- **Cuentas**: `/api/v1/accounts/`
- **Suscripciones**: `/api/v1/subscriptions/`

### Documentación Interactiva
Una vez iniciado el servidor, accede a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏗️ Arquitectura

### Modelos de Datos Principales

1. **Usuario**: Gestión de usuarios con autenticación JWT
2. **Cuenta**: Diferentes tipos de cuentas financieras
3. **Transacción**: Registro de ingresos y gastos
4. **Categoría**: Clasificación de transacciones
5. **Presupuesto**: Límites de gasto por categoría y período
6. **Suscripción**: Pagos recurrentes automatizados
7. **Meta de Ahorro**: Objetivos financieros con seguimiento
8. **Etiqueta**: Sistema de etiquetado personalizable
9. **Recordatorio**: Sistema de notificaciones

### Características Técnicas

- **Arquitectura RESTful**: API limpia y estándar
- **Versionado de API**: Soporte para múltiples versiones
- **Validación de Datos**: Schemas Pydantic robustos
- **Manejo de Errores**: Respuestas de error consistentes
- **CORS**: Configurado para integraciones frontend
- **Logging**: Sistema de logs para monitoreo

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🐛 Reporte de Problemas

Si encuentras algún problema o tienes sugerencias, por favor crea un issue en el repositorio.

---

**Lunance IA** - Tu asistente inteligente para el manejo de finanzas personales 💰✨