-- Chaque mois consolidé doit contenir des annonces BODACC : un mois vide = extraction ratée.
select m.mois
from {{ ref('dim_mois') }} as m
left join {{ ref('stg_bodacc__annonces') }} as a on date_trunc('month', a.date_parution) = m.mois
where m.statut_bodacc = 'consolide'
group by m.mois
having count(a.id_annonce) = 0
