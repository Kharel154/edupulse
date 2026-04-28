# database.py — Connexion SQLite corrigée

import aiosqlite
import os

DATA_DIR = "/data" if os.path.exists("/data") else os.path.dirname(__file__)
DB_PATH = os.path.join(DATA_DIR, "edupulse.db")

async def init_db():
    """Crée la table si elle n'existe pas."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filiere     TEXT    NOT NULL,
                niveau      TEXT    NOT NULL,
                matiere     TEXT    NOT NULL,
                difficulte  INTEGER NOT NULL,
                interet     INTEGER NOT NULL,
                charge      INTEGER NOT NULL,
                commentaire TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
