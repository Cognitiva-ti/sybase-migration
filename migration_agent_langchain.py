#!/usr/bin/env python3
"""
Agente de Migración SybaseIQ con LangChain + Claude API
Reemplaza referencias de fuentes de datos en store procedures
Utiliza acceso directo a la base de datos
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import pyodbc
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.chains import LLMChain
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


# ============================================================================
# CONFIGURACIÓN Y LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationType(str, Enum):
    """Tipos de migración disponibles"""
    SOURCE_REPLACEMENT = "source_replacement"
    SCHEMA_CHANGE = "schema_change"
    HYBRID = "hybrid"


@dataclass
class SybaseIQConfig:
    """Configuración de conexión a SybaseIQ"""
    server: str
    database: str
    username: str
    password: str
    port: int = 5000
    driver: str = "Adaptive Server Enterprise"
    timeout: int = 30

    def get_connection_string(self) -> str:
        """Genera string de conexión ODBC"""
        return (
            f"Driver={{{self.driver}}};"
            f"Server={self.server},"
            f"{self.port};"
            f"Database={self.database};"
            f"Uid={self.username};"
            f"Pwd={self.password};"
            f"Timeout={self.timeout};"
        )


@dataclass
class MigrationConfig:
    """Configuración de migración"""
    source_mapping: Dict[str, str]  # Old -> New
    sybase_config: SybaseIQConfig
    migration_type: MigrationType = MigrationType.SOURCE_REPLACEMENT
    validate_before_execution: bool = True
    create_rollback_plan: bool = True
    backup_before_migration: bool = True
    batch_size: int = 10
    output_dir: str = "./"


class ProcedureAnalysis(BaseModel):
    """Resultado del análisis de un procedure"""
    procedure_name: str
    found_old_sources: List[str] = Field(default_factory=list)
    changes_needed: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    migration_type: str
    migrated_code: str
    validation_notes: str = ""
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.9)


class MigrationValidation(BaseModel):
    """Resultado de validación"""
    is_valid: bool
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# ============================================================================
# CONEXIÓN A SYBASEIQ
# ============================================================================

class SybaseIQDatabase:
    """Manejador de conexión a SybaseIQ"""

    def __init__(self, config: SybaseIQConfig):
        """
        Inicializa conexión a SybaseIQ
        
        Args:
            config: Configuración de conexión
        """
        self.config = config
        self.conn = None
        self._connect()

    def _connect(self):
        """Establece conexión a la BD"""
        try:
            conn_string = self.config.get_connection_string()
            self.conn = pyodbc.connect(conn_string, autocommit=False)
            logger.info(f"✅ Conectado a SybaseIQ: {self.config.server}/{self.config.database}")
        except Exception as e:
            logger.error(f"❌ Error de conexión a SybaseIQ: {e}")
            raise

    def disconnect(self):
        """Cierra la conexión"""
        if self.conn:
            self.conn.close()
            logger.info("🔌 Desconectado de SybaseIQ")

    def get_all_procedures(self) -> Dict[str, str]:
        """
        Obtiene todos los store procedures
        
        Returns:
            Dict con nombre -> código SQL
        """
        query = """
        SELECT DISTINCT 
            so.name,
            sc.text
        FROM syscomments sc
        INNER JOIN sysobjects so ON sc.id = so.id
        WHERE so.type = 'P'  -- P = Stored Procedure
        ORDER BY so.name, sc.colid
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            
            procedures = {}
            current_proc = None
            current_code = ""
            
            for row in cursor.fetchall():
                proc_name = row[0].strip()
                proc_text = row[1]
                
                if current_proc != proc_name and current_proc is not None:
                    procedures[current_proc] = current_code.strip()
                    current_code = proc_text
                elif current_proc != proc_name:
                    current_code = proc_text
                else:
                    current_code += proc_text
                
                current_proc = proc_name
            
            # Agregar el último procedure
            if current_proc:
                procedures[current_proc] = current_code.strip()
            
            cursor.close()
            logger.info(f"✅ {len(procedures)} procedures extraídos de SybaseIQ")
            return procedures
            
        except Exception as e:
            logger.error(f"❌ Error al extraer procedures: {e}")
            raise

    def get_procedure_by_name(self, name: str) -> Optional[str]:
        """Obtiene un procedure específico"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT text FROM syscomments WHERE id = OBJECT_ID(?) ORDER BY colid",
                (name,)
            )
            
            result = ""
            for row in cursor.fetchall():
                result += row[0]
            
            cursor.close()
            return result if result else None
            
        except Exception as e:
            logger.error(f"❌ Error al obtener procedure {name}: {e}")
            return None

    def get_procedures_using_source(self, source_name: str) -> Dict[str, str]:
        """Obtiene procedures que usan una fuente específica"""
        all_procs = self.get_all_procedures()
        filtered = {
            name: code
            for name, code in all_procs.items()
            if source_name.upper() in code.upper()
        }
        return filtered

    def execute_script(self, script: str, transaction: bool = True) -> Tuple[bool, str]:
        """
        Ejecuta un script SQL
        
        Args:
            script: Script SQL a ejecutar
            transaction: Si usar transacción
            
        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            cursor = self.conn.cursor()
            
            if transaction:
                cursor.execute("BEGIN TRANSACTION")
            
            # Dividir script por GO (instrucción batch en TSQL)
            batches = script.split("GO")
            
            for batch in batches:
                batch = batch.strip()
                if batch:
                    cursor.execute(batch)
            
            if transaction:
                cursor.execute("COMMIT TRANSACTION")
            
            self.conn.commit()
            cursor.close()
            
            logger.info("✅ Script ejecutado exitosamente")
            return True, "Script ejecutado exitosamente"
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Error ejecutando script: {e}")
            return False, str(e)

    def backup_procedures(self, filepath: str) -> bool:
        """Hace backup de todos los procedures"""
        try:
            procedures = self.get_all_procedures()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(procedures, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Backup realizado: {filepath}")
            return True
        except Exception as e:
            logger.error(f"❌ Error haciendo backup: {e}")
            return False


# ============================================================================
# AGENTE DE MIGRACIÓN CON LANGCHAIN
# ============================================================================

class SybaseIQMigrationAgent:
    """Agente de migración con LangChain + Claude API"""

    def __init__(self, config: MigrationConfig):
        """
        Inicializa el agente
        
        Args:
            config: Configuración completa de migración
        """
        self.config = config
        self.db = SybaseIQDatabase(config.sybase_config)
        
        # Inicializar Claude con LangChain
        self.llm = ChatAnthropic(
            model="claude-opus-4-6",
            temperature=0,
            max_tokens=2048,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        self.analyses: List[ProcedureAnalysis] = []
        self.migration_history = []
        
        logger.info("🚀 Agente de Migración inicializado")

    def analyze_procedure(self, procedure_name: str, procedure_code: str) -> ProcedureAnalysis:
        """
        Analiza un store procedure
        
        Args:
            procedure_name: Nombre del procedure
            procedure_code: Código SQL
            
        Returns:
            Resultado del análisis
        """
        mapping_str = json.dumps(self.config.source_mapping, indent=2, ensure_ascii=False)
        
        # Template para análisis
        template = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en migración de bases de datos SybaseIQ.
Analizarás store procedures y proporcionarás análisis JSON estructurado.

IMPORTANTE:
- Responde SOLO con JSON válido
- Sin markdown, sin explicaciones adicionales
- Usa la estructura exacta solicitada"""),
            ("human", """
Mapeo de fuentes (Antiguo -> Nuevo):
{mapping}

Procedure a analizar:
Nombre: {procedure_name}
Código:
```sql
{procedure_code}
```

Analiza este procedure y responde en JSON con esta estructura EXACTA:
{{
    "procedure_name": "string",
    "found_old_sources": ["list of old sources found"],
    "changes_needed": ["list of specific changes"],
    "risks": ["potential risks or concerns"],
    "migration_type": "source_replacement|schema_change|hybrid",
    "migrated_code": "new SQL code here",
    "validation_notes": "important notes",
    "confidence_score": 0.95
}}

Reemplaza TODAS las referencias antiguas con las nuevas según el mapeo.
""")
        ])
        
        try:
            # Ejecutar chain con parser JSON
            parser = JsonOutputParser(pydantic_object=ProcedureAnalysis)
            chain = template | self.llm | parser
            
            result = chain.invoke({
                "mapping": mapping_str,
                "procedure_name": procedure_name,
                "procedure_code": procedure_code
            })
            
            analysis = ProcedureAnalysis(**result)
            self.analyses.append(analysis)
            
            logger.info(f"✅ Analizado: {procedure_name}")
            logger.debug(f"   - Fuentes encontradas: {analysis.found_old_sources}")
            logger.debug(f"   - Cambios: {len(analysis.changes_needed)}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analizando {procedure_name}: {e}")
            raise

    def batch_analyze(self, procedures: Dict[str, str], limit: Optional[int] = None) -> List[ProcedureAnalysis]:
        """
        Analiza múltiples procedures
        
        Args:
            procedures: Dict nombre -> código
            limit: Límite de procedures a analizar
            
        Returns:
            Lista de análisis
        """
        proc_list = list(procedures.items())
        if limit:
            proc_list = proc_list[:limit]
        
        logger.info(f"📋 Analizando {len(proc_list)} procedures...")
        
        for idx, (name, code) in enumerate(proc_list, 1):
            logger.info(f"[{idx}/{len(proc_list)}] Analizando: {name}")
            self.analyze_procedure(name, code)
        
        return self.analyses

    def generate_migration_script(self) -> str:
        """
        Genera script SQL completo de migración
        
        Returns:
            Script SQL migrado
        """
        if not self.analyses:
            logger.warning("⚠️ No hay análisis disponibles")
            return ""
        
        # Preparar datos para el prompt
        analyses_json = json.dumps(
            [asdict(a) for a in self.analyses],
            indent=2,
            ensure_ascii=False,
            default=str
        )
        
        template = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en SQL/TSQL para SybaseIQ.
Generarás un script de migración profesional y seguro.

REQUISITOS:
- Script listo para ejecutar en SybaseIQ
- Incluye transacciones
- Maneja dependencias entre procedures
- Idempotente (seguro ejecutar múltiples veces)
- Comentarios explicativos en inglés
- Responde SOLO con el script SQL"""),
            ("human", """
Basándote en estos análisis de migración, genera un script SQL completo:

{analyses}

El script debe:
1. Usar BEGIN TRANSACTION / COMMIT
2. Hacer DROP de procedures antiguos (si existen)
3. Crear procedures nuevos con cambios
4. Verificar éxito con mensajes
5. Ser seguro y reversible
6. Respetar el orden de dependencias

Genera el script completo sin explicaciones adicionales.
""")
        ])
        
        try:
            chain = template | self.llm
            
            result = chain.invoke({
                "analyses": analyses_json
            })
            
            script = result.content
            logger.info("✅ Script de migración generado")
            
            # Guardar script
            output_file = os.path.join(
                self.config.output_dir,
                f"migration_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            )
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(script)
            logger.info(f"💾 Script guardado en: {output_file}")
            
            return script
            
        except Exception as e:
            logger.error(f"❌ Error generando script: {e}")
            raise

    def validate_migration(self, original: str, migrated: str) -> MigrationValidation:
        """
        Valida que la migración sea correcta
        
        Args:
            original: Código original
            migrated: Código migrado
            
        Returns:
            Resultado de validación
        """
        template = ChatPromptTemplate.from_messages([
            ("system", """Eres un validador de scripts SQL para SybaseIQ.
Verificarás que migraciones sean correctas y seguras.
Responde SOLO con JSON válido sin markdown."""),
            ("human", """
Valida esta migración de procedure:

ORIGINAL:
```sql
{original}
```

MIGRADO:
```sql
{migrated}
```

Verifica:
1. ¿Se reemplazaron todas las fuentes antiguas?
2. ¿La lógica se mantiene intacta?
3. ¿Hay errores de sintaxis?
4. ¿Cambia el comportamiento?

Responde en JSON:
{{
    "is_valid": true/false,
    "issues": ["list of problems"],
    "warnings": ["list of warnings"],
    "recommendations": ["list of recommendations"]
}}
""")
        ])
        
        try:
            parser = JsonOutputParser(pydantic_object=MigrationValidation)
            chain = template | self.llm | parser
            
            result = chain.invoke({
                "original": original,
                "migrated": migrated
            })
            
            return MigrationValidation(**result)
            
        except Exception as e:
            logger.error(f"❌ Error validando: {e}")
            return MigrationValidation(
                is_valid=False,
                issues=[str(e)]
            )

    def generate_rollback_plan(self) -> str:
        """
        Genera plan de rollback
        
        Returns:
            Script de rollback
        """
        if not self.analyses:
            return ""
        
        proc_list = [a.procedure_name for a in self.analyses]
        
        template = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en rollback de SybaseIQ.
Generarás un script seguro para revertir migraciones.
Responde SOLO con el script SQL."""),
            ("human", """
Genera un script de ROLLBACK para estos procedures (restaura originales):
{procedures}

El script debe:
1. Ser idempotente
2. Restaurar procedures originales
3. Usar transacciones
4. Ser rápido y seguro
""")
        ])
        
        try:
            chain = template | self.llm
            
            result = chain.invoke({
                "procedures": "\n".join([f"  - {p}" for p in proc_list])
            })
            
            script = result.content
            logger.info("✅ Plan de rollback generado")
            
            # Guardar rollback
            output_file = os.path.join(
                self.config.output_dir,
                f"rollback_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            )
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(script)
            logger.info(f"💾 Rollback guardado en: {output_file}")
            
            return script
            
        except Exception as e:
            logger.error(f"❌ Error generando rollback: {e}")
            raise

    def export_report(self, filename: Optional[str] = None) -> str:
        """
        Exporta reporte completo en JSON
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Ruta del archivo
        """
        if not filename:
            filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.config.output_dir, filename)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "migration_config": {
                "source_mapping": self.config.source_mapping,
                "migration_type": self.config.migration_type.value,
                "total_procedures": len(self.analyses)
            },
            "analyses": [asdict(a) for a in self.analyses],
            "summary": {
                "procedures_analyzed": len(self.analyses),
                "procedures_with_changes": sum(1 for a in self.analyses if a.changes_needed),
                "total_changes": sum(len(a.changes_needed) for a in self.analyses),
                "procedures_with_risks": sum(1 for a in self.analyses if a.risks),
                "average_confidence": sum(a.confidence_score for a in self.analyses) / len(self.analyses) if self.analyses else 0
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📊 Reporte exportado: {filepath}")
        return filepath

    def run_migration_pipeline(self) -> Dict:
        """
        Ejecuta el pipeline completo de migración
        
        Returns:
            Resumen de ejecución
        """
        logger.info("\n" + "="*60)
        logger.info("🚀 INICIANDO PIPELINE DE MIGRACIÓN")
        logger.info("="*60 + "\n")
        
        try:
            # FASE 1: Backup
            if self.config.backup_before_migration:
                logger.info("[FASE 1] Haciendo backup...")
                backup_file = os.path.join(
                    self.config.output_dir,
                    f"procedures_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                self.db.backup_procedures(backup_file)
            
            # FASE 2: Extraer y Analizar
            logger.info("[FASE 2] Extrayendo procedures de la BD...")
            procedures = self.db.get_all_procedures()
            
            # Filtrar solo los que necesitan cambios
            affected = {}
            for old_source in self.config.source_mapping.keys():
                affected.update(self.db.get_procedures_using_source(old_source))
            
            logger.info(f"✅ {len(procedures)} procedures totales")
            logger.info(f"⚠️ {len(affected)} procedures afectados por cambios")
            
            logger.info("[FASE 3] Analizando procedures...")
            self.batch_analyze(affected, limit=self.config.batch_size)
            
            # FASE 4: Generar Scripts
            logger.info("[FASE 4] Generando scripts de migración...")
            migration_script = self.generate_migration_script()
            rollback_script = self.generate_rollback_plan()
            
            # FASE 5: Validación
            if self.config.validate_before_execution:
                logger.info("[FASE 5] Validando cambios...")
                validation_issues = 0
                for analysis in self.analyses:
                    validation = self.validate_migration(
                        self.db.get_procedure_by_name(analysis.procedure_name) or "",
                        analysis.migrated_code
                    )
                    if not validation.is_valid:
                        logger.warning(f"⚠️ Problemas en {analysis.procedure_name}")
                        for issue in validation.issues:
                            logger.warning(f"   - {issue}")
                        validation_issues += 1
                
                if validation_issues > 0:
                    logger.warning(f"⚠️ {validation_issues} procedures tienen problemas")
            
            # FASE 6: Exportar Reporte
            logger.info("[FASE 6] Exportando reporte...")
            report_file = self.export_report()
            
            # Resumen
            logger.info("\n" + "="*60)
            logger.info("✅ PIPELINE COMPLETADO EXITOSAMENTE")
            logger.info("="*60)
            logger.info(f"\n📊 RESUMEN:")
            logger.info(f"   Procedures analizados: {len(self.analyses)}")
            logger.info(f"   Fuentes a migrar: {len(self.config.source_mapping)}")
            logger.info(f"   Scripts generados: 2 (migración + rollback)")
            logger.info(f"\n📁 ARCHIVOS GENERADOS:")
            logger.info(f"   - Reporte: {report_file}")
            logger.info(f"   - Scripts en: {self.config.output_dir}/")
            
            return {
                "success": True,
                "procedures_analyzed": len(self.analyses),
                "procedures_affected": len(affected),
                "migration_script": migration_script,
                "rollback_script": rollback_script,
                "report_file": report_file
            }
            
        except Exception as e:
            logger.error(f"\n❌ ERROR EN PIPELINE: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            self.db.disconnect()

    def __del__(self):
        """Limpieza al destruir el objeto"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

def main():
    """Ejemplo completo de uso"""
    
    # Configuración de SybaseIQ
    sybase_config = SybaseIQConfig(
        server="tu-servidor.com",      # Reemplazar
        database="tu_base_datos",      # Reemplazar
        username="tu_usuario",         # Reemplazar
        password="tu_contraseña",      # Reemplazar
    )
    
    # Configuración de migración
    migration_config = MigrationConfig(
        source_mapping={
            "LEGACY_PROD": "NEW_PROD",
            "OLD_SCHEMA": "NEW_SCHEMA",
            "db_antigua": "db_nueva",
        },
        sybase_config=sybase_config,
        migration_type=MigrationType.SOURCE_REPLACEMENT,
        validate_before_execution=True,
        backup_before_migration=True,
        output_dir="./migration_output"
    )
    
    # Crear directorio de salida
    os.makedirs(migration_config.output_dir, exist_ok=True)
    
    # Ejecutar pipeline
    agent = SybaseIQMigrationAgent(migration_config)
    result = agent.run_migration_pipeline()
    
    if result["success"]:
        print("\n✅ Migración preparada exitosamente")
        print(f"Scripts guardados en: {migration_config.output_dir}/")
        print("\n⚠️ PRÓXIMOS PASOS:")
        print("1. Revisar migration_script_*.sql")
        print("2. Probar en base de datos DEV")
        print("3. Ejecutar en PRODUCCIÓN con precaución")
        print("4. Mantener rollback_plan_*.sql accesible")
    else:
        print(f"\n❌ Error: {result['error']}")


if __name__ == "__main__":
    main()
