-- Garde-fou RGPD : aucune table de la couche marts (source de l'export public) ne doit
-- porter d'identifiant d'entreprise ou de donnée nominative.
select table_name, column_name
from information_schema.columns
where table_schema = 'marts'
  and (
    lower(column_name) in ('siren', 'siret', 'nic', 'id_annonce', 'nom', 'prenom', 'denomination', 'adresse', 'ville')
    or lower(column_name) like '%nom_usage%'
    or lower(column_name) like 'prenom%'
  )
