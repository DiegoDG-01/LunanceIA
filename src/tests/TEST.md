# 🧪 Tests para Lunance API

Este directorio contiene los tests automatizados para la API de Lunance, convertidos desde los tests HTTP originales a pytest nativo.

## 📁 Estructura

```
src/tests/
├── __init__.py
├── conftest.py               # Configuración y fixtures de pytest
├── e2e/                      # Tests end-to-end (API completa)
│   ├── __init__.py
│   └── test_auth_api.py      # Tests de autenticación
├── integration/              # Tests de integración
│   ├── __init__.py
│   └── test_auth_integration.py
└── unit/                     # Tests unitarios
    ├── __init__.py
    └── test_auth_commands.py
```

## 🚀 Ejecución de Tests

### Instalación de dependencias
```bash
# Instalar dependencias de desarrollo con uv
uv pip install -e ".[dev]"

# O con pip tradicional
pip install -e ".[dev]"
```

### Ejecutar tests con pytest
```bash
# Tests E2E (disponibles y recomendados)
pytest src/tests/e2e/ -v

# Solo tests de autenticación (completos)
pytest src/tests/e2e/test_auth_api.py -v

# Con marcadores específicos
pytest -m "auth" -v
pytest -m "e2e" -v

# Test específico
pytest src/tests/e2e/test_auth_api.py::TestAPIConnectivity -v

# Test de flujo completo
pytest src/tests/e2e/test_auth_api.py::TestCompleteAuthFlow -v

# Con output detallado para debugging
pytest src/tests/e2e/ -v -s
```

### ⚠️ Tests en desarrollo
```bash
# Tests unitarios (en desarrollo)
# pytest src/tests/unit/ -v

# Tests de integración (en desarrollo) 
# pytest src/tests/integration/ -v

# Coverage (no disponible actualmente)
# pytest src/tests/ --cov=src --cov-report=html
```

## 📋 Tests Incluidos

### 🔐 Tests de Autenticación (`test_auth_api.py`)

> **Nota**: Con la migración a Auth0, el flujo de autenticación ha cambiado. Login y registro se manejan directamente con Auth0.

#### 1. **Conectividad API**
- ✅ API está corriendo y accesible
- ✅ Endpoints de auth están disponibles

#### 2. **Perfil de Usuario** (`/auth/me`)
- ✅ Obtener información con token Auth0 válido
- ✅ Error sin token de autorización
- ✅ Error con token inválido

#### 3. **Cierre de Sesión** (`/auth/logout`)
- ✅ Logout exitoso
- ✅ Verificación de token revocado

## 🔧 Configuración

### Fixtures Disponibles
- `http_client`: Cliente HTTP async para hacer requests
- `auth_tokens`: Container para tokens de autenticación
- `test_user_data`: Datos de usuario para tests
- `debug_user_data`: Datos de usuario para debugging
- `flow_user_data`: Datos para test de flujo completo

### Variables de Entorno
```bash
# Base URL de la API (opcional, por defecto localhost:8000)
export TEST_API_BASE_URL="http://localhost:8000/api/v2"

# Timeout para requests (opcional, por defecto 30s)
export TEST_TIMEOUT=30
```

## 📊 Reportes

### Tests E2E Disponibles
```bash
# Ejecutar todos los tests E2E con reporte detallado
pytest src/tests/e2e/ -v

# Ver resumen de tests
pytest src/tests/e2e/ --tb=short

# Solo mostrar tests que fallan
pytest src/tests/e2e/ --tb=no -q
```

### ⚠️ Coverage (en desarrollo)
El sistema de coverage no está completamente configurado. Los tests E2E validan funcionalidad end-to-end pero no miden cobertura de código fuente debido a que hacen llamadas HTTP externas.

**Estado actual:**
- ✅ **E2E Tests**: Tests de autenticación funcionando (requieren Auth0)
- ⚠️ **Coverage**: Limitado (tests HTTP externos)
- 🚧 **Integration Tests**: En desarrollo
- 🚧 **Unit Tests**: En desarrollo

## 🚀 Requisitos Previos

### Para Tests E2E (Recomendado)
1. **API corriendo**: La API debe estar ejecutándose en `http://127.0.0.1:8000`
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```
2. **Base de datos**: Debe estar configurada y migraciones aplicadas
3. **Dependencias**: `uv pip install -e ".[dev]"`

### Para Tests de Integración/Unitarios
1. **Dependencias de desarrollo**: `uv pip install -e ".[dev]"`
2. **Variables de entorno** (para tests de integración)

## 📝 Notas

### ✅ Tests E2E (Disponibles)
- Tests que validan la funcionalidad de autenticación con Auth0
- Tests **independientes** que pueden ejecutarse en cualquier orden
- Validan funcionalidad **end-to-end** de endpoints de auth
- Requieren **token Auth0 válido** para tests autenticados
- No requieren configuración compleja de código fuente

### 🚧 Tests de Integración (En desarrollo)
- Importarían y ejecutarían código real de la aplicación
- Requerirían configuración de entorno completa
- Proporcionarían coverage del código fuente

### 🚧 Tests Unitarios (En desarrollo)
- Probarían funciones y componentes específicos
- No requerirían servidor corriendo
- Ideales para desarrollo y refactoring

## 🐛 Debugging

```bash
# Debugging detallado
pytest src/tests/e2e/test_auth_api.py::TestUserAuthentication::test_login_success -v -s

# Ver todos los logs
pytest src/tests/e2e/ -v -s --tb=long

# Solo un test específico
pytest src/tests/e2e/test_auth_api.py::TestCompleteAuthFlow::test_complete_flow_register_to_logout -v -s
```

La opción `-s` permite ver prints y logs durante la ejecución.

## 🔄 Migración desde Simple Test.http

Los tests pytest han sido convertidos desde `Simple Test.http` manteniendo:
- ✅ Misma funcionalidad de validación
- ✅ Mismos casos de prueba
- ✅ Mismos datos de test
- ✅ Compatibilidad con CI/CD
- ✅ Reportes automáticos