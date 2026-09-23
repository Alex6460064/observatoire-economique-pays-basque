-- Métriques de qualité des données, une ligne par contrôle, affichées sur la page qualité.
-- `sens` indique si la valeur doit rester au-dessus (min) ou au-dessous (max) du seuil.
with loc as (
    select * from {{ ref('int_bodacc__evenements_localises') }}
),

valides as (
    select * from {{ ref('int_bodacc__annonces_valides') }}
),

bodacc_brut as (
    select * from {{ ref('stg_bodacc__annonces') }}
),

creations as (
    select * from {{ ref('int_sirene__creations_etablissements') }}
),

perimetre as (
    select code_commune from {{ ref('dim_communes') }}
),

metriques as (
    select 'bodacc' as source, 'annonces_extraites' as metrique,
        'Annonces BODACC extraites (départements du périmètre, fenêtre d''historique)' as libelle,
        count(*)::double as valeur, null::double as seuil, null as sens
    from bodacc_brut

    union all
    select 'bodacc', 'annonces_annulees_ou_rectifiees',
        'Annonces retirées car annulées ou remplacées par un rectificatif',
        (select count(*) from bodacc_brut where type_avis in ('annonce', 'rectificatif'))
        - (select count(*) from valides), null, null

    union all
    select 'bodacc', 'taux_siren_present',
        'Part des annonces valides portant un SIREN',
        avg((siren is not null)::int), null, null
    from loc

    union all
    select 'bodacc', 'taux_jointure_sirene',
        'Part des annonces avec SIREN retrouvées dans Sirene (jointure BODACC ↔ Sirene)',
        avg(siren_trouve_sirene::int), {{ var('taux_min_jointure_bodacc_sirene') }}, 'min'
    from loc where siren is not null

    union all
    select 'bodacc', 'taux_localisation',
        'Part des annonces valides rattachées à une commune',
        avg((methode_localisation != 'non_localisee')::int), {{ var('taux_min_localisation_bodacc') }}, 'min'
    from loc

    union all
    select 'bodacc', 'taux_localisation_cp_ville',
        'Part localisée par code postal + libellé de commune (méthode prioritaire)',
        avg((methode_localisation = 'cp_ville')::int), null, null
    from loc

    union all
    select 'bodacc', 'dates_jugement_incoherentes',
        'Procédures collectives dont la date de jugement est absente ou incohérente (date de parution retenue)',
        count(*) filter (where date_jugement_incoherente), null, null
    from loc

    union all
    select 'bodacc', 'taux_secteur_connu_perimetre',
        'Part des événements du périmètre dont le secteur NAF est connu',
        avg((source_secteur != 'non_determine')::int), null, null
    from loc where code_commune in (select code_commune from perimetre)

    union all
    select 'bodacc', 'taux_secteur_sirene_perimetre',
        'Part des événements du périmètre dont le secteur vient de Sirene',
        avg((source_secteur = 'sirene')::int), null, null
    from loc where code_commune in (select code_commune from perimetre)

    union all
    select 'bodacc', 'taux_secteur_jev_perimetre',
        'Part des événements du périmètre dont le secteur est attribué par Jev (IA TypeSafe) à partir du texte d''activité',
        avg((source_secteur like 'jev_%')::int), null, null
    from loc where code_commune in (select code_commune from perimetre)

    union all
    select 'sirene', 'etablissements_extraits',
        'Établissements Sirene extraits (départements du périmètre, tous états)',
        count(*), null, null
    from {{ ref('stg_sirene__etablissements') }}

    union all
    select 'sirene', 'part_diffusion_partielle',
        'Part des établissements créés en diffusion partielle (comptés en agrégat, jamais affichés)',
        avg((statut_diffusion = 'P')::int), null, null
    from creations

    union all
    select 'sirene', 'reprises_transferts_exclus',
        'Nouveaux SIRET exclus car issus d''une reprise ou d''un transfert (liens de succession)',
        count(*) filter (where est_reprise_ou_transfert), null, null
    from creations

    union all
    select 'sirene', 'dates_creation_futures',
        'Établissements dont la date de création est postérieure à la date du run (anomalie source)',
        count(*) filter (where date_creation_future), null, null
    from creations

    union all
    select 'sirene', 'creations_sans_naf',
        'Créations d''établissements sans code NAF rév. 2',
        count(*) filter (where code_naf is null), null, null
    from creations
)

select
    *,
    case
        when seuil is null then 'info'
        when sens = 'min' and valeur >= seuil then 'ok'
        when sens = 'max' and valeur <= seuil then 'ok'
        else 'echec'
    end as statut
from metriques
