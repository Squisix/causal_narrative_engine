"""
scripts/verify_fase2.py - Phase 2 prerequisite verification

Run before tests to verify that everything is ready.
"""

import asyncio
import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


async def verify_docker():
    """Verify that Docker is running."""
    print("\n[1/5] Verifying Docker...")
    try:
        proc = await asyncio.create_subprocess_exec(
            'docker', 'ps',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            print("  [OK] Docker is running")
            return True
        else:
            print("  [FAIL] Docker is not responding")
            print(f"  Error: {stderr.decode()}")
            return False
    except FileNotFoundError:
        print("  [FAIL] Docker is not installed or is not in the PATH")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


async def verify_docker_compose():
    """Verify that docker-compose services are running."""
    print("\n[2/5] Verifying Docker Compose services...")
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
                print("  [OK] PostgreSQL container is running")
                return True
            else:
                print("  [WARN] PostgreSQL container is not running")
                print("  Run: docker-compose up -d")
                return False
        else:
            print("  [WARN] Could not verify services")
            return False
    except FileNotFoundError:
        print("  [FAIL] docker-compose is not installed")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


async def verify_postgres_connection():
    """Verify connection to PostgreSQL."""
    print("\n[3/5] Verifying PostgreSQL connection...")
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
                print("  [OK] PostgreSQL connection successful")
                await config.dispose()
                return True
    except ImportError as e:
        print(f"  [FAIL] Could not import DatabaseConfig: {e}")
        print("  Verify that asyncpg is installed: pip install asyncpg")
        return False
    except Exception as e:
        print(f"  [FAIL] Could not connect to PostgreSQL")
        print(f"  Error: {e}")
        print("\n  Possible solutions:")
        print("  1. Verify that Docker is running")
        print("  2. Run: docker-compose up -d")
        print("  3. Wait a few seconds for PostgreSQL to start")
        return False


async def verify_tables():
    """Verify that tables have been created."""
    print("\n[4/5] Verifying PostgreSQL tables...")
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
                print(f"  [OK] All tables exist ({len(tables)} tables)")
                await config.dispose()
                return True
            else:
                print(f"  [WARN] Missing {len(missing_tables)} tables:")
                for table in missing_tables:
                    print(f"    - {table}")
                print("\n  Run: alembic upgrade head")
                await config.dispose()
                return False

    except Exception as e:
        print(f"  [FAIL] Could not verify tables")
        print(f"  Error: {e}")
        return False


async def verify_dependencies():
    """Verify that Python dependencies are installed."""
    print("\n[5/5] Verifying Python dependencies...")

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
            print(f"  [OK] {package_name} installed")
        except ImportError:
            print(f"  [FAIL] {package_name} NOT installed")
            print(f"    Run: pip install {package_name}")
            all_installed = False

    return all_installed


async def main():
    print("=" * 60)
    print("  PHASE 2 VERIFICATION - Causal Narrative Engine")
    print("=" * 60)

    results = []

    # Run all verifications
    results.append(await verify_docker())
    results.append(await verify_docker_compose())
    results.append(await verify_postgres_connection())
    results.append(await verify_tables())
    results.append(await verify_dependencies())

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nVerifications passed: {passed}/{total}")

    if all(results):
        print("\n[SUCCESS] All ready to run Phase 2 tests!")
        print("\nRun:")
        print("  pytest tests/test_fase2.py -v")
        return 0
    else:
        print("\n[WARNING] There are issues to resolve before running tests")
        print("\nSee FASE2_STEPS.md for more information")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
