-- Annonces BODACC exploitables, une ligne par événement :
--  * les annulations ne comptent pas et retirent l'annonce qu'elles visent ;
--  * un rectificatif remplace l'annonce qu'il corrige (on garde le rectificatif) ;
--  * classification métier de l'événement (voir docs/methodologie.md).
with annonces as (
    select * from {{ ref('stg_bodacc__annonces') }}
),

remplacees as (
    select distinct id_avis_precedent as id_annonce
    from annonces
    where type_avis in ('annulation', 'rectificatif')
      and id_avis_precedent is not null
),

classees as (
    select
        a.*,
        case
            when famille_avis = 'creation' then 'immatriculation'
            when famille_avis = 'radiation' then 'radiation'
            when famille_avis = 'vente'
                and coalesce(categorie_vente, '') not like 'Autre achat, apport, attribution%' then 'cession'
            when famille_avis = 'vente' then 'restructuration'
            when famille_avis = 'collective'
                and jugement_famille = 'Jugement d''ouverture'
                and jugement_nature not ilike '%extension%' then 'ouverture_procedure'
            when famille_avis = 'collective' then 'autre_procedure'
            when famille_avis = 'immatriculation' then 'transfert_entrant'
        end as evenement
    from annonces as a
    where type_avis in ('annonce', 'rectificatif')
      and id_annonce not in (select id_annonce from remplacees)
)

select
    *,
    case
        when evenement != 'ouverture_procedure' then null
        when jugement_nature ilike '%liquidation%' then 'liquidation'
        when jugement_nature ilike '%redressement%' then 'redressement'
        when jugement_nature ilike '%sauvegarde%' then 'sauvegarde'
        else 'autre'
    end as type_procedure,
    -- Date économique : date du jugement pour les procédures collectives (si cohérente :
    -- au plus 1 an avant la parution et jamais après), date de parution sinon.
    case
        when famille_avis = 'collective'
            and jugement_date between date_parution - interval 1 year and date_parution
            then jugement_date
        else date_parution
    end as date_evenement,
    famille_avis = 'collective'
    and (jugement_date is null or jugement_date not between date_parution - interval 1 year and date_parution)
        as date_jugement_incoherente
from classees
