-- Sections et divisions NAF rév. 2, plus une modalité « non déterminé » (ZZ) pour les
-- événements sans activité connue : elle garantit que les secteurs somment au total.
with divisions as (
    select distinct code_division, libelle_division, code_section, libelle_section
    from {{ ref('stg_naf__secteurs') }}
)

select * from divisions
union all
-- Événements dont seule la section est connue (attribution Jev de confiance moyenne).
select distinct code_section || '_ND', 'Division non déterminée', code_section, libelle_section from divisions
union all
select 'ZZ', 'Activité non déterminée', 'ZZ', 'Activité non déterminée'
