# 🚀 Agente de Migración SybaseIQ - LangChain + Claude API

**Automatiza la migración de store procedures con IA usando LangChain y Claude API de Anthropic**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/langchain-0.1.13+-green.svg)](https://python.langchain.com/)
[![Anthropic Claude](https://img.shields.io/badge/anthropic-claude--opus--4--6-red.svg)](https://www.anthropic.com/)

---

## 📋 Tabla de Contenidos

- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso Rápido](#uso-rápido)
- [Configuración](#configuración)
- [Ejemplos](#ejemplos)
- [CLI](#cli)
- [Arquitectura](#arquitectura)
- [FAQ](#faq)

---

## ✨ Características

✅ **Análisis Inteligente**
- Claude IA analiza automáticamente store procedures
- Identifica todas las referencias a fuentes de datos antiguas
- Detecta riesgos y dependencias

✅ **Generación Automatizada**
- Genera scripts SQL válidos y seguros
- Respeta transacciones y estructuras de datos
- Código listo para ejecutar en SybaseIQ

✅ **Validación Robusta**
- Valida cambios antes de ejecutar
- Detecta problemas de sintaxis
- Verifica mantención de lógica

✅ **Planes de Contingencia**
- Genera automáticamente planes de rollback
- Scripts seguros y reversibles
- Transacciones ACID garantizadas

✅ **Acceso Directo a BD**
- Conecta directamente a SybaseIQ
- Extrae procedures automáticamente
- Hace backups antes de cambios

✅ **Reportes Detallados**
- Análisis JSON completo
- Estadísticas de migración
- Histórico de cambios

---

## 📦 Requisitos

### Sistema
- Python 3.9+
- SybaseIQ 16.0+ (o ASE)
- Cliente ODBC para SybaseIQ

### Dependencias
```bash
langchain==0.1.13
langchain-anthropic==0.1.15
anthropic==0.25.1
pyodbc==4.0.35
pydantic==2.5.0
pyyaml==6.0.1
```

### Credenciales
- API Key de Anthropic (obtén en https://console.anthropic.com)
- Credenciales de SybaseIQ

---

## ⚡ Instalación

### 1. Clonar repositorio
```bash
git clone https://github.com/tuorganizacion/sybase-migration.git
cd sybase-migration
```

### 2. Crear ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# o
venv\Scripts\activate     # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export SYBASE_USER="tu_usuario"
export SYBASE_PASSWORD="tu_contraseña"
```

### 5. Verificar instalación
```bash
python -c "from migration_agent_langchain import SybaseIQMigrationAgent; print('✅ OK')"
```

---

## 🚀 Uso Rápido

### Con archivo de configuración
```bash
# 1. Copiar y editar configuración
cp config_ejemplo.yaml config.yaml
# Editar config.yaml con tus credenciales

# 2. Ejecutar migración
python cli.py migrate --config config.yaml

# 3. Revisar reportes
cat migration_output/migration_report_*.json
```

### Directamente en Python
```python
from migration_agent_langchain import (
    SybaseIQMigrationAgent,
    MigrationConfig,
    SybaseIQConfig,
    MigrationType
)

# Configurar
config = MigrationConfig(
    source_mapping={
        "OLD_SOURCE": "NEW_SOURCE",
        "LEGACY_DB": "PRODUCTION_DB",
    },
    sybase_config=SybaseIQConfig(
        server="srv.com",
        database="mydb",
        username="admin",
        password="secret"
    )
)

# Ejecutar
agent = SybaseIQMigrationAgent(config)
result = agent.run_migration_pipeline()

print(f"✅ {result['procedures_analyzed']} procedures analizados")
```

---

## ⚙️ Configuración

### Archivo config.yaml

```yaml
sybase:
  server: "tu-servidor.com"
  database: "production"
  username: "${SYBASE_USER}"
  password: "${SYBASE_PASSWORD}"
  port: 5000
  timeout: 30

migration:
  type: "source_replacement"
  source_mapping:
    "OLD_SOURCE": "NEW_SOURCE"
    "LEGACY_DB": "PRODUCTION_DB"
    "old_schema": "new_schema"
  
  options:
    validate_before_execution: true
    backup_before_migration: true
    create_rollback_plan: true
    batch_size: 10
  
  output_directory: "./migration_output"
```

### Variables de Entorno

```bash
# Requeridas
ANTHROPIC_API_KEY=sk-ant-...

# Opcionales (si no están en config.yaml)
SYBASE_USER=mi_usuario
SYBASE_PASSWORD=mi_contraseña
```

---

## 📚 Ejemplos

### Ejemplo 1: Migración básica
```bash
python cli.py migrate --config config.yaml
```

### Ejemplo 2: Probar conexión
```bash
python cli.py test-connection \
  --server srv.com \
  --db mydb \
  --user admin \
  --pass secret
```

### Ejemplo 3: Listar procedures afectados
```bash
python cli.py list-affected \
  --config config.yaml \
  --output affected_procs.json
```

### Ejemplo 4: Análisis sin ejecución
```bash
python cli.py analyze \
  --config config.yaml \
  --limit 20 \
  --output analysis.json
```

### Ejemplo 5: Migración por fases
```python
from config_y_ejemplos import example_phased_migration
example_phased_migration()
```

---

## 💻 CLI

```bash
# Ver ayuda
python cli.py --help

# Migración completa
python cli.py migrate --config config.yaml [--output DIR] [--limit N]

# Opciones especiales
python cli.py migrate --config config.yaml --dry-run        # Simular
python cli.py migrate --config config.yaml --skip-backup    # Sin backup
python cli.py migrate --config config.yaml --skip-validation # Sin validación
python cli.py migrate --config config.yaml --phase read      # Solo lectura
python cli.py migrate --config config.yaml --phase write     # Solo escritura

# Otros comandos
python cli.py test-connection --server S --db D --user U --pass P
python cli.py list-affected --config config.yaml [--source OLD_SOURCE]
python cli.py analyze --config config.yaml [--limit 10]
python cli.py info [--config config.yaml]
```

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────┐
│         Agente de Migración SybaseIQ                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  CLI Interface (cli.py)                     │   │
│  │  - migrate, test-connection, analyze...     │   │
│  └──────────────────┬──────────────────────────┘   │
│                     │                              │
│  ┌──────────────────▼──────────────────────────┐   │
│  │  SybaseIQMigrationAgent (main)              │   │
│  │  - Coordina pipeline completo              │   │
│  │  - Usa LangChain + Claude API              │   │
│  └──────────────────┬──────────────────────────┘   │
│                     │                              │
│  ┌──────────────────▼──────────────────────────┐   │
│  │  SybaseIQDatabase (BD Connection)           │   │
│  │  - Extrae procedures                        │   │
│  │  - Ejecuta scripts                          │   │
│  │  - Maneja transacciones                     │   │
│  └──────────────────┬──────────────────────────┘   │
│                     │                              │
│  ┌──────────────────▼──────────────────────────┐   │
│  │  Claude API (LangChain)                     │   │
│  │  - Analiza procedures                       │   │
│  │  - Genera código migrado                    │   │
│  │  - Valida cambios                           │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Flujo de ejecución

```
1. EXTRACCIÓN
   BD → Extrae procedures mediante ODBC

2. ANÁLISIS (con IA)
   Procedures → Claude API → Análisis detallado

3. GENERACIÓN
   Análisis → Claude API → Scripts SQL

4. VALIDACIÓN
   Scripts → Claude API → Valida cambios

5. APROBACIÓN
   Reporte → Usuario revisa

6. EJECUCIÓN
   Scripts → BD → Transacciones ACID

7. REPORTES
   Análisis → JSON completo con histórico
```

---

## 📊 Salidas Generadas

### 1. migration_script_TIMESTAMP.sql
Script SQL listo para ejecutar:
```sql
BEGIN TRANSACTION

DROP PROCEDURE IF EXISTS sp_GetCustomers
GO

CREATE PROCEDURE sp_GetCustomers
    @Status VARCHAR(20) = 'ACTIVE'
AS
BEGIN
    SELECT CustomerID, Name, Email
    FROM NEW_DATASOURCE.dbo.Customers
    WHERE Status = @Status
    ORDER BY Name
END
GO

COMMIT TRANSACTION
```

### 2. rollback_plan_TIMESTAMP.sql
Plan de contingencia:
```sql
BEGIN TRANSACTION
-- Restaurar procedures originales
-- ... scripts de rollback
COMMIT TRANSACTION
```

### 3. migration_report_TIMESTAMP.json
Reporte detallado:
```json
{
  "timestamp": "2024-01-15T10:30:45",
  "migration_config": {
    "source_mapping": {...},
    "total_procedures": 42
  },
  "analyses": [
    {
      "procedure_name": "sp_GetCustomers",
      "found_old_sources": ["OLD_DATASOURCE"],
      "changes_needed": ["Reemplazar OLD_DATASOURCE con NEW_DATASOURCE"],
      "risks": [],
      "confidence_score": 0.95
    }
  ],
  "summary": {
    "procedures_analyzed": 42,
    "procedures_with_changes": 42,
    "average_confidence": 0.94
  }
}
```

---

## 🔍 Casos de Uso

### Caso 1: Cambio de fuente de datos
```python
source_mapping = {
    "LEGACY_DATASOURCE": "NEW_DATASOURCE"
}
```

### Caso 2: Cambio de esquema
```python
source_mapping = {
    "dbo.old_table": "dbo.new_table",
    "legacy_schema": "production_schema"
}
```

### Caso 3: Migración de BD completa
```python
source_mapping = {
    "OLD_PROD_DB": "NEW_PROD_DB",
    "OLD_STAGING": "NEW_STAGING"
}
```

### Caso 4: Migración por fases
- Fase 1: Procedures de lectura (bajo riesgo)
- Fase 2: Procedures de escritura (mayor riesgo)
- Fase 3: Procedures críticos (máxima validación)

---

## 🛡️ Seguridad

✅ **Buenas prácticas**
- Credenciales en variables de entorno
- Backups automáticos antes de cambios
- Transacciones ACID para atomicidad
- Planes de rollback generados automáticamente
- Validación de cambios antes de ejecutar
- Logging detallado de todas las acciones

⚠️ **Precauciones**
1. NUNCA poner credenciales en código
2. Usar archivo .env con credenciales
3. Probar en DEV/TEST antes de PROD
4. Mantener rollback_plan accesible
5. Revisar scripts antes de ejecutar
6. Hacer backups periódicos

---

## 📖 Documentación Adicional

- [API de Claude](https://docs.claude.com)
- [LangChain Documentation](https://python.langchain.com)
- [SybaseIQ Docs](https://help.sap.com)
- [pyodbc](https://github.com/mkleehammer/pyodbc)

---

## ❓ FAQ

### P: ¿Puedo usar esto en producción?
**R:** Sí, pero revisa cuidadosamente los scripts generados antes de ejecutar.

### P: ¿Qué pasa si algo sale mal?
**R:** Ejecuta el rollback_plan.sql generado automáticamente.

### P: ¿Cuánto cuesta usar el agente?
**R:** Solo pagas por las llamadas a Claude API (~0.03 USD por migración).

### P: ¿Soporta otros motores de BD?
**R:** Actualmente solo SybaseIQ, pero es extensible.

### P: ¿Puedo migrar sin acceso directo a BD?
**R:** Sí, usando archivos SQL en lugar de conexión ODBC.

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a rama (`git push origin feature/AmazingFeature`)
5. Abre Pull Request

---

## 📄 Licencia

MIT License - Ver LICENSE.md

---

## 📞 Soporte

- Crear issue en GitHub
- Email: migration@example.com
- Slack: #database-migrations

---

## 🙏 Agradecimientos

- Anthropic por Claude API
- LangChain Team por el framework
- SAP/Sybase por SybaseIQ

---

**Última actualización:** Enero 2024
**Mantenedor:** Tu Equipo
**Versión:** 1.0.0
