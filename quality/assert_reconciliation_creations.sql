-- Le total publiable des créations d'établissements doit égaler le décompte ligne à ligne
-- de la couche intermédiaire (mêmes filtres) : aucun événement perdu ni dupliqué par les jointures.
with attendu as (
    select count(*) as n
    from {{ ref('int_sirene__creations_etablissements') }} as c
    inner join {{ ref('dim_mois') }} as m on m.mois = c.mois
    where not c.est_reprise_ou_transfert
      and not c.date_creation_future
      and m.statut_sirene != 'non_couvert'
),

obtenu as (
    select coalesce(sum(valeur), 0) as n
    from {{ ref('fct_evenements_mensuels') }}
    where indicateur = 'creations_etablissements'
)

select attendu.n as attendu, obtenu.n as obtenu
from attendu, obtenu
where attendu.n != obtenu.n
