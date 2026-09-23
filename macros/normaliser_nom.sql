{#- Miroir SQL de socle_territorial.geo.normaliser_nom : clé de rapprochement des libellés
    de commune saisis librement (BODACC) avec le COG. Les deux côtés passent par la même
    macro, ce qui garantit la cohérence du rapprochement. -#}
{% macro normaliser_nom(col) -%}
regexp_replace(
  regexp_replace(
    regexp_replace(
      trim(regexp_replace(
        trim(regexp_replace(upper(strip_accents(coalesce({{ col }}, ''))), '[^A-Z0-9]+', ' ', 'g')),
        '\bCEDEX\b.*$', '')),
      '\bSTE\b', 'SAINTE', 'g'),
    '\bST\b', 'SAINT', 'g'),
  '^(LE|LA|LES|L) ', '')
{%- endmacro %}
