-- Nouvelles unités légales (nouveau SIREN) dont le siège est dans le périmètre.
-- Approximation documentée : la commune retenue est celle du siège actuel.
-- Une unité dont le siège est issu d'une reprise avec continuité économique n'est pas
-- une création d'entreprise au sens de l'INSEE : elle est marquée et exclue.
with ul as (
    select * from {{ ref('stg_sirene__unites_legales') }}
    where date_creation >= {{ debut_historique() }}
),

sieges as (
    select
        e.siret,
        e.code_commune,
        coalesce(c.est_reprise_ou_transfert, false) as est_reprise_ou_transfert
    from {{ ref('stg_sirene__etablissements') }} as e
    left join {{ ref('int_sirene__creations_etablissements') }} as c on c.siret = e.siret
    where e.est_siege
)

select
    ul.siren,
    ul.date_creation,
    date_trunc('month', ul.date_creation)::date as mois,
    s.code_commune,
    ul.code_naf,
    ul.est_entrepreneur_individuel,
    s.est_reprise_ou_transfert,
    ul.date_creation > {{ date_reference() }} as date_creation_future
from ul
inner join sieges as s on s.siret = ul.siret_siege
inner join {{ ref('stg_geo__communes_perimetre') }} as p on p.code_commune = s.code_commune
