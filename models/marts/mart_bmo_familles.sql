-- Projets de recrutement BMO par bassin d'emploi recouvrant le périmètre, année et famille de métiers.
--
-- Les cellules couvertes par le secret de France Travail (« * ») ne sont pas comptées :
-- les totaux sont des minorants, et la part de lignes secrètes est publiée à côté.
-- Les taux ne sont calculés que sur les lignes où numérateur et dénominateur sont connus.
with bassins as (
    select distinct code_bassin_bmo as code_bassin from {{ ref('dim_communes') }} where code_bassin_bmo is not null
),

p as (
    select * from {{ ref('stg_bmo__projets') }}
    where code_bassin in (select code_bassin from bassins)
)

select
    annee,
    code_bassin,
    any_value(libelle_bassin) as libelle_bassin,
    code_famille,
    any_value(libelle_famille) as libelle_famille,
    sum(projets) as projets,
    sum(projets_difficiles) filter (where projets is not null) as projets_difficiles,
    sum(projets) filter (where projets_difficiles is not null) as base_taux_difficile,
    sum(projets_saisonniers) filter (where projets is not null) as projets_saisonniers,
    sum(projets) filter (where projets_saisonniers is not null) as base_taux_saisonnier,
    count(*) as nb_metiers,
    count(*) filter (where projets_secret) as nb_metiers_secret
from p
group by annee, code_bassin, code_famille
