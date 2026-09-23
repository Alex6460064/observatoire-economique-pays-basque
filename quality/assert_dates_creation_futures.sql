{{ config(severity = 'warn') }}
-- Anomalie de la source (non bloquante) : établissements datés après le jour du run.
-- Exclus des indicateurs ; comptés sur la page qualité.
select siret, date_creation
from {{ ref('int_sirene__creations_etablissements') }}
where date_creation_future
