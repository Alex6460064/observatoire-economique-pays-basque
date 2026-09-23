select
    annee,
    code_metier,
    libelle_metier,
    code_famille,
    libelle_famille,
    code_departement,
    code_bassin,
    libelle_bassin,
    projets,
    projets_difficiles,
    projets_saisonniers,
    projets_secret,
    -- FAP2009 jusqu'au millésime 2023, FAP2021 ensuite : les codes métier ne sont
    -- comparables qu'à nomenclature égale. Les familles (A, C, I…) le sont partout.
    case when annee <= 2023 then 'FAP2009' else 'FAP2021' end as nomenclature_metier
from {{ source('bmo', 'projets') }}
