-- Attributions retenues par la politique de confiance (voir ingestion/jev.py) ;
-- les réponses « aucun » ne sont pas utilisées.
select
    id_annonce,
    modele,
    niveau,
    code_division,
    code_section,
    confiance,
    masse_section
from {{ source('enrichissement', 'secteurs_jev') }}
where niveau in ('division', 'section')
