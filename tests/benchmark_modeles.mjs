// Comparaison de modèles locaux pour l'extension « IA locale pour Calc ».
// Mesure, pour chaque modèle : bonnes réponses sur 20 demandes, temps moyen, mémoire occupée.
// Usage :  node benchmark_modeles.mjs                      (liste par défaut ci-dessous)
//          node benchmark_modeles.mjs qwen2.5:3b gemma3:4b  (modèles au choix)
// Les modèles absents sont signalés et ignorés. Tout reste sur ce PC (localhost).

import { writeFileSync } from "node:fs";

const BASE = "http://localhost:11434";
const PAR_DEFAUT = ["qwen2.5:1.5b", "qwen2.5:3b", "qwen3:1.7b", "qwen3:4b", "gemma3:1b", "gemma3:4b",
  "llama3.2:3b", "phi4-mini", "granite3.3:2b"];
const MODELES = process.argv.slice(2).length ? process.argv.slice(2) : PAR_DEFAUT;
const COLONNES = ["Nom", "Prénom", "Email", "Téléphone", "Ville", "Code postal", "Entreprise", "Secteur", "Date 1er contact", "Montant devis (€)"];

// Même consigne et même schéma que l'extension (extension/pythonpath/calc_ia/llm.py)
const ACTIONS = ["normaliser_texte", "formater_telephone", "supprimer_doublons", "tableau_croise", "graphique", "trier", "aucune"];
const SCHEMA = {
  type: "object",
  properties: {
    action: { type: "string", enum: ACTIONS },
    colonne: { type: "string", enum: [...COLONNES, ""] },
    casse: { type: "string", enum: ["nom_propre", "majuscules", "minuscules", ""] },
    colonne_valeurs: { type: "string", enum: [...COLONNES, ""] },
    operation: { type: "string", enum: ["somme", "moyenne", "nombre", ""] },
    type_graphique: { type: "string", enum: ["barres", "courbe", "camembert", ""] },
    ordre: { type: "string", enum: ["croissant", "decroissant", ""] }
  },
  required: ["action", "colonne", "casse", "colonne_valeurs", "operation", "type_graphique", "ordre"]
};
const SYSTEME =
  "Tu traduis une demande d'utilisateur de tableur en UNE action parmi une liste fermée. Tu ne modifies rien toi-même.\n" +
  "Colonnes du tableau : " + COLONNES.join(", ") + ".\n" +
  "Actions possibles :\n" +
  "- normaliser_texte : nettoyer une colonne de texte (espaces superflus, casse). Champs : colonne, casse. casse = majuscules pour TOUT en majuscules (DUPONT), nom_propre pour seulement la première lettre de chaque mot (Dupont), minuscules pour tout en minuscules, vide pour ne changer que les espaces.\n" +
  "- formater_telephone : mettre une colonne de numéros de téléphone au format 06 12 34 56 78. Champ : colonne.\n" +
  "- supprimer_doublons : supprimer les lignes en double selon une colonne. Champ : colonne.\n" +
  "- tableau_croise : regrouper par une colonne et calculer sur une autre. Champs : colonne (regroupement), colonne_valeurs, operation (somme, moyenne, ou nombre pour compter des lignes).\n" +
  "- graphique : graphique d'une colonne de valeurs par catégorie. Champs : colonne (catégories), colonne_valeurs, type_graphique, operation.\n" +
  "- trier : trier le tableau. Champs : colonne, ordre. decroissant = du plus grand au plus petit, de Z à A, du plus récent au plus ancien. croissant = l'inverse.\n" +
  "- aucune : la demande ne porte pas sur une de ces actions (envoyer un mail, traduire, rédiger, calculer autre chose, etc.).\n" +
  "Laisse vide (\"\") tout champ inutile pour l'action choisie.";

const CAS = [
  ["Uniformise la colonne Ville avec une majuscule au début et sans espaces", { action: "normaliser_texte", colonne: "Ville", casse: "nom_propre" }],
  ["les villes sont écrites n'importe comment, corrige", { action: "normaliser_texte", colonne: "Ville" }],
  ["mets tous les noms en majuscules", { action: "normaliser_texte", colonne: "Nom", casse: "majuscules" }],
  ["passe les emails en minuscules", { action: "normaliser_texte", colonne: "Email", casse: "minuscules" }],
  ["Mets les téléphones au format 06 12 34 56 78", { action: "formater_telephone", colonne: "Téléphone" }],
  ["les numéros de tel sont pas tous pareils, harmonise", { action: "formater_telephone", colonne: "Téléphone" }],
  ["Supprime les doublons en te basant sur l'email", { action: "supprimer_doublons", colonne: "Email" }],
  ["il y a des contacts en double, enlève-les (même adresse mail = même personne)", { action: "supprimer_doublons", colonne: "Email" }],
  ["retire les doublons de téléphone", { action: "supprimer_doublons", colonne: "Téléphone" }],
  ["Crée un tableau croisé dynamique avec le total des devis par ville", { action: "tableau_croise", colonne: "Ville", colonne_valeurs: "Montant devis (€)", operation: "somme" }],
  ["combien de contacts par secteur ?", { action: "tableau_croise", colonne: "Secteur", operation: "nombre" }],
  ["montant moyen des devis par secteur d'activité", { action: "tableau_croise", colonne: "Secteur", colonne_valeurs: "Montant devis (€)", operation: "moyenne" }],
  ["fais un TCD des montants par entreprise", { action: "tableau_croise", colonne: "Entreprise", colonne_valeurs: "Montant devis (€)", operation: "somme" }],
  ["Fais un graphique en barres du total des devis par ville", { action: "graphique", colonne: "Ville", colonne_valeurs: "Montant devis (€)", type_graphique: "barres" }],
  ["un camembert de la répartition des montants par secteur", { action: "graphique", colonne: "Secteur", colonne_valeurs: "Montant devis (€)", type_graphique: "camembert" }],
  ["trie par montant de devis du plus grand au plus petit", { action: "trier", colonne: "Montant devis (€)", ordre: "decroissant" }],
  ["classe les contacts par ordre alphabétique de nom", { action: "trier", colonne: "Nom", ordre: "croissant" }],
  ["range par date de premier contact, les plus anciens d'abord", { action: "trier", colonne: "Date 1er contact", ordre: "croissant" }],
  ["envoie un mail à tous les contacts de Lyon", { action: "aucune" }],
  ["traduis le tableau en anglais", { action: "aucune" }]
];

async function json(url, body) {
  const r = await fetch(url, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const t = await r.text();
  if (!r.ok) throw new Error(t);
  return JSON.parse(t);
}

async function demander(modele, demande, sansReflexion) {
  const body = {
    model: modele, stream: false, format: SCHEMA, keep_alive: "5m",
    options: { temperature: 0, num_ctx: 4096 },
    messages: [{ role: "system", content: SYSTEME }, { role: "user", content: demande }]
  };
  if (sansReflexion) body.think = false;
  const t0 = Date.now();
  const j = await json(`${BASE}/api/chat`, body);
  return { sortie: JSON.parse(j.message.content), s: (Date.now() - t0) / 1000 };
}

let installes;
try {
  installes = (await json(`${BASE}/api/tags`)).models.map(m => m.name);
} catch {
  console.error("Ollama ne répond pas. Lancez-le puis relancez ce script.");
  process.exit(1);
}

const bilan = [];
for (const modele of MODELES) {
  const nom = installes.includes(modele) ? modele : installes.find(n => n === modele + ":latest");
  if (!nom) { console.log(`\n${modele} : non installé (ollama pull ${modele}), ignoré.`); continue; }
  console.log(`\n=== ${nom} ===`);
  let sansReflexion = true, ok = 0, total = 0, n = 0;
  const detail = [];
  // premier appel hors mesure : chargement du modèle en mémoire
  try { await demander(nom, "trie par nom", true); } catch (e) {
    if (/think/i.test(e.message)) sansReflexion = false; else { console.log("  erreur :", e.message); continue; }
    await demander(nom, "trie par nom", false);
  }
  for (const [demande, attendu] of CAS) {
    try {
      const { sortie, s } = await demander(nom, demande, sansReflexion);
      const ecarts = Object.entries(attendu).filter(([k, v]) => sortie[k] !== v).map(([k, v]) => `${k}=${sortie[k]} (attendu ${v})`);
      ok += ecarts.length === 0; total += s; n++;
      if (ecarts.length) console.log(`  ÉCHEC ${s.toFixed(1)} s  ${demande}\n        ${ecarts.join(" ; ")}`);
      detail.push({ demande, attendu, sortie, s });
    } catch (e) {
      console.log(`  ERREUR ${demande} : ${e.message}`); n++;
    }
  }
  let memoire = null;
  try {
    const ps = (await json(`${BASE}/api/ps`)).models.find(m => m.name === nom || m.model === nom);
    if (ps) memoire = +(ps.size / 1e9).toFixed(1);
  } catch {}
  const ligne = { modele: nom, score: ok, sur: CAS.length, temps_moyen_s: +(total / Math.max(n, 1)).toFixed(1), memoire_go: memoire };
  console.log(`  Score ${ok}/${CAS.length} · ${ligne.temps_moyen_s} s en moyenne · ${memoire ?? "?"} Go en mémoire`);
  bilan.push({ ...ligne, detail });
  try { await json(`${BASE}/api/generate`, { model: nom, keep_alive: 0 }); } catch {} // libère la mémoire
}

console.log("\n================ BILAN ================");
console.log("Modèle".padEnd(20) + "Score   Temps   Mémoire");
for (const b of bilan.sort((a, c) => c.score - a.score || a.temps_moyen_s - c.temps_moyen_s)) {
  console.log(b.modele.padEnd(20) + `${b.score}/${b.sur}`.padEnd(8) + `${b.temps_moyen_s} s`.padEnd(8) + `${b.memoire_go ?? "?"} Go`);
}
const fichier = `benchmark-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-")}.json`;
writeFileSync(fichier, JSON.stringify(bilan, null, 2));
console.log(`\nDétail enregistré dans ${fichier}`);
