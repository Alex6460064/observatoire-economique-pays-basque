-- Sous-classe NAF rév. 2 -> division -> section, avec libellés INSEE.
select
    n.code_naf,
    n.code_division,
    d.libelle as libelle_division,
    n.code_section,
    s.libelle as libelle_section
from {{ source('naf', 'niveaux') }} as n
left join {{ source('naf', 'divisions') }} as d on d.code = n.code_division
left join {{ source('naf', 'sections') }} as s on s.code = n.code_section
