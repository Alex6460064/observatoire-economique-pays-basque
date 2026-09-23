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
from {{ source('sirene', 'unites_legales') }}
