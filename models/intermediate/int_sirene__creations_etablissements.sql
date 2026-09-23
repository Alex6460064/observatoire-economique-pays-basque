-- Établissements dont la date de création tombe dans la fenêtre d'historique, situés
-- dans le périmètre (un établissement ne change pas de commune sans changer de SIRET).
--
-- Un nouveau SIRET n'est pas toujours une création : un transfert ou une reprise avec
-- continuité économique crée aussi un SIRET. Ces cas sont repérés via les liens de
-- succession Sirene et marqués `est_reprise_ou_transfert` (exclus des indicateurs).
with etab as (
    select * from {{ ref('stg_sirene__etablissements') }}
),

perimetre as (
    select code_commune from {{ ref('stg_geo__communes_perimetre') }}
),

successions as (
    select distinct siret_successeur as siret
    from {{ ref('stg_sirene__liens_succession') }}
    where est_continuite_economique
)

select
    e.siret,
    e.siren,
    e.code_commune,
    e.date_creation,
    date_trunc('month', e.date_creation)::date as mois,
    e.code_naf,
    e.est_siege,
    e.statut_diffusion,
    s.siret is not null as est_reprise_ou_transfert,
    e.date_creation > {{ date_reference() }} as date_creation_future
from etab as e
inner join perimetre as p on p.code_commune = e.code_commune
left join successions as s on s.siret = e.siret
where e.date_creation >= {{ debut_historique() }}
