-- Une ligne par couple (code postal, commune) sur les départements du périmètre :
-- table de rapprochement des adresses BODACC (code postal + libellé libre).
select
    unnest(codes_postaux) as code_postal,
    code_commune,
    nom_commune,
    {{ normaliser_nom('nom_commune') }} as nom_normalise
from {{ source('geo', 'communes_departements') }}
