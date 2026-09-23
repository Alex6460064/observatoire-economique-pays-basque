{% macro debut_historique() -%}
date '{{ var("debut_historique") }}'
{%- endmacro %}

{% macro date_reference() -%}
date '{{ var("date_reference") }}'
{%- endmacro %}
