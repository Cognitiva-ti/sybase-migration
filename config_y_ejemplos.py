# ===========================================================================
# config.yaml - Configuración de Migración SybaseIQ
# ===========================================================================
# Edita este archivo con tus credenciales y configuración específica

sybase:
  server: "tu-servidor-sybase.com"
  database: "production"
  username: "${SYBASE_USER}"              # Usa variables de entorno
  password: "${SYBASE_PASSWORD}"
  port: 5000
  timeout: 30

migration:
  type: "source_replacement"              # source_replacement | schema_change | hybrid
  
  # Mapeo de fuentes antiguas -> nuevas
  source_mapping:
    "LEGACY_DATASOURCE": "NEW_DATASOURCE"
    "OLD_PROD_DB": "CURRENT_PROD_DB"
    "LEGACY_SCHEMA": "NEW_SCHEMA"
    "old_connection": "new_connection"
    "db_antigua": "db_nueva"
  
  # Opciones de ejecución
  options:
    validate_before_execution: true
    backup_before_migration: true
    create_rollback_plan: true
    batch_size: 10                        # Procedures a procesar por lote
    
  # Salida
  output_directory: "./migration_output"


# ===========================================================================
# Ejemplo de uso: config.py
# ===========================================================================

from pathlib import Path
import yaml
import os
from migration_agent_langchain import (
    SybaseIQMigrationAgent,
    MigrationConfig,
    SybaseIQConfig,
    MigrationType
)


def load_config(config_file: str = "config.yaml") -> MigrationConfig:
    """Carga configuración desde archivo YAML"""
    
    # Leer YAML
    with open(config_file, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)
    
    # Expandir variables de entorno
    def expand_env_vars(obj):
        if isinstance(obj, dict):
            return {k: expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return os.path.expandvars(obj)
        return obj
    
    config_dict = expand_env_vars(config_dict)
    
    # Crear configuración
    sybase_config = SybaseIQConfig(
        server=config_dict['sybase']['server'],
        database=config_dict['sybase']['database'],
        username=config_dict['sybase']['username'],
        password=config_dict['sybase']['password'],
        port=config_dict['sybase']['port'],
        timeout=config_dict['sybase']['timeout'],
    )
    
    migration_config = MigrationConfig(
        source_mapping=config_dict['migration']['source_mapping'],
        sybase_config=sybase_config,
        migration_type=MigrationType(config_dict['migration']['type']),
        validate_before_execution=config_dict['migration']['options']['validate_before_execution'],
        backup_before_migration=config_dict['migration']['options']['backup_before_migration'],
        create_rollback_plan=config_dict['migration']['options']['create_rollback_plan'],
        batch_size=config_dict['migration']['options']['batch_size'],
        output_dir=config_dict['migration']['output_directory']
    )
    
    return migration_config


def main():
    """Uso principal con archivo de configuración"""
    
    # Cargar configuración
    config = load_config("config.yaml")
    
    # Crear directorio de salida
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Ejecutar agente
    agent = SybaseIQMigrationAgent(config)
    result = agent.run_migration_pipeline()
    
    return result


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    result = main()
    
    if result['success']:
        print("\n✅ Pipeline completado exitosamente")
    else:
        print(f"\n❌ Error: {result['error']}")


# ===========================================================================
# Ejemplo de uso: script.py (Sin archivo de configuración)
# ===========================================================================

from migration_agent_langchain import (
    SybaseIQMigrationAgent,
    MigrationConfig,
    SybaseIQConfig,
    MigrationType
)


def example_direct():
    """Uso directo sin archivo de configuración"""
    
    # Configurar conexión a SybaseIQ
    sybase_config = SybaseIQConfig(
        server="prod-sybase.mycompany.com",
        database="financial_db",
        username="migration_user",
        password="SecurePassword123!",
        port=5000
    )
    
    # Configurar migración
    migration_config = MigrationConfig(
        source_mapping={
            "LEGACY_DATAMART": "MODERN_DATAMART",
            "OLD_PROD_SOURCE": "NEW_PROD_SOURCE",
            "db_2020": "db_2024",
            "archive_schema": "production_schema",
        },
        sybase_config=sybase_config,
        migration_type=MigrationType.SOURCE_REPLACEMENT,
        validate_before_execution=True,
        backup_before_migration=True,
        create_rollback_plan=True,
        batch_size=15,
        output_dir="./sybase_migration"
    )
    
    # Ejecutar
    agent = SybaseIQMigrationAgent(migration_config)
    result = agent.run_migration_pipeline()
    
    return result


# ===========================================================================
# Ejemplo avanzado: Migración selectiva por fases
# ===========================================================================

def example_phased_migration():
    """Migración en fases por tipo de procedure"""
    
    sybase_config = SybaseIQConfig(
        server="prod-sybase.mycompany.com",
        database="operational_db",
        username="migration_user",
        password="SecurePassword123!",
    )
    
    # FASE 1: Procedures de lectura (bajo riesgo)
    print("="*60)
    print("FASE 1: Migrando procedures de LECTURA")
    print("="*60)
    
    config_phase1 = MigrationConfig(
        source_mapping={
            "OLD_SOURCE": "NEW_SOURCE",
        },
        sybase_config=sybase_config,
        migration_type=MigrationType.SOURCE_REPLACEMENT,
        output_dir="./phase1_migration"
    )
    
    agent1 = SybaseIQMigrationAgent(config_phase1)
    
    # Obtener procedures de lectura
    read_procedures = {
        name: code
        for name, code in agent1.db.get_all_procedures().items()
        if 'SELECT' in code.upper() and 'INSERT' not in code.upper()
    }
    
    agent1.batch_analyze(read_procedures)
    migration_script_1 = agent1.generate_migration_script()
    agent1.export_report("phase1_report.json")
    
    print(f"✅ FASE 1: {len(agent1.analyses)} procedures de lectura analizados")
    
    # FASE 2: Procedures de escritura (mayor riesgo)
    print("\n" + "="*60)
    print("FASE 2: Migrando procedures de ESCRITURA")
    print("="*60)
    
    config_phase2 = MigrationConfig(
        source_mapping=config_phase1.source_mapping,
        sybase_config=sybase_config,
        migration_type=MigrationType.SOURCE_REPLACEMENT,
        output_dir="./phase2_migration"
    )
    
    agent2 = SybaseIQMigrationAgent(config_phase2)
    
    # Obtener procedures de escritura
    write_procedures = {
        name: code
        for name, code in agent2.db.get_all_procedures().items()
        if 'INSERT' in code.upper() or 'UPDATE' in code.upper() or 'DELETE' in code.upper()
    }
    
    agent2.batch_analyze(write_procedures)
    migration_script_2 = agent2.generate_migration_script()
    agent2.export_report("phase2_report.json")
    
    print(f"✅ FASE 2: {len(agent2.analyses)} procedures de escritura analizados")
    
    # Resumen final
    print("\n" + "="*60)
    print("✅ MIGRACIONES COMPLETADAS EN 2 FASES")
    print("="*60)
    print(f"Total procedures: {len(agent1.analyses) + len(agent2.analyses)}")
    print(f"Scripts generados en: ./phase1_migration y ./phase2_migration")


# ===========================================================================
# Ejemplo: Integración con CI/CD
# ===========================================================================

import subprocess
from datetime import datetime


def example_with_git_integration():
    """Integración con Git para versionado de migraciones"""
    
    import os
    from migration_agent_langchain import (
        SybaseIQMigrationAgent,
        MigrationConfig,
        SybaseIQConfig,
        MigrationType
    )
    
    # Configuración
    sybase_config = SybaseIQConfig(
        server="prod-sybase.mycompany.com",
        database="operational_db",
        username="migration_user",
        password="SecurePassword123!",
    )
    
    migration_config = MigrationConfig(
        source_mapping={
            "OLD_SOURCE": "NEW_SOURCE",
            "LEGACY_DB": "CURRENT_DB",
        },
        sybase_config=sybase_config,
        output_dir="./migrations"
    )
    
    # Crear directorio de migraciones versionado
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    migration_dir = f"./migrations/{timestamp}"
    os.makedirs(migration_dir, exist_ok=True)
    
    migration_config.output_dir = migration_dir
    
    # Ejecutar agente
    agent = SybaseIQMigrationAgent(migration_config)
    result = agent.run_migration_pipeline()
    
    if result['success']:
        # Commit a Git
        try:
            subprocess.run([
                "git", "add", "-A"
            ], check=True, cwd="./migrations")
            
            commit_message = (
                f"Migration: Replace OLD_SOURCE with NEW_SOURCE\n\n"
                f"Timestamp: {timestamp}\n"
                f"Procedures analyzed: {result['procedures_analyzed']}\n"
                f"Procedures affected: {result['procedures_affected']}"
            )
            
            subprocess.run([
                "git", "commit", "-m", commit_message
            ], check=True, cwd="./migrations")
            
            print(f"✅ Migración versionada en Git: {migration_dir}")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Error committing a Git: {e}")
    
    return result


# ===========================================================================
# Instalación de dependencias
# ===========================================================================

# Instalar requerimientos:
# pip install langchain langchain-anthropic pyodbc pydantic pyyaml

# Variables de entorno requeridas:
# export ANTHROPIC_API_KEY="sk-ant-..."
# export SYBASE_USER="tu_usuario"
# export SYBASE_PASSWORD="tu_contraseña"


# ===========================================================================
# Línea de comando (CLI)
# ===========================================================================

"""
Para usar como CLI:

python migration_agent_langchain.py --config config.yaml --output ./output

Argumentos opcionales:
  --config FILE           Archivo de configuración YAML
  --output DIR           Directorio de salida
  --limit N              Analizar solo N procedures
  --dry-run              Simular sin ejecutar cambios reales
  --phase 1|2|3          Ejecutar solo una fase específica
"""


# ===========================================================================
# Monitoreo y alertas
# ===========================================================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_migration_alert(result: dict, email_to: str, email_from: str, smtp_server: str):
    """Envía alerta de migración por email"""
    
    status = "✅ EXITOSA" if result['success'] else "❌ FALLIDA"
    
    message = MIMEMultipart()
    message['Subject'] = f"Migración SybaseIQ {status}"
    message['From'] = email_from
    message['To'] = email_to
    
    body = f"""
    Estado: {status}
    
    Detalles:
    - Procedures analizados: {result.get('procedures_analyzed', 'N/A')}
    - Procedures afectados: {result.get('procedures_affected', 'N/A')}
    - Reporte: {result.get('report_file', 'N/A')}
    
    {'Error: ' + result.get('error', '') if not result['success'] else 'Migración completada exitosamente'}
    """
    
    message.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(smtp_server, 587)
        server.starttls()
        server.login(email_from, "password")
        server.send_message(message)
        server.quit()
        print(f"✅ Alerta enviada a: {email_to}")
    except Exception as e:
        print(f"❌ Error enviando alerta: {e}")
