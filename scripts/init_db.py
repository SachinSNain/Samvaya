"""
scripts/init_db.py
Creates all database tables using SQLAlchemy models.
Run once on a fresh database before loading data.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.models import Base
from src.database.connection import engine

print("Creating all database tables...")
Base.metadata.create_all(engine)
print("Done! All tables created successfully.")
