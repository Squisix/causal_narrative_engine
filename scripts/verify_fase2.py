"""
scripts/verify_fase2.py - Verificación de prerrequisitos para Fase 2

Ejecutar antes de los tests para verificar que todo está listo.
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


async def verify_docker():
    """Verifica que Docker esté corriendo."""
    print("\n[1/5] Verificando Docker...")
    try:
        proc = await asyncio.create_subprocess_exec(
            'docker', 'ps',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            print("  [OK] Docker está corriendo")
            return True
        else:
            print("  [FAIL] Docker no está respondiendo")
            print(f"  Error: {stderr.decode()}")
            return False
    except FileNotFoundError:
        print("  [FAIL] Docker no está instalado o no está en el PATH")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


async def verify_docker_compose():
    """Verifica que los servicios de docker-compose estén corriendo."""
    print("\n[2/5] Verificando servicios de Docker Compose...")
    try:
        proc = await asyncio.create_subprocess_exec(
            'docker-compose', 'ps', '--format', 'json',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            output = stdout.decode()
            if 'cne_postgres' in output:
                print("  [OK] PostgreSQL container está corriendo")
                return True
            else:
                print("  [WARN] PostgreSQL container no está corriendo")
                print("  Ejecuta: docker-compose up -d")
                return False
        else:
            print("  [WARN] No se pudieron verificar los servicios")
            return False
    except FileNotFoundError:
        print("  [FAIL] docker-compose no está instalado")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


async def verify_postgres_connection():
    """Verifica conexión a PostgreSQL."""
    print("\n[3/5] Verificando conexión a PostgreSQL...")
    try:
        from persistence.database import DatabaseConfig
        from sqlalchemy import text

        config = DatabaseConfig(
            "postgresql+asyncpg://cne_user@localhost:5433/cne_db",
            echo=False
        )

        async with config.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                print("  [OK] Conexión a PostgreSQL exitosa")
                await config.dispose()
                return True
    except ImportError as e:
        print(f"  [FAIL] No se pudo importar DatabaseConfig: {e}")
        print("  Verifica que asyncpg esté instalado: pip install asyncpg")
        return False
    except Exception as e:
        print(f"  [FAIL] No se pudo conectar a PostgreSQL")
        print(f"  Error: {e}")
        print("\n  Posibles soluciones:")
        print("  1. Verifica que Docker esté corriendo")
        print("  2. Ejecuta: docker-compose up -d")
        print("  3. Espera unos segundos a que PostgreSQL inicie")
        return False


async def verify_tables():
    """Verifica que las tablas estén creadas."""
    print("\n[4/5] Verificando tablas en PostgreSQL...")
    try:
        from persistence.database import DatabaseConfig
        from sqlalchemy import text

        config = DatabaseConfig(
            "postgresql+asyncpg://cne_user@localhost:5433/cne_db",
            echo=False
        )

        async with config.get_session() as session:
            result = await session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            expected_tables = [
                'worlds', 'entities', 'branches', 'commits',
                'events', 'event_edges', 'entity_deltas',
                'world_variable_deltas', 'dramatic_deltas', 'dramatic_states'
            ]

            missing_tables = [t for t in expected_tables if t not in tables]

            if not missing_tables:
                print(f"  [OK] Todas las tablas existen ({len(tables)} tablas)")
                await config.dispose()
                return True
            else:
                print(f"  [WARN] Faltan {len(missing_tables)} tablas:")
                for table in missing_tables:
                    print(f"    - {table}")
                print("\n  Ejecuta: alembic upgrade head")
                await config.dispose()
                return False

    except Exception as e:
        print(f"  [FAIL] No se pudieron verificar las tablas")
        print(f"  Error: {e}")
        return False


async def verify_dependencies():
    """Verifica que las dependencias de Python estén instaladas."""
    print("\n[5/5] Verificando dependencias de Python...")

    required_packages = [
        ('sqlalchemy', 'SQLAlchemy'),
        ('asyncpg', 'asyncpg'),
        ('alembic', 'Alembic'),
        ('pytest', 'pytest'),
    ]

    all_installed = True
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"  [OK] {package_name} instalado")
        except ImportError:
            print(f"  [FAIL] {package_name} NO instalado")
            print(f"    Ejecuta: pip install {package_name}")
            all_installed = False

    return all_installed


async def main():
    print("=" * 60)
    print("  VERIFICACION DE FASE 2 - Causal Narrative Engine")
    print("=" * 60)

    results = []

    # Ejecutar todas las verificaciones
    results.append(await verify_docker())
    results.append(await verify_docker_compose())
    results.append(await verify_postgres_connection())
    results.append(await verify_tables())
    results.append(await verify_dependencies())

    # Resumen
    print("\n" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nVerificaciones pasadas: {passed}/{total}")

    if all(results):
        print("\n[SUCCESS] Todo listo para ejecutar tests de Fase 2!")
        print("\nEjecuta:")
        print("  pytest tests/test_fase2.py -v")
        return 0
    else:
        print("\n[WARNING] Hay problemas que resolver antes de ejecutar tests")
        print("\nConsulta FASE2_STEPS.md para más información")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
