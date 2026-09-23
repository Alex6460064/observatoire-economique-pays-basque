-- Calendrier des mois publiés et statut de consolidation par famille de source.
--
-- Sirene : le stock couvre jusqu'au mois du dernier traitement INSEE observé ; les
--   `mois_provisoires_sirene` derniers mois couverts sont incomplets (enregistrements
--   tardifs : août 2026 compte ~900 créations dans le stock du 01/09 contre ~1 700 un mois
--   normal). Au-delà : non couvert.
-- BODACC : le mois courant et les `mois_provisoires_bodacc - 1` précédents sont
--   provisoires (délai entre jugement et parution : médiane 7 j, 99e centile 52 j).
with bornes as (
    select
        date_trunc('month', max(date_dernier_traitement))::date as dernier_mois_sirene,
        date_trunc('month', {{ date_reference() }})::date as mois_courant
    from {{ ref('stg_sirene__etablissements') }}
),

mois as (
    select unnest(generate_series({{ debut_historique() }}, (select mois_courant from bornes), interval 1 month))::date as mois
)

select
    m.mois,
    strftime(m.mois, '%Y-%m') as periode,
    case
        when m.mois > b.dernier_mois_sirene then 'non_couvert'
        when m.mois > b.dernier_mois_sirene - to_months({{ var('mois_provisoires_sirene') }}) then 'provisoire'
        else 'consolide'
    end as statut_sirene,
    case
        when m.mois > b.mois_courant - to_months({{ var('mois_provisoires_bodacc') }}) then 'provisoire'
        else 'consolide'
    end as statut_bodacc
from mois as m
cross join bornes as b
