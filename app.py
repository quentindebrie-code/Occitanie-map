import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import folium
from folium.plugins import Draw, Fullscreen, MeasureControl
from streamlit_folium import st_folium
from shapely.geometry import shape, Point, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "communes_codes_postaux.csv"
DEPARTEMENTS = {
    "09": "Ariège", "11": "Aude", "31": "Haute-Garonne",
    "32": "Gers", "65": "Hautes-Pyrénées", "81": "Tarn",
    "82": "Tarn-et-Garonne",
}

st.set_page_config(page_title="Zones sur mesure — Occitanie", page_icon="🗺️", layout="wide")
st.title("🗺️ Créateur de zones sur mesure — Occitanie")
st.caption("Dessinez des zones, sélectionnez les communes et codes postaux couverts, puis exportez vos résultats.")

@st.cache_data(ttl=86400, show_spinner=False)
def load_communes_geojson():
    """Récupère les contours officiels des communes depuis geo.api.gouv.fr."""
    features = []
    for dep in DEPARTEMENTS:
        url = "https://geo.api.gouv.fr/communes"
        params = {
            "codeDepartement": dep,
            "fields": "nom,code,departement",
            "format": "geojson",
            "geometry": "contour",
        }
        r = requests.get(url, params=params, timeout=40)
        r.raise_for_status()
        payload = r.json()
        features.extend(payload.get("features", []))
    return {"type": "FeatureCollection", "features": features}

df = pd.read_csv(DATA_PATH, dtype={"code_postal": str, "code_insee": str, "code_departement": str})
df["code_postal"] = df["code_postal"].str.zfill(5)
df["code_departement"] = df["code_departement"].str.zfill(2)
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df = df.dropna(subset=["latitude", "longitude"])

with st.sidebar:
    st.header("Filtres")
    selected_deps = st.multiselect(
        "Départements affichés",
        options=list(DEPARTEMENTS),
        default=list(DEPARTEMENTS),
        format_func=lambda x: f"{x} — {DEPARTEMENTS[x]}",
    )
    search = st.text_input("Rechercher une commune ou un code postal")
    show_boundaries = st.checkbox("Afficher les contours des communes", value=True)
    show_points = st.checkbox("Afficher les points des communes", value=False)
    st.markdown("---")
    st.markdown("**Dessiner sur la carte**")
    st.caption("Utilisez la barre d’outils en haut à gauche : polygone, rectangle, ligne, marqueur ou cercle. Les polygones servent à définir les zones.")

if not selected_deps:
    st.warning("Choisissez au moins un département.")
    st.stop()

filtered = df[df["code_departement"].isin(selected_deps)].copy()
if search.strip():
    term = search.strip().lower()
    filtered = filtered[
        filtered["commune"].str.lower().str.contains(term, na=False)
        | filtered["code_postal"].str.contains(term, na=False)
    ]

@st.cache_data(ttl=86400, show_spinner="Chargement des contours officiels des communes…")
def safe_geojson():
    return load_communes_geojson()

try:
    geojson = safe_geojson()
    geojson["features"] = [
        f for f in geojson["features"]
        if str(f.get("properties", {}).get("code", ""))[:2] in selected_deps
    ]
    geo_error = None
except Exception as exc:
    geojson = {"type": "FeatureCollection", "features": []}
    geo_error = str(exc)

center_lat = float(filtered["latitude"].mean()) if not filtered.empty else 43.6
center_lon = float(filtered["longitude"].mean()) if not filtered.empty else 1.45
m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles="OpenStreetMap", control_scale=True)
Fullscreen(position="topright").add_to(m)
MeasureControl(position="topright", primary_length_unit="kilometers").add_to(m)

if show_boundaries and geojson["features"]:
    folium.GeoJson(
        geojson,
        name="Contours officiels des communes",
        style_function=lambda feat: {
            "color": "#536d8a", "weight": 1, "fillColor": "#a9c6e8",
            "fillOpacity": 0.08,
        },
        tooltip=folium.GeoJsonTooltip(fields=["nom", "code"], aliases=["Commune", "Code INSEE"]),
    ).add_to(m)

if show_points:
    for _, row in filtered.iterrows():
        folium.CircleMarker(
            [row["latitude"], row["longitude"]], radius=3,
            tooltip=f'{row["commune"]} — {row["code_postal"]}',
            color="#d35400", fill=True, fill_opacity=0.8,
        ).add_to(m)

Draw(
    export=True,
    filename="zones_occitanie.geojson",
    position="topleft",
    draw_options={
        "polyline": True,
        "polygon": {"allowIntersection": False, "showArea": True},
        "rectangle": True,
        "circle": True,
        "marker": True,
        "circlemarker": False,
    },
    edit_options={"edit": True, "remove": True},
).add_to(m)
folium.LayerControl(collapsed=True).add_to(m)

left, right = st.columns([3, 1])
with left:
    map_result = st_folium(
        m, height=690, use_container_width=True,
        returned_objects=["all_drawings", "last_active_drawing", "last_object_clicked"],
        key="occitanie_zone_map",
    )
with right:
    st.subheader("Mode d’emploi")
    st.markdown(
        "1. Zoomez jusqu’au secteur souhaité.\n"
        "2. Dessinez un **polygone** ou un **rectangle** autour de votre zone.\n"
        "3. Modifiez ou supprimez les formes avec les outils d’édition.\n"
        "4. Les communes dont le point de référence tombe dans le polygone sont listées ci-dessous.\n"
        "5. Exportez la sélection en CSV et les formes en GeoJSON."
    )
    st.info("Les codes postaux n’ont pas de limites géographiques officielles universelles. La sélection ci-dessous se base sur les points de référence des communes, pas sur une prétendue frontière officielle de code postal.")

drawings = (map_result or {}).get("all_drawings") or []
polygon_geoms = []
for feature in drawings:
    try:
        geom = shape(feature.get("geometry", {}))
        if geom.geom_type in ("Polygon", "MultiPolygon"):
            polygon_geoms.append(geom)
    except Exception:
        pass

if polygon_geoms:
    zones_geom = unary_union(polygon_geoms)
    # Keep postal-code rows whose commune reference point falls inside any drawn polygon.
    chosen_mask = filtered.apply(
        lambda row: zones_geom.covers(Point(float(row["longitude"]), float(row["latitude"]))),
        axis=1,
    )
    selected_rows = filtered[chosen_mask].copy()
else:
    selected_rows = filtered.iloc[0:0].copy()

st.divider()
st.subheader("Résultat de la sélection")
metric1, metric2, metric3 = st.columns(3)
metric1.metric("Communes / codes postaux", f"{len(selected_rows):,}".replace(",", " "))
metric2.metric("Communes distinctes", f"{selected_rows['commune'].nunique():,}".replace(",", " "))
metric3.metric("Codes postaux distincts", f"{selected_rows['code_postal'].nunique():,}".replace(",", " "))

if not polygon_geoms:
    st.write("Dessinez un polygone ou un rectangle sur la carte pour afficher les communes et codes postaux sélectionnés.")
elif selected_rows.empty:
    st.warning("Aucun point de commune n’est inclus dans les zones dessinées. Essayez d’élargir ou déplacer le polygone.")
else:
    st.dataframe(
        selected_rows[["code_postal", "commune", "code_departement", "departement", "code_insee"]]
        .drop_duplicates()
        .sort_values(["code_departement", "code_postal", "commune"]),
        use_container_width=True,
        hide_index=True,
    )
    csv_bytes = selected_rows[["code_postal", "commune", "code_departement", "departement", "code_insee"]].drop_duplicates().to_csv(index=False).encode("utf-8-sig")
    st.download_button("Télécharger la sélection (CSV)", csv_bytes, "selection_zones_occitanie.csv", "text/csv")

if drawings:
    export_geojson = {
        "type": "FeatureCollection",
        "name": "zones_personnalisees_occitanie",
        "features": drawings,
    }
    st.download_button(
        "Télécharger les zones dessinées (GeoJSON)",
        json.dumps(export_geojson, ensure_ascii=False, indent=2).encode("utf-8"),
        "zones_personnalisees_occitanie.geojson",
        "application/geo+json",
    )

with st.expander("À propos des données et des limites géographiques"):
    st.markdown(
        "- **Correspondance codes postaux / communes** : fichier CSV fourni dans le projet, dérivé de la base communale d’août 2023.\n"
        "- **Contours communaux** : récupérés au lancement depuis l’API officielle `geo.api.gouv.fr`.\n"
        "- **Limite importante** : une commune peut avoir plusieurs codes postaux et un code postal peut couvrir plusieurs communes. Les contours dessinés par l’utilisateur sont donc la source de vérité pour les zones métier; l’application ne prétend pas reconstituer une frontière officielle de code postal.\n"
        "- **Sélection actuelle** : une commune est retenue si son point de référence fourni dans le CSV se trouve dans une zone dessinée. Ce choix est rapide et reproductible, mais ne signifie pas que toute la surface communale est couverte."
    )
if geo_error:
    st.warning(f"Impossible de charger les contours depuis l’API officielle. Vérifiez la connexion internet. Détail technique : {geo_error}")
