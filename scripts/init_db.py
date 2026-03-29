"""
Initialize database: run Alembic migrations.
Usage: python scripts/init_db.py
"""
import subprocess
import sys
import os

def main():
    backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
    print("Running Alembic migrations...")
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
        cwd=backend_dir,
    )
    if result.returncode != 0:
        print("Migration failed!")
        sys.exit(1)
    print("Database initialized successfully.")

if __name__ == '__main__':
    main()
