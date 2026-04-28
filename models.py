# models.py — Schémas Pydantic pour la validation stricte des données

from pydantic import BaseModel, Field, field_validator
from typing import Optional

# Liste des filières valides
FILIERES_VALIDES = [
    "Informatique", "Mathématiques", "Physique",
    "Chimie", "Biologie", "Économie", "Lettres", "Autre"
]

# Liste des niveaux valides
NIVEAUX_VALIDES = ["Licence 1", "Licence 2", "Licence 3", "Master 1", "Master 2"]

class ReponseCreate(BaseModel):
    """Schéma de validation pour la création d'une réponse."""

    filiere: str = Field(..., min_length=2, max_length=50,
                         description="Filière de l'étudiant")
    niveau: str = Field(..., description="Niveau académique")
    matiere: str = Field(..., min_length=2, max_length=100,
                         description="Matière évaluée")
    difficulte: int = Field(..., ge=1, le=5,
                            description="Note de difficulté (1 à 5)")
    interet: int = Field(..., ge=1, le=5,
                         description="Note d'intérêt (1 à 5)")
    charge: int = Field(..., ge=1, le=5,
                        description="Note de charge de travail (1 à 5)")
    commentaire: Optional[str] = Field(None, max_length=500,
                                       description="Commentaire libre")

    @field_validator("filiere")
    @classmethod
    def valider_filiere(cls, v):
        if v not in FILIERES_VALIDES:
            raise ValueError(f"Filière invalide. Choisissez parmi : {FILIERES_VALIDES}")
        return v

    @field_validator("niveau")
    @classmethod
    def valider_niveau(cls, v):
        if v not in NIVEAUX_VALIDES:
            raise ValueError(f"Niveau invalide. Choisissez parmi : {NIVEAUX_VALIDES}")
        return v

class ReponseRead(ReponseCreate):
    """Schéma de lecture (inclut les champs auto-générés)."""
    id: int
    created_at: str

    class Config:
        from_attributes = True