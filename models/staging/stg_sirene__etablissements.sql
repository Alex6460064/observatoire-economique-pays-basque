-- Stock mensuel complété par l'API Sirene : la version API, plus récente, l'emporte par siret.
with api as (
    select * from {{ source('sirene_api', 'etablissements') }}
),

stock as (
    select s.*
    from {{ source('sirene', 'etablissements') }} as s
    where not exists (select 1 from api as a where a.siret = s.siret)
),

fusion as (
    select * from api
    union all by name
    select * from stock
)

select
    siret,
    siren,
    nic,
    statutDiffusionEtablissement as statut_diffusion,
    dateCreationEtablissement as date_creation,
    trancheEffectifsEtablissement as tranche_effectifs,
    etablissementSiege as est_siege,
    codeCommuneEtablissement as code_commune,
    etatAdministratifEtablissement as etat_administratif,
    dateDebut as date_debut_periode,
    nomenclatureActivitePrincipaleEtablissement as nomenclature_activite,
    -- Seule la NAF rév. 2 est exploitée ; les codes d'anciennes nomenclatures
    -- (établissements anciens) ne sont pas convertis.
    case
        when nomenclatureActivitePrincipaleEtablissement = 'NAFRev2' then activitePrincipaleEtablissement
    end as code_naf,
    activitePrincipaleNAF25Etablissement as code_naf25,
    caractereEmployeurEtablissement = 'O' as est_employeur,
    cast(dateDernierTraitementEtablissement as timestamp) as date_dernier_traitement
from fusion
