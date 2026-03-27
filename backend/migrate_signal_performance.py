"""Add points_earned column to signals table"""
import sys
sys.path.insert(0, '/app')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE signals ADD COLUMN IF NOT EXISTS points_earned FLOAT"))
        conn.commit()
        print("points_earned column added")
    except Exception as e:
        print(f"Error: {e}")
