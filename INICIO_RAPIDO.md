# ⚡ INICIO RÁPIDO - Migración SybaseIQ con LangChain + Claude API

**Migra tus store procedures en menos de 10 minutos**

---

## 🎯 Paso 1: Instalar (2 minutos)

```bash
# Clonar
git clone https://github.com/tuorganizacion/sybase-migration.git
cd sybase-migration

# Ambiente virtual
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows

# Instalar dependencias
pip install -r requirements.txt

# Verificar
python -c "from migration_agent_langchain import SybaseIQMigrationAgent; print('✅ OK')"
```

---

## 🔑 Paso 2: Obtener Credenciales (1 minuto)

### API Key de Anthropic
1. Ir a https://console.anthropic.com
2. Crear API Key
3. Copiarla

### Credenciales de SybaseIQ
- Servidor: `tu-servidor.com`
- Base de datos: `mi_bd`
- Usuario: `mi_usuario`
- Contraseña: `mi_contraseña`

---

## ⚙️ Paso 3: Configurar (1 minuto)

### Opción A: Con archivo YAML (recomendado)

```bash
# Crear archivo config.yaml
cat > config.yaml << 'EOF'
sybase:
  server: "tu-servidor.com"
  database: "mi_bd"
  username: "${SYBASE_USER}"
  password: "${SYBASE_PASSWORD}"
  port: 5000

migration:
  type: "source_replacement"
  source_mapping:
    "LEGACY_SOURCE": "NEW_SOURCE"
    "OLD_SCHEMA": "NEW_SCHEMA"
  
  options:
    validate_before_execution: true
    backup_before_migration: true
    batch_size: 10
  
  output_directory: "./migration_output"
EOF
```

### Opción B: Variables de entorno

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export SYBASE_USER="mi_usuario"
export SYBASE_PASSWORD="mi_contraseña"
```

---

## 🧪 Paso 4: Probar Conexión (1 minuto)

```bash
# Verificar que todo funciona
python cli.py test-connection \
  --server tu-servidor.com \
  --db mi_bd \
  --user mi_usuario \
  --pass mi_contraseña

# Debería mostrar:
# ✅ Conexión exitosa
# Procedures encontrados: 42
```

---

## 🚀 Paso 5: Ejecutar Migración (1 minuto + espera)

```bash
# Iniciar migración
python cli.py migrate --config config.yaml

# O con opciones:
python cli.py migrate \
  --config config.yaml \
  --limit 10 \
  --output ./migration_result \
  --skip-backup

# Resultado:
# [FASE 1] Haciendo backup...
# [FASE 2] Extrayendo procedures...
# [FASE 3] Analizando...
# [FASE 4] Generando scripts...
# ✅ COMPLETADO
```

---

## 📊 Ver Resultados

```bash
# Archivos generados en ./migration_output/
ls -la migration_output/

# Ver reporte
cat migration_output/migration_report_*.json | jq .

# Ver script de migración
cat migration_output/migration_script_*.sql

# Ver plan de rollback
cat migration_output/rollback_plan_*.sql
```

---

## ✅ Validación (ANTES de ejecutar en PROD)

### Paso 1: Revisar script
```bash
# Leer script generado
cat migration_output/migration_script_*.sql

# Verificar:
# ✓ Todas las fuentes fueron reemplazadas
# ✓ Sintaxis SQL correcta
# ✓ Transacciones están presentes
# ✓ Comentarios son claros
```

### Paso 2: Probar en DEV
```bash
# Conectar a BD de prueba
sqlcmd -S dev-server -d test_db -U admin

# Ejecutar script
:r migration_output/migration_script_*.sql

# Verificar resultados
SELECT * FROM sys.procedures WHERE name LIKE '%sp_%'
```

### Paso 3: Ejecutar en PROD
```bash
# En SybaseIQ
sqlcmd -S prod-server -d production -U admin

# Ejecutar (con backup primero)
BACKUP DATABASE production TO 'backup_location'
:r migration_output/migration_script_*.sql

# Verificar éxito
SELECT @@ERROR
```

### Paso 4 (Si algo falla): Rollback
```bash
# Ejecutar plan de rollback
:r migration_output/rollback_plan_*.sql

# Verificar restauración
SELECT COUNT(*) FROM sysobjects WHERE type = 'P'
```

---

## 🔍 Exploración Adicional

### Ver procedures afectados
```bash
python cli.py list-affected --config config.yaml --output affected.json
```

### Analizar sin ejecutar
```bash
python cli.py analyze \
  --config config.yaml \
  --limit 5 \
  --output analysis.json
```

### Información del sistema
```bash
python cli.py info --config config.yaml
```

---

## 🐛 Troubleshooting Rápido

### Error: "ANTHROPIC_API_KEY not found"
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Error: "Unable to connect to SybaseIQ"
```bash
# Probar conexión manual
python -c "
import pyodbc
conn = pyodbc.connect(
    'Driver={Adaptive Server Enterprise};'
    'Server=tu-servidor.com,5000;'
    'Database=mi_bd;'
    'Uid=usuario;'
    'Pwd=contraseña;'
)
print('✅ Conectado')
conn.close()
"
```

### Error: "pyodbc no encontrado"
```bash
pip install pyodbc
# En Linux: sudo apt-get install python3-dev unixodbc-dev
```

---

## 💡 Próximos Pasos

### Integración con CI/CD
```yaml
# GitHub Actions (.github/workflows/migrate.yml)
name: SybaseIQ Migration
on: [push]
jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Migration
        run: |
          pip install -r requirements.txt
          python cli.py migrate --config config.yaml
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SYBASE_USER: ${{ secrets.SYBASE_USER }}
          SYBASE_PASSWORD: ${{ secrets.SYBASE_PASSWORD }}
```

### Migración por Fases
```bash
# Fase 1: Solo procedures de lectura
python cli.py migrate --config config.yaml --phase read

# Fase 2: Solo procedures de escritura
python cli.py migrate --config config.yaml --phase write

# Fase 3: Todos
python cli.py migrate --config config.yaml --phase all
```

### Alertas por Email
```python
from config_y_ejemplos import send_migration_alert

result = agent.run_migration_pipeline()
send_migration_alert(
    result,
    email_to="equipo@example.com",
    email_from="migracion@example.com",
    smtp_server="smtp.gmail.com"
)
```

---

## 📚 Documentación Completa

Ver `README.md` para:
- Arquitectura detallada
- Todos los comandos CLI
- Configuración avanzada
- Casos de uso
- API Reference

---

## ⏱️ Tiempo Estimado

| Tarea | Tiempo |
|-------|--------|
| Instalación | 2 min |
| Configuración | 1 min |
| Test de conexión | 1 min |
| Análisis de 50 procedures | 3 min |
| Generación de scripts | 1 min |
| Validación manual | 5 min |
| **Total** | **~13 min** |

---

## 🎓 Aprender Más

### Entender el agente
```bash
# Ver código principal
less migration_agent_langchain.py

# Ver ejemplos
less config_y_ejemplos.py

# Ver CLI
less cli.py
```

### Debugar
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from migration_agent_langchain import SybaseIQMigrationAgent
# Ahora verás logs detallados
```

### Personalizar
```python
# Crear tu propia versión
from migration_agent_langchain import SybaseIQMigrationAgent

class MyCustomAgent(SybaseIQMigrationAgent):
    def analyze_procedure(self, name, code):
        # Tu lógica personalizada
        return super().analyze_procedure(name, code)
```

---

## ✨ Éxito

¡Enhorabuena! Ya tienes un agente inteligente para migrar tus store procedures.

```
┌──────────────────────────────────────┐
│  ✅ MIGRACIÓN COMPLETADA             │
│                                      │
│  Procedures migrados: 42             │
│  Fuentes reemplazadas: 3             │
│  Riesgos detectados: 0               │
│  Scripts listos: SÍ                  │
│  Rollback preparado: SÍ              │
│                                      │
│  🚀 ¡Listo para producción!          │
└──────────────────────────────────────┘
```

---

## 🆘 Ayuda

- **Documentación**: Ver `README.md`
- **Ejemplos**: Ver `config_y_ejemplos.py`
- **Comandos CLI**: `python cli.py --help`
- **Issues**: GitHub Issues
- **Email**: migration-support@example.com

---

**Happy Migrating! 🚀**
