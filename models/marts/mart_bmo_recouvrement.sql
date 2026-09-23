-- Recouvrement entre le périmètre et les bassins d'emploi BMO : les bassins ne coïncident
-- pas avec l'EPCI. Affiché tel quel sur le site pour que le lecteur sache ce que couvre
-- le chiffre BMO.
with perimetre as (
    select * from {{ ref('dim_communes') }}
),

bassins as (
    select * from {{ ref('stg_bmo__bassins_communes') }}
    where code_bassin in (select distinct code_bassin_bmo from perimetre)
)

select
    b.code_bassin,
    any_value(b.libelle_bassin) as libelle_bassin,
    any_value(b.millesime_zonage) as millesime_zonage,
    count(*) as nb_communes_bassin,
    count(p.code_commune) as nb_communes_bassin_dans_perimetre,
    count(*) - count(p.code_commune) as nb_communes_bassin_hors_perimetre,
    sum(p.population) as population_perimetre_dans_bassin,
    round(sum(p.population) / (select sum(population) from perimetre), 4) as part_population_perimetre,
    string_agg(case when p.code_commune is null then b.libelle_commune end, ', ' order by b.libelle_commune)
        as communes_hors_perimetre
from bassins as b
left join perimetre as p on p.code_commune = b.code_commune
group by b.code_bassin
