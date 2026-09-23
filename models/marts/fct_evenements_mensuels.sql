-- Table de faits centrale : nombre d'événements par indicateur × mois × commune × division NAF.
-- Comptages bruts, NON soumis au secret statistique : table interne, jamais publiée
-- telle quelle (l'export applique le secret, voir ingestion/export.py).
with secteurs as (
    select code_naf, code_division, code_section from {{ ref('stg_naf__secteurs') }}
),

evenements as (
    select
        'creations_etablissements' as indicateur, c.mois, c.code_commune,
        coalesce(s.code_section, 'ZZ') as code_section, coalesce(s.code_division, 'ZZ') as code_division,
        null as detail
    from {{ ref('int_sirene__creations_etablissements') }} as c
    left join secteurs as s on s.code_naf = c.code_naf
    where not c.est_reprise_ou_transfert and not c.date_creation_future

    union all
    select
        'creations_entreprises', c.mois, c.code_commune,
        coalesce(s.code_section, 'ZZ'), coalesce(s.code_division, 'ZZ'), null
    from {{ ref('int_sirene__creations_entreprises') }} as c
    left join secteurs as s on s.code_naf = c.code_naf
    where not c.est_reprise_ou_transfert and not c.date_creation_future

    union all
    select
        case evenement
            when 'immatriculation' then 'immatriculations_rcs'
            when 'radiation' then 'radiations_rcs'
            when 'cession' then 'cessions'
            when 'ouverture_procedure' then 'defaillances'
        end,
        mois,
        code_commune,
        code_section,
        code_division,
        type_procedure
    from {{ ref('int_bodacc__evenements_localises') }}
    where evenement in ('immatriculation', 'radiation', 'cession', 'ouverture_procedure')
)

select
    e.indicateur,
    e.mois,
    e.code_commune,
    e.code_section,
    e.code_division,
    e.detail,
    count(*) as valeur
from evenements as e
inner join {{ ref('dim_communes') }} as c on c.code_commune = e.code_commune
inner join {{ ref('dim_mois') }} as m on m.mois = e.mois
-- Mois postérieurs au stock Sirene : les rares créations déjà enregistrées avec une date
-- future ne représentent pas le mois ; on ne les publie pas.
where not (e.indicateur like 'creations_%' and m.statut_sirene = 'non_couvert')
group by all
