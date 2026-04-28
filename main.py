# main.py — EduPulse FastAPI (version corrigée)

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import aiosqlite
import statistics
import os

from database import init_db, DB_PATH
from models import ReponseCreate

# ── Initialisation ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="EduPulse API",
    description="Collecte et analyse descriptive des données éducatives",
    version="1.0.0",
    lifespan=lifespan
)

# ── Fichiers statiques ──
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# ── POST — Enregistrer une réponse ──
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
                data.commentaire
            ))
            await db.commit()
        return {"message": "Réponse enregistrée avec succès ✅"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'enregistrement : {str(e)}"
        )

# ── GET — Toutes les réponses ──
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
            detail=f"Erreur récupération : {str(e)}"
        )

# ── GET — Statistiques descriptives ──
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

        difficultes = [r["difficulte"] for r in data]
        interets    = [r["interet"]    for r in data]
        charges     = [r["charge"]     for r in data]

        def describe(values):
            return {
                "moyenne":    round(statistics.mean(values), 2),
                "mediane":    round(statistics.median(values), 2),
                "ecart_type": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
                "min":        min(values),
                "max":        max(values),
                "total":      len(values)
            }

        filieres = {}
        for r in data:
            filieres[r["filiere"]] = filieres.get(r["filiere"], 0) + 1

        niveaux = {}
        for r in data:
            niveaux[r["niveau"]] = niveaux.get(r["niveau"], 0) + 1

        return {
            "total":       len(data),
            "difficulte":  describe(difficultes),
            "interet":     describe(interets),
            "charge":      describe(charges),
            "par_filiere": filieres,
            "par_niveau":  niveaux
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur stats : {str(e)}"
        )

# ── GET — Top 3 matières les plus difficiles (avec filière) ──
@app.get("/api/stats/top-matieres")
async def get_top_matieres():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT matiere,
                       filiere,
                       ROUND(AVG(difficulte), 2) as moy_difficulte,
                       ROUND(AVG(interet), 2)    as moy_interet,
                       ROUND(AVG(charge), 2)     as moy_charge,
                       COUNT(*)                  as total
                FROM responses
                GROUP BY matiere, filiere
                ORDER BY moy_difficulte DESC
                LIMIT 3
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET — Classement des filières par nombre de matières difficiles ──
@app.get("/api/stats/top-filieres-difficiles")
async def get_top_filieres_difficiles():
    """
    Une matière est considérée 'difficile' si sa moyenne de difficulté >= 3.5
    On compte combien de matières difficiles chaque filière possède,
    et on calcule aussi la difficulté moyenne globale de la filière.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT
                    filiere,
                    COUNT(DISTINCT CASE WHEN moy_diff >= 3.5 THEN matiere END) as nb_matieres_difficiles,
                    COUNT(DISTINCT matiere)                                     as nb_matieres_total,
                    ROUND(AVG(moy_diff), 2)                                     as diff_moyenne_filiere
                FROM (
                    SELECT
                        filiere,
                        matiere,
                        AVG(difficulte) as moy_diff
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

# ── GET — Derniers commentaires ──
@app.get("/api/stats/commentaires")
async def get_commentaires():
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


# ── GET — Évolution des réponses dans le temps ──
@app.get("/api/stats/evolution")
async def get_evolution():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT DATE(created_at)          as jour,
                       COUNT(*)                  as total,
                       ROUND(AVG(difficulte), 2) as moy_diff,
                       ROUND(AVG(interet), 2)    as moy_int,
                       ROUND(AVG(charge), 2)     as moy_charge
                FROM responses
                GROUP BY DATE(created_at)
                ORDER BY jour ASC
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
