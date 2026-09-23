-- Communes du périmètre, avec leur bassin d'emploi BMO (zonage France Travail).
select
    c.code_commune,
    c.nom_commune,
    c.code_departement,
    c.code_epci,
    c.population,
    b.code_bassin as code_bassin_bmo,
    b.libelle_bassin as libelle_bassin_bmo
from {{ ref('stg_geo__communes_perimetre') }} as c
left join {{ ref('stg_bmo__bassins_communes') }} as b on b.code_commune = c.code_commune
