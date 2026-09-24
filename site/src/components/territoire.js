// Sélecteurs et tableau par commune partagés par les pages thématiques.
import * as Inputs from "npm:@observablehq/inputs";
import {html} from "npm:htl";
import {communes, fenetres, nombre, parCommune, pourcent} from "./donnees.js";

export function choixTerritoire() {
  const options = [
    {code: "TOTAL", nom: "Tout le territoire"},
    ...[...communes].sort((a, b) => a.nom_commune.localeCompare(b.nom_commune, "fr")).map((c) => ({
      code: c.code_commune,
      nom: c.nom_commune
    }))
  ];
  return Inputs.select(options, {label: "Territoire", format: (d) => d.nom, value: options[0]});
}

export function tableauCommunes(ind) {
  const [precedente, fin] = fenetres(ind);
  const lignes = parCommune(ind, fin, precedente);
  return html`<div>
    ${Inputs.table(lignes, {
      columns: ["commune", "v", "n1", "evolution", "pour1000"],
      header: {
        commune: "Commune",
        v: "12 mois",
        n1: "12 mois avant",
        evolution: "Évolution",
        pour1000: "Pour 1 000 hab."
      },
      format: {
        v: nombre,
        n1: nombre,
        evolution: (v) => (v == null ? "–" : `${v > 0 ? "+" : ""}${pourcent(v)}`),
        pour1000: (v) => (v == null ? "–" : v.toLocaleString("fr-FR", {maximumFractionDigits: 1}))
      },
      sort: "v",
      reverse: true,
      rows: 12,
      layout: "auto"
    })}
    <p class="note">« s » : secret statistique (moins de 5 événements, ou valeur qui permettrait d'en recalculer une masquée).</p>
  </div>`;
}
