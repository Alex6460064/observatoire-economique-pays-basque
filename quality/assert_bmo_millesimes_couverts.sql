-- Chaque millésime BMO ingéré doit alimenter le mart : sinon le code du bassin a changé
-- d'une année à l'autre et la série serait silencieusement tronquée.
select distinct p.annee
from {{ ref('stg_bmo__projets') }} as p
where p.annee not in (select annee from {{ ref('mart_bmo_familles') }})
