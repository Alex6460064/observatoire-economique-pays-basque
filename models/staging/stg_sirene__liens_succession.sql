select
    siretEtablissementPredecesseur as siret_predecesseur,
    siretEtablissementSuccesseur as siret_successeur,
    dateLienSuccession as date_lien,
    transfertSiege as est_transfert_siege,
    continuiteEconomique as est_continuite_economique
from {{ source('sirene', 'liens_succession') }}
