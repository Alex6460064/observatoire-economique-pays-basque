// Tableau de bord statique : les données (déjà agrégées et passées au secret statistique)
// sont produites par `uv run obs exporter` dans src/data avant le build.
export default {
  title: "Observatoire économique du Pays Basque",
  root: "src",
  output: "dist",
  theme: ["air", "near-midnight"],
  style: "style.css",
  lang: "fr",
  search: false,
  toc: false,
  pager: false,
  cleanUrls: false,
  head: '<meta name="robots" content="index,follow"><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E%3Crect width=%2216%22 height=%2216%22 rx=%223%22 fill=%22%232a78d6%22/%3E%3Cpath d=%22M3 12 L6 8 L9 10 L13 4%22 stroke=%22white%22 stroke-width=%221.6%22 fill=%22none%22/%3E%3C/svg%3E">',
  pages: [
    {name: "Créations", path: "/creations"},
    {name: "Défaillances", path: "/defaillances"},
    {name: "Cessions", path: "/cessions"},
    {name: "Solde indicatif", path: "/solde"},
    {name: "Recrutement (BMO)", path: "/recrutement"},
    {name: "Qualité des données", path: "/qualite"},
    {name: "Méthodologie", path: "/methodologie"}
  ],
  footer: 'Projet open source — <a href="https://github.com/Alex6460064/observatoire-economique-pays-basque">code et documentation</a>. Agrégats uniquement : aucune donnée nominative.'
};
