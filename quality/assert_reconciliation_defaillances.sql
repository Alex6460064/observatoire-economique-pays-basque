-- Idem pour les ouvertures de procédures collectives localisées dans le périmètre.
with attendu as (
    select count(*) as n
    from {{ ref('int_bodacc__evenements_localises') }} as e
    inner join {{ ref('dim_communes') }} using (code_commune)
    inner join {{ ref('dim_mois') }} using (mois)
    where e.evenement = 'ouverture_procedure'
),

obtenu as (
    select coalesce(sum(valeur), 0) as n from {{ ref('fct_evenements_mensuels') }} where indicateur = 'defaillances'
)

select attendu.n as attendu, obtenu.n as obtenu from attendu, obtenu where attendu.n != obtenu.n
