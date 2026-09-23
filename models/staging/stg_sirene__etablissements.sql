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
from {{ source('sirene', 'etablissements') }}
