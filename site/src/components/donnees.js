// Chargement et accès aux données publiées. Toutes les valeurs sont déjà passées au
// secret statistique par le pipeline : une case masquée a `v === null` et `secret` non vide.
import {FileAttachment} from "observablehq:stdlib";

export const meta = await FileAttachment("../data/meta.json").json();
export const qualite = await FileAttachment("../data/qualite.json").json();
export const recouvrement = await FileAttachment("../data/bmo_recouvrement.json").json();
export const communes = await FileAttachment("../data/communes.csv").csv();
export const secteurs = await FileAttachment("../data/secteurs.csv").csv();
export const mois = await FileAttachment("../data/mois.csv").csv();
export const bmoFamilles = (await FileAttachment("../data/bmo_familles.csv").csv({typed: true}));
export const bmoMetiers = (await FileAttachment("../data/bmo_metiers.csv").csv({typed: true}));
export const historiqueSeries = await FileAttachment("../data/historique_series_total.csv").csv();
export const contours = await FileAttachment("../data/communes.geojson").json();
export const historiqueQualite = await FileAttachment("../data/historique_qualite.csv").csv();

const brut = await FileAttachment("../data/indicateurs.csv").csv();

const cle = (ind, tp, p, geo, niv, sect) => `${ind}|${tp}|${p}|${geo}|${niv}|${sect}`;
const index = new Map(
  brut.map((d) => [
    cle(d.indicateur, d.type_periode, d.periode, d.geo, d.niveau_secteur, d.secteur),
    {v: d.valeur === "" ? null : +d.valeur, secret: d.secret, provisoire: d.provisoire === "1"}
  ])
);

/** Case publiée ; une case absente du fichier est un zéro publié. */
export function cellule(ind, tp, p, geo = "TOTAL", niv = "T", sect = "") {
  return index.get(cle(ind, tp, p, geo, niv, sect)) ?? {v: 0, secret: "", provisoire: false};
}

export const nomCommune = new Map(communes.map((c) => [c.code_commune, c.nom_commune]));
export const libelleSection = new Map(secteurs.map((s) => [s.code_section, s.libelle_section]));
export const libelleDivision = new Map(secteurs.map((s) => [s.code_division, s.libelle_division]));
export const sectionDeDivision = new Map(secteurs.map((s) => [s.code_division, s.code_section]));
export const sections = [...new Set(secteurs.map((s) => s.code_section))];

export const libelle = (ind) => meta.indicateurs[ind].libelle;
const sourceDe = (ind) => meta.indicateurs[ind].source;

/** Mois publiés pour l'indicateur (ceux que sa source couvre), avec leur statut. */
export function moisPublies(ind) {
  const col = `statut_${sourceDe(ind)}`;
  return mois.filter((m) => m[col] !== "non_couvert").map((m) => ({periode: m.periode, statut: m[col]}));
}

// Dates en UTC : Plot formate ses axes temporels en UTC.
const versDate = (p) => new Date(Date.UTC(+p.slice(0, 4), +p.slice(5, 7) - 1, 1));
const decaler = (p, n) => {
  const d = versDate(p);
  d.setUTCMonth(d.getUTCMonth() + n);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
};

/** Série mensuelle, avec la valeur du même mois un an plus tôt quand elle est publiée. */
export function serieMensuelle(ind, geo = "TOTAL", niv = "T", sect = "") {
  const publies = moisPublies(ind);
  const connus = new Set(publies.map((m) => m.periode));
  return publies.map(({periode, statut}) => {
    const c = cellule(ind, "mois", periode, geo, niv, sect);
    const pN1 = decaler(periode, -12);
    const n1 = connus.has(pN1) ? cellule(ind, "mois", pN1, geo, niv, sect) : null;
    return {date: versDate(periode), periode, v: c.v, secret: c.secret, provisoire: statut === "provisoire", n1: n1?.v ?? null};
  });
}

/** Fenêtres de 12 mois publiées pour l'indicateur : [précédente, dernière]. */
export function fenetres(ind) {
  const ps = [...new Set(brut.filter((d) => d.indicateur === ind && d.type_periode === "12m").map((d) => d.periode))].sort();
  return ps.slice(-2);
}

export function libelleFenetre(fin) {
  const debut = decaler(fin, -11);
  return `${moisLong(debut)} – ${moisLong(fin)}`;
}

const fmtMois = new Intl.DateTimeFormat("fr-FR", {month: "short", year: "numeric", timeZone: "UTC"});
export const moisLong = (p) => fmtMois.format(versDate(p));

const nf = new Intl.NumberFormat("fr-FR");
export const nombre = (v) => (v == null ? "s" : nf.format(v));
export const pourcent = (v, chiffres = 0) =>
  v == null || !isFinite(v) ? "–" : `${(100 * v).toLocaleString("fr-FR", {maximumFractionDigits: chiffres})} %`;

/** Évolution relative, seulement si les deux valeurs sont publiées et la base non nulle. */
export function evolution(v, base) {
  if (v == null || base == null || base === 0) return null;
  return v / base - 1;
}

/** Tableau par géographie × secteur sur une fenêtre de 12 mois. */
export function parSecteur(ind, fin, geo = "TOTAL", niv = "S") {
  const codes = niv === "S" ? sections : [...libelleDivision.keys()];
  return codes
    .map((code) => {
      const c = cellule(ind, "12m", fin, geo, niv, code);
      return {
        code,
        libelle:
          niv === "S"
            ? libelleSection.get(code)
            : code.endsWith("_ND")
              ? `Non déterminée (${libelleSection.get(sectionDeDivision.get(code))})`
              : libelleDivision.get(code),
        section: niv === "S" ? code : sectionDeDivision.get(code),
        v: c.v,
        secret: c.secret
      };
    })
    .filter((d) => d.v !== 0);
}

export function parCommune(ind, fin, precedente) {
  return communes
    .map((c) => {
      const a = cellule(ind, "12m", fin, c.code_commune);
      const b = precedente ? cellule(ind, "12m", precedente, c.code_commune) : {v: null};
      return {
        commune: c.nom_commune,
        code: c.code_commune,
        population: +c.population,
        v: a.v,
        n1: b.v,
        evolution: evolution(a.v, b.v),
        pour1000: a.v == null ? null : (1000 * a.v) / +c.population
      };
    })
    .sort((x, y) => (y.v ?? -1) - (x.v ?? -1));
}
