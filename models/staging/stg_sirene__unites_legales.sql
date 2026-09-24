-- Stock mensuel complété par l'API Sirene : la version API, plus récente, l'emporte par siren.
with api as (
    select * from {{ source('sirene_api', 'unites_legales') }}
),

stock as (
    select s.*
    from {{ source('sirene', 'unites_legales') }} as s
    where not exists (select 1 from api as a where a.siren = s.siren)
),

fusion as (
    select * from api
    union all by name
    select * from stock
)

select
    siren,
    statutDiffusionUniteLegale as statut_diffusion,
    unitePurgeeUniteLegale = 'true' as est_purgee,
    dateCreationUniteLegale as date_creation,
    categorieJuridiqueUniteLegale as categorie_juridique,
    categorieJuridiqueUniteLegale = '1000' as est_entrepreneur_individuel,
    case
        when nomenclatureActivitePrincipaleUniteLegale = 'NAFRev2' then activitePrincipaleUniteLegale
    end as code_naf,
    etatAdministratifUniteLegale as etat_administratif,
    siren || nicSiegeUniteLegale as siret_siege,
    categorieEntreprise as categorie_entreprise
from fusion
