select
    code_commune,
    nom_commune,
    code_departement,
    code_epci,
    population,
    codes_postaux
from {{ source('geo', 'communes_perimetre') }}
