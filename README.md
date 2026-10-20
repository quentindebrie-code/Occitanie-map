# Créateur de zones sur mesure — Occitanie (Streamlit)

Application Streamlit pour visualiser les communes et codes postaux associés aux départements 09, 11, 31, 32, 65, 81 et 82, dessiner des zones personnalisées et exporter les résultats.

## Fonctionnalités
- Carte interactive centrée sur les sept départements ciblés.
- Contours des communes chargés depuis l'API officielle `geo.api.gouv.fr`.
- Filtres par département, recherche commune/code postal.
- Dessin de polygones, rectangles, lignes, cercles et marqueurs via les outils Leaflet Draw.
- Édition et suppression des formes dessinées.
- Liste des communes/codes postaux dont le point de référence tombe dans une zone polygonale.
- Export CSV de la sélection et GeoJSON des zones dessinées.

## Lancer en local
Python 3.10+ recommandé.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Déploiement sur Streamlit Community Cloud
1. Déposez le contenu de ce dossier dans un dépôt GitHub.
2. Dans Streamlit Community Cloud, choisissez le dépôt, la branche et `app.py`.
3. Le fichier `requirements.txt` installe les dépendances.
4. L'application doit pouvoir accéder à Internet pour charger les contours communaux de `geo.api.gouv.fr`.

## Données et limites
- `data/communes_codes_postaux.csv` est construit à partir du CSV fourni par l'utilisateur (fichier source daté d'août 2023), limité aux départements demandés.
- Les contours communaux sont chargés à l'exécution depuis l'API de découpage administratif de l'État : https://geo.api.gouv.fr/decoupage-administratif/communes
- La base officielle des codes postaux ne fournit pas de polygones officiels pour chaque code postal. Les zones postales peuvent se recouper et ne correspondent pas toujours aux limites communales.
- Pour associer les communes à une zone dessinée, la première version utilise le point de référence (latitude/longitude) fourni dans le CSV. Une commune est sélectionnée si ce point se trouve dans le polygone dessiné. C'est un critère simple, pas une intersection exacte de la surface communale.
- Pour une sélection métier basée sur l'intersection réelle avec le territoire communal, il faudra faire évoluer le calcul pour intersecter les polygones dessinés avec les géométries communales, et définir si l'on retient toute commune touchée ou seulement celles dont le centroïde est dans la zone.

## Sources
- Base officielle des codes postaux (La Poste) : https://www.data.gouv.fr/datasets/base-officielle-des-codes-postaux
- API de découpage administratif : https://geo.api.gouv.fr/decoupage-administratif/communes
- Contours administratifs sur data.gouv.fr : https://www.data.gouv.fr/datasets/contours-administratifs

## Licence / attribution
Vérifiez les licences des données intégrées dans votre déploiement. Le fichier de correspondance fourni par l'utilisateur est distribué avec le projet pour faciliter le démarrage.
