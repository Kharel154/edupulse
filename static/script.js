/* ══════════════════════════════════════════
   EduPulse — Logique principale (Vanilla JS)
══════════════════════════════════════════ */

// ── État global des notes (étoiles) ──
const ratings = { difficulte: 0, interet: 0, charge: 0 };
const LABELS  = ["", "Très faible", "Faible", "Moyen", "Élevé", "Très élevé"];

// ── Instances Chart.js ──
let chartBarres      = null;
let chartFiliere     = null;
let chartNiveau      = null;

// ──────────────────────────────────────────
// INIT
// ──────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initStars();
    initCharCount();
});

// ──────────────────────────────────────────
// ONGLETS
// ──────────────────────────────────────────
function showTab(name, event) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
    document.getElementById(`tab-${name}`).classList.add("active");
    if (event && event.target) event.target.classList.add("active");
    if (name === "analyse") loadStats();
}

// ──────────────────────────────────────────
// ÉTOILES
// ──────────────────────────────────────────
function initStars() {
    ["difficulte", "interet", "charge"].forEach(field => {
        const container = document.getElementById(`stars-${field}`);
        for (let i = 1; i <= 5; i++) {
            const star = document.createElement("span");
            star.className   = "star";
            star.textContent = "★";
            star.dataset.value = i;
            star.addEventListener("click",      () => setRating(field, i));
            star.addEventListener("mouseenter", () => highlightStars(field, i));
            star.addEventListener("mouseleave", () => highlightStars(field, ratings[field]));
            container.appendChild(star);
        }
    });
}

function setRating(field, value) {
    ratings[field] = value;
    highlightStars(field, value);
    document.getElementById(`label-${field}`).textContent = LABELS[value];
}

function highlightStars(field, value) {
    document.querySelectorAll(`#stars-${field} .star`)
        .forEach((s, i) => s.classList.toggle("active", i < value));
}

// ──────────────────────────────────────────
// COMPTEUR DE CARACTÈRES
// ──────────────────────────────────────────
function initCharCount() {
    const textarea = document.getElementById("commentaire");
    const counter  = document.getElementById("char-num");
    textarea.addEventListener("input", () => { counter.textContent = textarea.value.length; });
}

// ──────────────────────────────────────────
// ALERTES
// ──────────────────────────────────────────
function showAlert(message, type = "success") {
    const el = document.getElementById("form-alert");
    el.textContent = message;
    el.className   = `alert ${type}`;
    el.classList.remove("hidden");
    setTimeout(() => el.classList.add("hidden"), 4000);
}

// ──────────────────────────────────────────
// SOUMISSION DU FORMULAIRE
// ──────────────────────────────────────────
async function submitForm() {
    const filiere     = document.getElementById("filiere").value.trim();
    const niveau      = document.getElementById("niveau").value.trim();
    const matiere     = document.getElementById("matiere").value.trim();
    const commentaire = document.getElementById("commentaire").value.trim();

    if (!filiere || !niveau || !matiere)
        return showAlert("⚠️ Veuillez remplir tous les champs obligatoires.", "error");
    if (ratings.difficulte === 0 || ratings.interet === 0 || ratings.charge === 0)
        return showAlert("⚠️ Veuillez noter les trois critères.", "error");

    const payload = { filiere, niveau, matiere,
        difficulte:  ratings.difficulte,
        interet:     ratings.interet,
        charge:      ratings.charge,
        commentaire: commentaire || null
    };

    const btn = document.getElementById("btn-submit");
    btn.disabled    = true;
    btn.textContent = "Envoi en cours…";

    try {
        const response = await fetch("/api/responses", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Erreur inconnue");
        }
        showAlert("✅ Votre évaluation a bien été enregistrée. Merci !");
        resetForm();
    } catch (err) {
        showAlert(`❌ Erreur : ${err.message}`, "error");
    } finally {
        btn.disabled    = false;
        btn.textContent = "Envoyer mon évaluation 🚀";
    }
}

// ──────────────────────────────────────────
// RÉINITIALISATION DU FORMULAIRE
// ──────────────────────────────────────────
function resetForm() {
    ["filiere", "niveau", "matiere", "commentaire"].forEach(id => {
        document.getElementById(id).value = "";
    });
    document.getElementById("char-num").textContent = "0";
    ["difficulte", "interet", "charge"].forEach(field => {
        ratings[field] = 0;
        highlightStars(field, 0);
        document.getElementById(`label-${field}`).textContent = "—";
    });
}

// ──────────────────────────────────────────
// CHARGEMENT DES STATISTIQUES (centralisé)
// ──────────────────────────────────────────
async function loadStats() {
    try {
        const [resStats, resTop, resComments, resFilieres] = await Promise.all([
            fetch("/api/stats"),
            fetch("/api/stats/top-matieres"),
            fetch("/api/stats/commentaires"),
            fetch("/api/stats/top-filieres-difficiles")
        ]);

        const stats    = await resStats.json();
        const top      = await resTop.json();
        const comments = await resComments.json();
        const filieres = await resFilieres.json();

        // ── KPIs ──
        if (!stats.total || stats.total === 0) {
            document.getElementById("kpi-total").textContent = "0";
            ["kpi-diff", "kpi-int", "kpi-charge"].forEach(id => {
                document.getElementById(id).textContent = "—";
            });
            return;
        }
        document.getElementById("kpi-total").textContent  = stats.total;
        document.getElementById("kpi-diff").textContent   = stats.difficulte.moyenne;
        document.getElementById("kpi-int").textContent    = stats.interet.moyenne;
        document.getElementById("kpi-charge").textContent = stats.charge.moyenne;

        // ── Graphiques ──
        renderBarChart(stats);
        renderFiliereChart(stats);
        renderNiveauChart(stats);
        renderStatsTable(stats);
        renderTopMatieres(top);
        renderTopFilieresDifficiles(filieres);
        renderCommentaires(comments);

    } catch (err) {
        console.error("Erreur chargement stats :", err);
    }
}

// ──────────────────────────────────────────
// GRAPHIQUE 1 — Barres moyennes par critère
// ──────────────────────────────────────────
function renderBarChart(data) {
    if (chartBarres) chartBarres.destroy();
    chartBarres = new Chart(document.getElementById("chartBarres"), {
        type: "bar",
        data: {
            labels: ["Difficulté", "Intérêt", "Charge"],
            datasets: [{
                label: "Moyenne /5",
                data: [data.difficulte.moyenne, data.interet.moyenne, data.charge.moyenne],
                backgroundColor: ["#6366f1", "#06b6d4", "#f59e0b"],
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { min: 0, max: 5, ticks: { stepSize: 1 } } }
        }
    });
}

// ──────────────────────────────────────────
// GRAPHIQUE 2 — Doughnut répartition filières
// ──────────────────────────────────────────
function renderFiliereChart(data) {
    if (chartFiliere) chartFiliere.destroy();
    const labels = Object.keys(data.par_filiere);
    const values = Object.values(data.par_filiere);
    const colors = ["#6366f1","#06b6d4","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#14b8a6"];

    chartFiliere = new Chart(document.getElementById("chartFiliere"), {
        type: "doughnut",
        data: {
            labels,
            datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length), borderWidth: 2 }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: "bottom", labels: { font: { size: 11 } } } }
        }
    });
}

// ──────────────────────────────────────────
// GRAPHIQUE 3 — Barres horizontales niveaux
// ──────────────────────────────────────────
function renderNiveauChart(data) {
    if (chartNiveau) chartNiveau.destroy();
    const labels = Object.keys(data.par_niveau);
    const values = Object.values(data.par_niveau);

    chartNiveau = new Chart(document.getElementById("chartNiveau"), {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Réponses",
                data: values,
                backgroundColor: "#10b981",
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { x: { ticks: { stepSize: 1 } } }
        }
    });
}

// ──────────────────────────────────────────
// GRAPHIQUE 4 — Tableau stats descriptives
// ──────────────────────────────────────────
function renderStatsTable(data) {
    const criteres = [
        { key: "difficulte", label: "Difficulté" },
        { key: "interet",    label: "Intérêt"    },
        { key: "charge",     label: "Charge"     }
    ];
    let html = `
        <table>
            <thead>
                <tr>
                    <th>Critère</th><th>Moy.</th><th>Méd.</th>
                    <th>σ</th><th>Min</th><th>Max</th>
                </tr>
            </thead><tbody>`;
    criteres.forEach(({ key, label }) => {
        const s = data[key];
        html += `<tr>
            <td><strong>${label}</strong></td>
            <td>${s.moyenne}</td><td>${s.mediane}</td>
            <td>${s.ecart_type}</td><td>${s.min}</td><td>${s.max}</td>
        </tr>`;
    });
    html += "</tbody></table>";
    document.getElementById("stats-table").innerHTML = html;
}

// ──────────────────────────────────────────
// GRAPHIQUE 5 — Évolution réponses + moyennes
// ──────────────────────────────────────────
function renderEvolutionChart(data) {
    if (chartEvolution) chartEvolution.destroy();
    if (!data.length) return;

    chartEvolution = new Chart(document.getElementById("chartEvolution"), {
        type: "line",
        data: {
            labels: data.map(d => d.jour),
            datasets: [
                {
                    label: "Réponses",
                    data: data.map(d => d.total),
                    borderColor: "#4f46e5",
                    backgroundColor: "rgba(79,70,229,0.1)",
                    fill: true, tension: 0.4, yAxisID: "y"
                },
                {
                    label: "Moy. Difficulté",
                    data: data.map(d => d.moy_diff),
                    borderColor: "#ef4444",
                    borderDash: [5,5], tension: 0.4, yAxisID: "y2"
                },
                {
                    label: "Moy. Intérêt",
                    data: data.map(d => d.moy_int),
                    borderColor: "#06b6d4",
                    borderDash: [5,5], tension: 0.4, yAxisID: "y2"
                }
            ]
        },
        options: {
            responsive: true,
            interaction: { mode: "index", intersect: false },
            plugins: { legend: { position: "top" } },
            scales: {
                y:  { type: "linear", position: "left",
                      title: { display: true, text: "Nb réponses" }, ticks: { stepSize: 1 } },
                y2: { type: "linear", position: "right", min: 0, max: 5,
                      title: { display: true, text: "Note /5" }, grid: { drawOnChartArea: false } }
            }
        }
    });
}

// ──────────────────────────────────────────
// GRAPHIQUE 6 — Évolution des commentaires
// ──────────────────────────────────────────
function renderCommentairesChart(data) {
    if (chartCommentaires) chartCommentaires.destroy();

    // On filtre les jours où il y a eu des commentaires (moy_charge sert de proxy)
    // En réalité on utilise les données d'évolution pour montrer les soumissions par jour
    if (!data.length) return;

    chartCommentaires = new Chart(document.getElementById("chartCommentaires"), {
        type: "bar",
        data: {
            labels: data.map(d => d.jour),
            datasets: [
                {
                    label: "Réponses soumises",
                    data: data.map(d => d.total),
                    backgroundColor: "rgba(99,102,241,0.7)",
                    borderColor: "#4f46e5",
                    borderWidth: 2,
                    borderRadius: 6,
                    type: "bar"
                },
                {
                    label: "Moy. Charge",
                    data: data.map(d => d.moy_charge),
                    borderColor: "#f59e0b",
                    backgroundColor: "transparent",
                    borderDash: [4,4],
                    tension: 0.4,
                    type: "line",
                    yAxisID: "y2"
                }
            ]
        },
        options: {
            responsive: true,
            interaction: { mode: "index", intersect: false },
            plugins: { legend: { position: "top" } },
            scales: {
                y:  { ticks: { stepSize: 1 }, title: { display: true, text: "Nb réponses" } },
                y2: { position: "right", min: 0, max: 5,
                      title: { display: true, text: "Charge /5" },
                      grid: { drawOnChartArea: false } }
            }
        }
    });
}

// ──────────────────────────────────────────
// TOP 3 MATIÈRES — avec filière affichée
// ──────────────────────────────────────────
function renderTopMatieres(data) {
    const container = document.getElementById("top-matieres");
    if (!data.length) {
        container.innerHTML = "<p style='color:var(--text-muted);font-size:.9rem'>Pas encore de données.</p>";
        return;
    }
    const medals  = ["gold", "silver", "bronze"];
    const trophees = ["🥇", "🥈", "🥉"];

    container.innerHTML = data.map((m, i) => `
        <div class="top-matiere-item">
            <div class="top-rank ${medals[i]}">${trophees[i]}</div>
            <div class="top-info">
                <div class="top-matiere-name">${m.matiere}</div>
                <div class="top-meta">
                    🎓 <strong>${m.filiere}</strong> &nbsp;·&nbsp;
                    Intérêt : ${m.moy_interet}/5 &nbsp;·&nbsp;
                    Charge : ${m.moy_charge}/5 &nbsp;·&nbsp;
                    ${m.total} rép.
                </div>
            </div>
            <div class="top-badge">⚡ ${m.moy_difficulte}/5</div>
        </div>
    `).join("");
}

// ──────────────────────────────────────────
// CLASSEMENT FILIÈRES PAR MATIÈRES DIFFICILES
// ──────────────────────────────────────────
function renderTopFilieresDifficiles(data) {
    const container = document.getElementById("top-filieres-difficiles");
    if (!data.length) {
        container.innerHTML = "<p style='color:var(--text-muted);font-size:.9rem'>Pas encore de données.</p>";
        return;
    }
    const maxDifficiles = Math.max(...data.map(f => f.nb_matieres_difficiles)) || 1;
    const couleurs = ["#ef4444","#f59e0b","#10b981","#06b6d4","#8b5cf6","#94a3b8"];

    container.innerHTML = data.map((f, i) => {
        const pct     = Math.round((f.nb_matieres_difficiles / maxDifficiles) * 100);
        const couleur = couleurs[i] || "#94a3b8";
        return `
        <div class="filiere-rank-item">
            <div class="filiere-rank-num" style="color:${couleur}">#${i+1}</div>
            <div class="filiere-rank-info">
                <div class="filiere-rank-name">${f.filiere}</div>
                <div class="filiere-rank-meta">
                    📚 ${f.nb_matieres_difficiles} matière(s) difficile(s)
                    sur ${f.nb_matieres_total} &nbsp;·&nbsp;
                    Diff. globale : <strong>${f.diff_moyenne_filiere}/5</strong>
                </div>
                <div class="filiere-bar-wrap">
                    <div class="filiere-bar-fill"
                         style="width:${pct}%; background:${couleur}"></div>
                </div>
            </div>
            <div class="filiere-diff-badge"
                 style="background:${couleur}22; color:${couleur}">
                🔥 ${f.nb_matieres_difficiles}/${f.nb_matieres_total}
            </div>
        </div>`;
    }).join("");
}

// ──────────────────────────────────────────
// DERNIERS COMMENTAIRES
// ──────────────────────────────────────────
function renderCommentaires(data) {
    const container = document.getElementById("commentaires-list");
    if (!data.length) {
        container.innerHTML = "<p style='color:var(--text-muted);font-size:.9rem'>Aucun commentaire pour l'instant.</p>";
        return;
    }
    container.innerHTML = data.map(c => `
        <div class="comment-item">
            <div class="comment-text">"${c.commentaire}"</div>
            <div class="comment-meta">
                📚 ${c.matiere} &nbsp;·&nbsp;
                🎓 ${c.filiere} — ${c.niveau} &nbsp;·&nbsp;
                🕐 ${(c.created_at || "").split("T")[0] || c.created_at}
            </div>
        </div>
    `).join("");
}