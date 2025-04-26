import os
import streamlit as st
import plotly.express as px
import geopandas as gpd
import pandas as pd

# Setze den Seitenlayout auf "wide", damit die Darstellung den ganzen Bildschirm nutzt
st.set_page_config(layout="wide")

# Setze den Dateipfad
GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "analyse_ergebnis_combined.geojson")


def main():
    with st.container():
        st.title("Anbindung deutscher Gemeinden ans Bahnnetz")

        # GeoJSON-Daten laden
        gemeinde_gdf = gpd.read_file(GEOJSON_PATH)

        # Sicherstellen, dass die Spalte 'anbindung' in der gewünschten Reihenfolge vorliegt
        # Wir definieren sie als kategorischen Datentyp
        anbindung_order = ["sehr gut", "gut", "mäßig", "schlecht"]
        gemeinde_gdf["anbindung"] = pd.Categorical(gemeinde_gdf["anbindung"],
                                                   categories=anbindung_order,
                                                   ordered=True)

        # Erstelle eine interaktive Karte mit Plotly für Gemeinden
        fig = px.scatter_map(
            gemeinde_gdf,
            lat=gemeinde_gdf.geometry.y,
            lon=gemeinde_gdf.geometry.x,
            title="Klassifizierung des Anschlusses aller Gemeinden an das Bahnnetz des Fern- und Regionalverkehrs der Deutschen Bahn",
            color="anbindung",
            color_discrete_map={
                "sehr gut": "green",
                "gut": "lightgreen",
                "mäßig": "orange",
                "schlecht": "red"
            },
            size="Einwohner",
            hover_name="Gitter_ID_1km",
            hover_data=["anbindung", "distanz_km", "haltefrequenz"],
            zoom=5,
            height=800,
            width=1200,
        )

        # Konfiguriere den Maplibre-Stil (OpenStreetMap als Basis)
        fig.update_layout(mapbox_style="open-street-map")

        # Setze Layout und Ränder des Plots
        fig.update_layout(margin={"r": 0, "t": 30, "l": 0, "b": 0})

        # Plotly-Graph in Streamlit anzeigen
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()

def main_last_Version():
    st.title("Anbindung deutscher Gemeinden ans Bahnnetz")

    # GeoJSON-Daten laden
    gdf = gpd.read_file(GEOJSON_PATH)

    # Falls im kombinierten GeoDataFrame beide Typen (Gemeinden und Bahnhöfe) enthalten sind,
    # filtern wir diese jeweils
    bahnhof_gdf = gdf[gdf['type'] == 'Bahnhof']
    gemeinde_gdf = gdf[gdf['type'] == 'Gemeinde']

    # Falls bei den Bahnhöfen der Haltefrequenz-Wert in der Spalte 'halte_pro_tag' gespeichert ist,
    # unterteilen wir diese in zwei Gruppen: mit Halten == 0 und > 0.
    if 'halte_pro_tag' in bahnhof_gdf.columns:
        bahnhof_zero = bahnhof_gdf[bahnhof_gdf["halte_pro_tag"] == 0]
        bahnhof_non_zero = bahnhof_gdf[bahnhof_gdf["halte_pro_tag"] != 0]
    else:
        # Falls die Spalte anders heißt, etwa 'haltefrequenz', dann:
        bahnhof_zero = bahnhof_gdf[bahnhof_gdf["haltefrequenz"] == 0]
        bahnhof_non_zero = bahnhof_gdf[bahnhof_gdf["haltefrequenz"] != 0]

    # Erstelle eine interaktive Karte mit Plotly für Gemeinden
    fig = px.scatter_map(
        gemeinde_gdf,
        lat=gemeinde_gdf.geometry.y,
        lon=gemeinde_gdf.geometry.x,
        color="anbindung",
        color_discrete_map={
            "sehr gut": "green",
            "gut": "lightgreen",
            "mäßig": "orange",
            "schlecht": "red"
        },
        size="Einwohner",
        hover_name="Gitter_ID_1km",
        hover_data=["anbindung", "distanz_km", "haltefrequenz"],
        zoom=5,
        height=700,
        width=700,
    )

    # Füge zuerst alle Bahnhöfe mit nicht-null Haltefrequenz hinzu (Farbe: blau)
    fig.add_scattermapbox(
        lat=bahnhof_non_zero.geometry.y,
        lon=bahnhof_non_zero.geometry.x,
        mode='markers',
        marker=dict(size=6, color="blue"),
        name='Bahnhöfe (Freq > 0)',
        hoverinfo='text',
        text=bahnhof_non_zero['stop_id']
    )

    # Füge nun die Bahnhöfe mit Haltefrequenz 0 hinzu (andere Farbe, z. B. magenta)
    fig.add_scattermapbox(
        lat=bahnhof_zero.geometry.y,
        lon=bahnhof_zero.geometry.x,
        mode='markers',
        marker=dict(size=6, color="magenta"),
        name='Bahnhöfe (Freq = 0)',
        hoverinfo='text',
        text=bahnhof_zero['stop_id']
    )

    # Konfiguriere den Maplibre-Stil (OpenStreetMap als Basis)
    fig.update_layout(mapbox_style="open-street-map")

    # Setze Titel und Layout des Plots
    fig.update_layout(margin={"r": 0, "t": 30, "l": 0, "b": 0})

    # Plotly-Graph in Streamlit anzeigen
    st.plotly_chart(fig, use_container_width=True)
