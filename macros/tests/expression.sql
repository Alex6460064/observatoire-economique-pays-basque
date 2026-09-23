{#- Test générique : chaque valeur non nulle de la colonne doit vérifier `expression`.
    Exemple : data_tests: [{expression: {arguments: {expression: "> 0"}}}] -#}
{% test expression(model, column_name, expression) %}
select *
from {{ model }}
where {{ column_name }} is not null
  and not ({{ column_name }} {{ expression }})
{% endtest %}
