# main.py — EduPulse FastAPI

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import aiosqlite
import statistics
import os
import httpx
import asyncio

from database import init_db, DB_PATH
from models import ReponseCreate


# ── Configuration ───────────────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")


# ── Keep-alive (évite l'endormissement sur Render) ──────────────────────────────

async def keep_alive():
    """Ping l'app toutes les 5 min pour éviter l'endormissement sur Render."""
    await asyncio.sleep(60)  # attendre 1 min au démarrage avant le 1er ping
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{RENDER_URL}/health", timeout=10)
            print(f"✅ Keep-alive ping — status {resp.status_code}")
        except Exception as e:
            print(f"⚠️  Keep-alive échoué : {e}")
        await asyncio.sleep(300)  # toutes les 5 minutes

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")

async def keep_alive():
    await asyncio.sleep(60)
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{RENDER_URL}/health", timeout=10)
            print(f"✅ Keep-alive — {resp.status_code}")
        except Exception as e:
            print(f"⚠️ Keep-alive échoué : {e}")
        await asyncio.sleep(300)

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}

# ── Lifespan ────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(keep_alive())
    yield
    task.cancel()


# ── Application ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="EduPulse API",
    description="Collecte et analyse descriptive des données éducatives",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Routes — Général ────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}


# ── Routes — Réponses ───────────────────────────────────────────────────────────

@app.post("/api/responses", status_code=status.HTTP_201_CREATED)
async def create_response(data: ReponseCreate):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO responses
                    (filiere, niveau, matiere, difficulte, interet, charge, commentaire)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.filiere,
                data.niveau,
                data.matiere,
                data.difficulte,
                data.interet,
                data.charge,
                data.commentaire,
            ))
            await db.commit()
        return {"message": "Réponse enregistrée avec succès ✅"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'enregistrement : {str(e)}",
        )


@app.get("/api/responses")
async def get_responses():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM responses ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération : {str(e)}",
        )


# ── Routes — Statistiques ───────────────────────────────────────────────────────

def describe(values: list[float]) -> dict:
    """Retourne les statistiques descriptives d'une liste de valeurs."""
    return {
        "moyenne":    round(statistics.mean(values), 2),
        "mediane":    round(statistics.median(values), 2),
        "ecart_type": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        "min":        min(values),
        "max":        max(values),
        "total":      len(values),
    }


@app.get("/api/stats")
async def get_stats():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM responses")
            rows = await cursor.fetchall()
            data = [dict(row) for row in rows]

        if not data:
            return {"message": "Aucune donnée disponible", "total": 0}

        filieres: dict[str, int] = {}
        niveaux:  dict[str, int] = {}
        for r in data:
            filieres[r["filiere"]] = filieres.get(r["filiere"], 0) + 1
            niveaux[r["niveau"]]   = niveaux.get(r["niveau"], 0) + 1

        return {
            "total":       len(data),
            "difficulte":  describe([r["difficulte"] for r in data]),
            "interet":     describe([r["interet"]    for r in data]),
            "charge":      describe([r["charge"]     for r in data]),
            "par_filiere": filieres,
            "par_niveau":  niveaux,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur stats : {str(e)}")


@app.get("/api/stats/top-matieres")
async def get_top_matieres():
    """Top 3 matières les plus difficiles (avec filière)."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT matiere,
                       filiere,
                       ROUND(AVG(difficulte), 2) AS moy_difficulte,
                       ROUND(AVG(interet), 2)    AS moy_interet,
                       ROUND(AVG(charge), 2)     AS moy_charge,
                       COUNT(*)                  AS total
                FROM responses
                GROUP BY matiere, filiere
                ORDER BY moy_difficulte DESC
                LIMIT 3
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/top-filieres-difficiles")
async def get_top_filieres_difficiles():
    """
    Classement des filières par nombre de matières difficiles.
    Une matière est considérée difficile si sa moyenne de difficulté >= 3.5.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT
                    filiere,
                    COUNT(DISTINCT CASE WHEN moy_diff >= 3.5 THEN matiere END) AS nb_matieres_difficiles,
                    COUNT(DISTINCT matiere)                                     AS nb_matieres_total,
                    ROUND(AVG(moy_diff), 2)                                     AS diff_moyenne_filiere
                FROM (
                    SELECT filiere,
                           matiere,
                           AVG(difficulte) AS moy_diff
                    FROM responses
                    GROUP BY filiere, matiere
                ) sub
                GROUP BY filiere
                ORDER BY nb_matieres_difficiles DESC, diff_moyenne_filiere DESC
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/commentaires")
async def get_commentaires():
    """Derniers commentaires non vides (5 max)."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT matiere, filiere, niveau, commentaire, created_at
                FROM responses
                WHERE commentaire IS NOT NULL AND TRIM(commentaire) != ''
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/evolution")
async def get_evolution():
    """Évolution des réponses dans le temps (agrégées par jour)."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT DATE(created_at)          AS jour,
                       COUNT(*)                  AS total,
                       ROUND(AVG(difficulte), 2) AS moy_diff,
                       ROUND(AVG(interet), 2)    AS moy_int,
                       ROUND(AVG(charge), 2)     AS moy_charge
                FROM responses
                GROUP BY DATE(created_at)
                ORDER BY jour ASC
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
