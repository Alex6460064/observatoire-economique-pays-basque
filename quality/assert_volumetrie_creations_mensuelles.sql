-- Détection de rupture : un mois consolidé dont les créations d'établissements tombent sous
-- 40 % de la médiane des mois consolidés signale une extraction incomplète ou un filtre cassé.
with mensuel as (
    select m.mois, coalesce(sum(f.valeur), 0) as n
    from {{ ref('dim_mois') }} as m
    left join {{ ref('fct_evenements_mensuels') }} as f
        on f.mois = m.mois and f.indicateur = 'creations_etablissements'
    where m.statut_sirene = 'consolide'
    group by m.mois
),

reference as (select median(n) as mediane from mensuel)

select mensuel.*, reference.mediane
from mensuel, reference
where mensuel.n < 0.4 * reference.mediane
