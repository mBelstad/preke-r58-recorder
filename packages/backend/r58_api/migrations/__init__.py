"""
Database migration runner for R58.

Migrations are Python files in the migrations directory with a `migrate()` function.
They are run in alphabetical order and tracked in a _migrations table.
"""
import sqlite3
import importlib.util
import logging
from pathlib import Path
from datetime import datetime
from typing import Set, List, Optional

logger = logging.getLogger(__name__)

MIGRATIONS_TABLE = "_migrations"


def get_applied_migrations(db_path: Path) -> Set[str]:
    """
    Get set of already-applied migration names.
    
    Creates the migrations tracking table if it doesn't exist.
    """
    conn = sqlite3.connect(db_path)
    try:
        # Try to get applied migrations
        cursor = conn.execute(f"SELECT name FROM {MIGRATIONS_TABLE}")
        return {row[0] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        # Table doesn't exist, create it
        conn.execute(f"""
            CREATE TABLE {MIGRATIONS_TABLE} (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL,
                checksum TEXT
            )
        """)
        conn.commit()
        return set()
    finally:
        conn.close()


def get_pending_migrations(db_path: Path, migrations_dir: Path) -> List[str]:
    """
    Get list of pending migration names in order.
    """
    applied = get_applied_migrations(db_path)
    
    pending = []
    for migration_file in sorted(migrations_dir.glob("*.py")):
        name = migration_file.stem
        # Skip __init__ and private files
        if name.startswith("_"):
            continue
        if name not in applied:
            pending.append(name)
    
    return pending


def run_migration(db_path: Path, migrations_dir: Path, name: str) -> bool:
    """
    Run a single migration.
    
    Args:
        db_path: Path to SQLite database
        migrations_dir: Directory containing migration files
        name: Migration name (without .py extension)
    
    Returns:
        True if successful, False otherwise
    """
    migration_file = migrations_dir / f"{name}.py"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    logger.info(f"Running migration: {name}")
    
    try:
        # Load the migration module
        spec = importlib.util.spec_from_file_location(name, migration_file)
        if spec is None or spec.loader is None:
            logger.error(f"Failed to load migration spec: {name}")
            return False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check for migrate function
        if not hasattr(module, "migrate"):
            logger.error(f"Migration {name} has no migrate() function")
            return False
        
        # Run the migration
        module.migrate(db_path)
        
        # Record as applied
        conn = sqlite3.connect(db_path)
        conn.execute(
            f"INSERT INTO {MIGRATIONS_TABLE} (name, applied_at) VALUES (?, ?)",
            (name, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        
        logger.info(f"Migration {name} completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration {name} failed: {e}")
        raise


def run_pending_migrations(db_path: Path, migrations_dir: Path) -> List[str]:
    """
    Run all pending migrations.
    
    Args:
        db_path: Path to SQLite database
        migrations_dir: Directory containing migration files
    
    Returns:
        List of migration names that were run
    """
    # Ensure db directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    pending = get_pending_migrations(db_path, migrations_dir)
    
    if not pending:
        logger.info("No pending migrations")
        return []
    
    logger.info(f"Found {len(pending)} pending migrations")
    
    applied = []
    for name in pending:
        if run_migration(db_path, migrations_dir, name):
            applied.append(name)
        else:
            # Stop on first failure
            break
    
    return applied


def rollback_migration(db_path: Path, migrations_dir: Path, name: str) -> bool:
    """
    Rollback a single migration if it has a rollback() function.
    
    Args:
        db_path: Path to SQLite database
        migrations_dir: Directory containing migration files
        name: Migration name (without .py extension)
    
    Returns:
        True if successful, False otherwise
    """
    migration_file = migrations_dir / f"{name}.py"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    logger.info(f"Rolling back migration: {name}")
    
    try:
        # Load the migration module
        spec = importlib.util.spec_from_file_location(name, migration_file)
        if spec is None or spec.loader is None:
            return False
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check for rollback function
        if not hasattr(module, "rollback"):
            logger.warning(f"Migration {name} has no rollback() function")
            return False
        
        # Run the rollback
        module.rollback(db_path)
        
        # Remove from applied
        conn = sqlite3.connect(db_path)
        conn.execute(f"DELETE FROM {MIGRATIONS_TABLE} WHERE name = ?", (name,))
        conn.commit()
        conn.close()
        
        logger.info(f"Rollback of {name} completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Rollback of {name} failed: {e}")
        raise


# Example migration template
MIGRATION_TEMPLATE = '''"""
Migration: {name}

Description: Add description here
"""
import sqlite3
from pathlib import Path


def migrate(db_path: Path):
    """Apply the migration"""
    conn = sqlite3.connect(db_path)
    try:
        # Add your migration SQL here
        conn.execute("""
            -- Example: CREATE TABLE new_table (id INTEGER PRIMARY KEY, name TEXT)
        """)
        conn.commit()
    finally:
        conn.close()


def rollback(db_path: Path):
    """Rollback the migration (optional)"""
    conn = sqlite3.connect(db_path)
    try:
        # Add your rollback SQL here
        conn.execute("""
            -- Example: DROP TABLE IF EXISTS new_table
        """)
        conn.commit()
    finally:
        conn.close()
'''


def create_migration(migrations_dir: Path, name: str, description: str = "") -> Path:
    """
    Create a new migration file from template.
    
    Args:
        migrations_dir: Directory for migration files
        name: Migration name (will be prefixed with number)
        description: Optional description
    
    Returns:
        Path to created migration file
    """
    migrations_dir.mkdir(parents=True, exist_ok=True)
    
    # Find next migration number
    existing = sorted(migrations_dir.glob("*.py"))
    existing = [f for f in existing if not f.name.startswith("_")]
    
    if existing:
        last_num = int(existing[-1].stem.split("_")[0])
        next_num = last_num + 1
    else:
        next_num = 1
    
    # Create filename
    filename = f"{next_num:03d}_{name}.py"
    filepath = migrations_dir / filename
    
    # Write template
    content = MIGRATION_TEMPLATE.format(name=f"{next_num:03d}_{name}")
    filepath.write_text(content)
    
    logger.info(f"Created migration: {filepath}")
    return filepath

