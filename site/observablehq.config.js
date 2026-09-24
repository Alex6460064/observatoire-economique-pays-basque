// Tableau de bord statique : les données (déjà agrégées et passées au secret statistique)
// sont produites par `uv run obs exporter` dans src/data avant le build.
export default {
  title: "Observatoire économique du Pays Basque",
  root: "src",
  output: "dist",
  // Thème clair/sombre maison dans style.css (le thème Observable est alors ignoré).
  style: "style.css",
  lang: "fr",
  search: false,
  toc: false,
  pager: false,
  cleanUrls: false,
  // Le thème choisi est appliqué avant le premier rendu (pas de flash clair en mode sombre).
  head: '<script>try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}</script>' +
    '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' +
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800&display=swap">' +
    '<meta name="robots" content="index,follow"><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E%3Crect width=%2216%22 height=%2216%22 rx=%221%22 fill=%22%239e1b22%22/%3E%3Cpath d=%22M3 12 L6 8 L9 10 L13 4%22 stroke=%22white%22 stroke-width=%221.6%22 fill=%22none%22/%3E%3C/svg%3E">',
  // Navigation horizontale dans l'en-tête (pas de barre latérale) : voir header().
  sidebar: false,
  pages: [
    {name: "Créations", path: "/creations"},
    {name: "Défaillances", path: "/defaillances"},
    {name: "Cessions", path: "/cessions"},
    {name: "Solde indicatif", path: "/solde"},
    {name: "Recrutement (BMO)", path: "/recrutement"},
    {name: "Qualité des données", path: "/qualite"},
    {name: "Méthodologie", path: "/methodologie"}
  ],
  header: ({path}) => `<a class="marque" href="./"><span class="marque-signe" aria-hidden="true"></span>Observatoire économique du Pays Basque</a>
  <nav class="nav-principale" aria-label="Rubriques">${[
    ["Créations", "creations"],
    ["Défaillances", "defaillances"],
    ["Cessions", "cessions"],
    ["Solde", "solde"],
    ["Recrutement", "recrutement"],
    ["Qualité", "qualite"],
    ["Méthodologie", "methodologie"]
  ]
    .map(([nom, p]) => `<a href="./${p}"${path === `/${p}` ? ' aria-current="page"' : ""}>${nom}</a>`)
    .join("")}</nav>
  <button type="button" class="bascule-theme" aria-label="Basculer entre thème clair et sombre" onclick="(function(){var r=document.documentElement,s=r.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'),n=s==='dark'?'light':'dark';r.dataset.theme=n;try{localStorage.setItem('theme',n)}catch(e){}})()">
    <svg class="icone-soleil" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
    <svg class="icone-lune" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
  </button>`,
  footer:'Projet open source — <a href="https://github.com/Alex6460064/observatoire-economique-pays-basque">code et documentation</a>. Agrégats uniquement : aucune donnée nominative.'
};
