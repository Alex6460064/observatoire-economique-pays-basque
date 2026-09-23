-- Détail par métier (déjà agrégé et secrétisé par France Travail) pour les bassins du périmètre.
select
    p.annee,
    p.code_bassin,
    p.libelle_bassin,
    p.code_famille,
    p.libelle_famille,
    p.code_metier,
    p.libelle_metier,
    p.nomenclature_metier,
    p.projets,
    p.projets_difficiles,
    p.projets_saisonniers,
    p.projets_secret
from {{ ref('stg_bmo__projets') }} as p
where p.code_bassin in (select distinct code_bassin_bmo from {{ ref('dim_communes') }})
