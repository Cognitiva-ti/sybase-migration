#!/usr/bin/env python3
"""
CLI - Interfaz de línea de comandos para Agente de Migración SybaseIQ
"""

import argparse
import json
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import yaml
from dotenv import load_dotenv

from migration_agent_langchain import (
    SybaseIQMigrationAgent,
    MigrationConfig,
    SybaseIQConfig,
    MigrationType,
    SybaseIQDatabase
)


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationCLI:
    """Interfaz de línea de comandos para migración"""

    def __init__(self):
        """Inicializa CLI"""
        load_dotenv()

    def create_parser(self) -> argparse.ArgumentParser:
        """Crea parser de argumentos"""
        parser = argparse.ArgumentParser(
            description='Agente de Migración Automático para SybaseIQ',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Ejemplos:

  # Ejecutar migración completa
  python cli.py migrate --config config.yaml

  # Probar conexión a SybaseIQ
  python cli.py test-connection --server srv.com --db mydb --user admin --pass secret

  # Listar procedures afectados
  python cli.py list-affected --config config.yaml

  # Generar solo el plan de rollback
  python cli.py generate-rollback --config config.yaml

  # Ejecutar migración en fases
  python cli.py migrate --config config.yaml --phase read
            """
        )

        # Subcomandos principales
        subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar')

        # Comando: migrate
        migrate_parser = subparsers.add_parser(
            'migrate',
            help='Ejecutar pipeline completo de migración'
        )
        migrate_parser.add_argument(
            '--config',
            required=True,
            help='Archivo de configuración YAML'
        )
        migrate_parser.add_argument(
            '--output',
            default=None,
            help='Directorio de salida (por defecto: en config)'
        )
        migrate_parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limitar a N procedures'
        )
        migrate_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin hacer cambios'
        )
        migrate_parser.add_argument(
            '--phase',
            choices=['read', 'write', 'all'],
            default='all',
            help='Ejecutar solo procedures de lectura, escritura o ambos'
        )
        migrate_parser.add_argument(
            '--skip-backup',
            action='store_true',
            help='No hacer backup antes de migración'
        )
        migrate_parser.add_argument(
            '--skip-validation',
            action='store_true',
            help='No validar cambios'
        )

        # Comando: test-connection
        test_parser = subparsers.add_parser(
            'test-connection',
            help='Probar conexión a SybaseIQ'
        )
        test_parser.add_argument('--server', required=True, help='Servidor')
        test_parser.add_argument('--db', required=True, help='Base de datos')
        test_parser.add_argument('--user', required=True, help='Usuario')
        test_parser.add_argument('--pass', dest='password', required=True, help='Contraseña')
        test_parser.add_argument('--port', type=int, default=5000, help='Puerto')

        # Comando: list-affected
        list_parser = subparsers.add_parser(
            'list-affected',
            help='Listar procedures afectados por cambios'
        )
        list_parser.add_argument(
            '--config',
            required=True,
            help='Archivo de configuración'
        )
        list_parser.add_argument(
            '--source',
            help='Filtrar por fuente específica'
        )
        list_parser.add_argument(
            '--output',
            help='Guardar lista en archivo'
        )

        # Comando: generate-rollback
        rollback_parser = subparsers.add_parser(
            'generate-rollback',
            help='Generar solo plan de rollback'
        )
        rollback_parser.add_argument(
            '--config',
            required=True,
            help='Archivo de configuración'
        )
        rollback_parser.add_argument(
            '--output',
            help='Archivo de salida'
        )

        # Comando: analyze
        analyze_parser = subparsers.add_parser(
            'analyze',
            help='Analizar procedures sin generar scripts'
        )
        analyze_parser.add_argument(
            '--config',
            required=True,
            help='Archivo de configuración'
        )
        analyze_parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Número de procedures a analizar'
        )
        analyze_parser.add_argument(
            '--output',
            help='Guardar análisis en JSON'
        )

        # Comando: validate
        validate_parser = subparsers.add_parser(
            'validate',
            help='Validar script de migración'
        )
        validate_parser.add_argument(
            '--original',
            required=True,
            help='Archivo con código original'
        )
        validate_parser.add_argument(
            '--migrated',
            required=True,
            help='Archivo con código migrado'
        )

        # Comando: info
        info_parser = subparsers.add_parser(
            'info',
            help='Mostrar información del sistema'
        )
        info_parser.add_argument(
            '--config',
            help='Archivo de configuración'
        )

        return parser

    def load_config(self, config_file: str) -> MigrationConfig:
        """Carga configuración desde YAML"""
        with open(config_file, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        # Expandir variables de entorno
        def expand_env(obj):
            if isinstance(obj, dict):
                return {k: expand_env(v) for k, v in obj.items()}
            elif isinstance(obj, str):
                return os.path.expandvars(obj)
            return obj

        config_dict = expand_env(config_dict)

        sybase_config = SybaseIQConfig(
            server=config_dict['sybase']['server'],
            database=config_dict['sybase']['database'],
            username=config_dict['sybase']['username'],
            password=config_dict['sybase']['password'],
            port=config_dict['sybase'].get('port', 5000),
            timeout=config_dict['sybase'].get('timeout', 30),
        )

        migration_config = MigrationConfig(
            source_mapping=config_dict['migration']['source_mapping'],
            sybase_config=sybase_config,
            migration_type=MigrationType(config_dict['migration']['type']),
            validate_before_execution=not config_dict['migration']['options'].get('skip_validation', False),
            backup_before_migration=not config_dict['migration']['options'].get('skip_backup', False),
            create_rollback_plan=config_dict['migration']['options'].get('create_rollback_plan', True),
            batch_size=config_dict['migration']['options'].get('batch_size', 10),
            output_dir=config_dict['migration']['output_directory']
        )

        return migration_config

    def cmd_migrate(self, args) -> int:
        """Ejecutar migración completa"""
        logger.info("🚀 Comando: migrate")

        try:
            config = self.load_config(args.config)

            if args.output:
                config.output_dir = args.output

            if args.skip_backup:
                config.backup_before_migration = False

            if args.skip_validation:
                config.validate_before_execution = False

            Path(config.output_dir).mkdir(parents=True, exist_ok=True)

            agent = SybaseIQMigrationAgent(config)

            if args.dry_run:
                logger.info("⚠️ DRY RUN - Sin cambios reales")

            # Obtener procedures según fase
            all_procs = agent.db.get_all_procedures()

            if args.phase == 'read':
                procs = {
                    n: c for n, c in all_procs.items()
                    if 'SELECT' in c.upper() and 'INSERT' not in c.upper()
                }
                logger.info(f"📖 Fase LECTURA: {len(procs)} procedures")

            elif args.phase == 'write':
                procs = {
                    n: c for n, c in all_procs.items()
                    if 'INSERT' in c.upper() or 'UPDATE' in c.upper()
                }
                logger.info(f"✏️ Fase ESCRITURA: {len(procs)} procedures")

            else:
                procs = all_procs
                logger.info(f"🔄 Fase COMPLETA: {len(procs)} procedures")

            if args.limit:
                procs = dict(list(procs.items())[:args.limit])
                logger.info(f"⚠️ Limitado a {args.limit} procedures")

            # Ejecutar pipeline
            agent.batch_analyze(procs)
            migration_script = agent.generate_migration_script()
            rollback_script = agent.generate_rollback_plan()
            report_file = agent.export_report()

            logger.info(f"\n✅ Migración completada")
            logger.info(f"   Procedures: {len(agent.analyses)}")
            logger.info(f"   Reporte: {report_file}")
            logger.info(f"   Output: {config.output_dir}/")

            return 0

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return 1

    def cmd_test_connection(self, args) -> int:
        """Probar conexión a SybaseIQ"""
        logger.info("🚀 Comando: test-connection")

        try:
            config = SybaseIQConfig(
                server=args.server,
                database=args.db,
                username=args.user,
                password=args.password,
                port=args.port
            )

            db = SybaseIQDatabase(config)
            procs = db.get_all_procedures()

            logger.info(f"✅ Conexión exitosa")
            logger.info(f"   Procedures encontrados: {len(procs)}")

            if procs:
                logger.info(f"   Primeros 5:")
                for name in list(procs.keys())[:5]:
                    logger.info(f"     - {name}")

            db.disconnect()
            return 0

        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            return 1

    def cmd_list_affected(self, args) -> int:
        """Listar procedures afectados"""
        logger.info("🚀 Comando: list-affected")

        try:
            config = self.load_config(args.config)
            db = SybaseIQDatabase(config.sybase_config)

            if args.source:
                affected = db.get_procedures_using_source(args.source)
                logger.info(f"Procedures usando {args.source}: {len(affected)}")
            else:
                # Mostrar todos los afectados
                affected = {}
                for old_source in config.source_mapping.keys():
                    affected.update(db.get_procedures_using_source(old_source))

                logger.info(f"Total procedures afectados: {len(affected)}")

            for name in sorted(affected.keys()):
                logger.info(f"  - {name}")

            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(list(affected.keys()), f, indent=2)
                logger.info(f"✅ Lista guardada en: {args.output}")

            db.disconnect()
            return 0

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return 1

    def cmd_analyze(self, args) -> int:
        """Analizar procedures"""
        logger.info("🚀 Comando: analyze")

        try:
            config = self.load_config(args.config)
            agent = SybaseIQMigrationAgent(config)

            procs = agent.db.get_all_procedures()
            procs = dict(list(procs.items())[:args.limit])

            logger.info(f"Analizando {len(procs)} procedures...")
            agent.batch_analyze(procs)

            logger.info(f"\n✅ Análisis completado")
            for analysis in agent.analyses:
                logger.info(f"\n{analysis.procedure_name}:")
                logger.info(f"  Fuentes: {analysis.found_old_sources}")
                logger.info(f"  Cambios: {len(analysis.changes_needed)}")
                if analysis.risks:
                    logger.info(f"  ⚠️ Riesgos: {analysis.risks}")

            if args.output:
                report_file = agent.export_report(args.output)
                logger.info(f"✅ Análisis guardado: {report_file}")

            return 0

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return 1

    def cmd_info(self, args) -> int:
        """Mostrar información del sistema"""
        logger.info("🚀 Información del Sistema")

        try:
            logger.info(f"\nPython: {sys.version}")
            logger.info(f"Plataforma: {sys.platform}")

            if args.config:
                config = self.load_config(args.config)
                logger.info(f"\n📋 Configuración de Migración:")
                logger.info(f"   Server: {config.sybase_config.server}")
                logger.info(f"   Database: {config.sybase_config.database}")
                logger.info(f"   Fuentes a migrar: {len(config.source_mapping)}")
                for old, new in config.source_mapping.items():
                    logger.info(f"     {old} -> {new}")

                db = SybaseIQDatabase(config.sybase_config)
                procs = db.get_all_procedures()
                logger.info(f"\n   Total procedures: {len(procs)}")
                db.disconnect()

            return 0

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return 1

    def run(self, argv: Optional[list] = None) -> int:
        """Ejecutar CLI"""
        parser = self.create_parser()

        if argv is None:
            argv = sys.argv[1:]

        if not argv:
            parser.print_help()
            return 0

        args = parser.parse_args(argv)

        if args.command == 'migrate':
            return self.cmd_migrate(args)
        elif args.command == 'test-connection':
            return self.cmd_test_connection(args)
        elif args.command == 'list-affected':
            return self.cmd_list_affected(args)
        elif args.command == 'analyze':
            return self.cmd_analyze(args)
        elif args.command == 'info':
            return self.cmd_info(args)
        else:
            parser.print_help()
            return 0


def main():
    """Entry point"""
    cli = MigrationCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
