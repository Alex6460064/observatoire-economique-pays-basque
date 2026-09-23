select code_commune, libelle_commune, code_bassin, libelle_bassin, millesime_zonage
from {{ source('bmo', 'bassins_communes') }}
