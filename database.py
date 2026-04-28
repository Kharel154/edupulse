# database.py — Connexion SQLite corrigée

import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "edupulse.db")

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
