-- Stock mensuel complété par l'API Sirene. Le stock garde chaque version d'un même lien
-- (retraitements INSEE) : une seule est retenue par (prédécesseur, successeur, date),
-- celle de l'API puis la plus récemment traitée.
with fusion as (
    select *, 1 as priorite from {{ source('sirene_api', 'liens_succession') }}
    union all by name
    select *, 2 as priorite from {{ source('sirene', 'liens_succession') }}
),

dedoublonne as (
    select *
    from fusion
    qualify row_number() over (
        partition by siretEtablissementPredecesseur, siretEtablissementSuccesseur, dateLienSuccession
        order by priorite, dateDernierTraitementLienSuccession desc
    ) = 1
)

select
    siretEtablissementPredecesseur as siret_predecesseur,
    siretEtablissementSuccesseur as siret_successeur,
    dateLienSuccession as date_lien,
    transfertSiege as est_transfert_siege,
    continuiteEconomique as est_continuite_economique
from dedoublonne
