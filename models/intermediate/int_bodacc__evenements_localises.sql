-- Rattache chaque annonce valide à une commune et à un secteur.
--
-- Commune, par ordre de priorité :
--   1. code postal + libellé de commune de l'annonce (adresse contemporaine de l'annonce) ;
--   2. code postal seul s'il ne désigne qu'une commune ;
--   3. commune du siège dans Sirene (adresse actuelle : peut différer après un transfert).
-- Secteur, par ordre de priorité :
--   1. activité principale NAF rév. 2 de l'unité légale (Sirene), à défaut celle de son siège ;
--   2. à défaut, attribution par Jev (TypeSafe) à partir du texte d'activité de l'annonce,
--      au niveau division ou section selon la confiance (voir ingestion/jev.py) ;
--   3. sinon non déterminé.
with annonces as (
    select * from {{ ref('int_bodacc__annonces_valides') }}
),

cp as (
    select * from {{ ref('stg_geo__codes_postaux') }}
),

par_cp_ville as (
    select a.id_annonce, any_value(cp.code_commune) as code_commune, count(distinct cp.code_commune) as n
    from annonces as a
    inner join cp on cp.code_postal = a.code_postal and cp.nom_normalise = a.ville_normalisee
    group by a.id_annonce
),

cp_unique as (
    select code_postal, any_value(code_commune) as code_commune
    from cp
    group by code_postal
    having count(distinct code_commune) = 1
),

sieges as (
    select siren, any_value(code_commune) as code_commune, any_value(code_naf) as code_naf
    from {{ ref('stg_sirene__etablissements') }}
    where est_siege
    group by siren
),

ul as (
    select siren, code_naf from {{ ref('stg_sirene__unites_legales') }}
),

naf as (
    select code_naf, code_division, code_section from {{ ref('stg_naf__secteurs') }}
),

jev as (
    select * from {{ ref('stg_enrichissement__secteurs_jev') }}
),

base as (

select
    a.id_annonce,
    a.date_parution,
    a.date_evenement,
    date_trunc('month', a.date_evenement)::date as mois,
    a.evenement,
    a.type_procedure,
    a.type_personne,
    a.siren,
    a.departement,
    a.date_jugement_incoherente,
    coalesce(
        case when pcv.n = 1 then pcv.code_commune end,
        cu.code_commune,
        s.code_commune
    ) as code_commune,
    case
        when pcv.n = 1 then 'cp_ville'
        when cu.code_commune is not null then 'cp_unique'
        when s.code_commune is not null then 'sirene_siege'
        else 'non_localisee'
    end as methode_localisation,
    coalesce(ul.code_naf, s.code_naf) as code_naf_sirene,
    ul.siren is not null as siren_trouve_sirene,
    a.activite
from annonces as a
left join par_cp_ville as pcv on pcv.id_annonce = a.id_annonce
left join cp_unique as cu on cu.code_postal = a.code_postal
left join sieges as s on s.siren = a.siren
left join ul on ul.siren = a.siren
)

select
    b.*,
    case
        when b.code_naf_sirene is not null then 'sirene'
        when jev.niveau = 'division' then 'jev_division'
        when jev.niveau = 'section' then 'jev_section'
        else 'non_determine'
    end as source_secteur,
    -- Division : Sirene, sinon Jev ; pour une section seule, pseudo-division « <section>_ND »
    -- (voir dim_secteurs) afin que les divisions somment toujours à leur section.
    coalesce(naf.code_division, jev.code_division, jev.code_section || '_ND', 'ZZ') as code_division,
    coalesce(naf.code_section, jev.code_section, 'ZZ') as code_section
from base as b
left join naf on naf.code_naf = b.code_naf_sirene
left join jev on jev.id_annonce = b.id_annonce and b.code_naf_sirene is null
