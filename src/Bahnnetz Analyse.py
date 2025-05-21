import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from scipy.spatial import cKDTree
import os
from datetime import timedelta

# Setze den Datenpfad
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")
FV_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data/Fernverkehr")
RV_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data/Regionalverkehr")

# 1. Daten einladen
# Gemeinden mit georeferenzierten Bevölkerungsdaten
gemeinden = pd.read_csv(os.path.join(DATA_PATH, "Georeferenzierte_BevDaten_2021.csv"), sep=';')

# Funktion zur Extraktion von Koordinaten aus der Gitter-ID
def gitter_id_to_coords(gitter_id):
    parts = gitter_id.replace('CRS3035RES1000m', '').split('E')
    northing = int(parts[0].strip('N'))
    easting = int(parts[1])
    return easting, northing

# Extrahiere Easting und Northing aus den Gitter-IDs und erstelle ein GeoDataFrame
gemeinden[['easting', 'northing']] = gemeinden['Gitter_ID_1km'].apply(gitter_id_to_coords).apply(pd.Series)
gemeinden_gdf = gpd.GeoDataFrame(gemeinden, geometry=gpd.points_from_xy(gemeinden.easting, gemeinden.northing), crs="EPSG:3035")
# Transformiere ins WGS84 CRS
gemeinden_gdf = gemeinden_gdf.to_crs("EPSG:4326")

# Bahnhöfe aus GTFS-Daten laden
FV_stops = pd.read_csv(os.path.join(FV_DATA_PATH, "stops.txt"))
RV_stops = pd.read_csv(os.path.join(RV_DATA_PATH, "stops.txt"))

# Standardisiere stop_id: Konvertiere zu String und entferne eventuelle Leerzeichen
FV_stops['stop_id'] = FV_stops['stop_id'].astype(str).str.strip()
RV_stops['stop_id'] = RV_stops['stop_id'].astype(str).str.strip()

FV_bahnhoefe = gpd.GeoDataFrame(
    FV_stops,
    geometry=[Point(xy) for xy in zip(FV_stops.stop_lon, FV_stops.stop_lat)],
    crs="EPSG:4326"
)
RV_bahnhoefe = gpd.GeoDataFrame(
    RV_stops,
    geometry=[Point(xy) for xy in zip(RV_stops.stop_lon, RV_stops.stop_lat)],
    crs="EPSG:4326"
)
# Füge beide Datensätze zusammen
bahnhoefe = pd.concat([FV_bahnhoefe, RV_bahnhoefe])

# GTFS-Fahrplandaten laden
FV_stop_times = pd.read_csv(os.path.join(FV_DATA_PATH, "stop_times.txt"))
FV_trips = pd.read_csv(os.path.join(FV_DATA_PATH, "trips.txt"))
FV_calendar = pd.read_csv(os.path.join(FV_DATA_PATH, "calendar.txt"))

RV_stop_times = pd.read_csv(os.path.join(RV_DATA_PATH, "stop_times.txt"))
RV_trips = pd.read_csv(os.path.join(RV_DATA_PATH, "trips.txt"))
RV_calendar = pd.read_csv(os.path.join(RV_DATA_PATH, "calendar.txt"))

# Standardisiere die stop_id in stop_times
FV_stop_times['stop_id'] = FV_stop_times['stop_id'].astype(str).str.strip()
RV_stop_times['stop_id'] = RV_stop_times['stop_id'].astype(str).str.strip()

# Vereine die Fahrplandaten
stop_times = pd.concat([FV_stop_times, RV_stop_times])
trips = pd.concat([FV_trips, RV_trips])
calendar = pd.concat([FV_calendar, RV_calendar])

# Debugging: Vergleiche die IDs aus stops.txt und stop_times.txt
stops_ids = set(bahnhoefe['stop_id'])
stop_times_ids = set(stop_times['stop_id'])
fehlende_ids = stops_ids - stop_times_ids
print("Stop-IDs, die in stop_times.txt fehlen:", fehlende_ids)

# 2. Berechnung der durchschnittlichen Haltefrequenz pro Tag je Bahnhof
tage = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

# Wochentage als Integer-Spalten
calendar[tage] = calendar[tage].fillna(0).astype(int)

# Zähle, an wie vielen Wochentagen der Dienst aktiv ist
calendar['fahrtage_pro_woche'] = calendar[tage].sum(axis=1)

# Verknüpfe trips mit Fahrtagen pro Woche
trips = trips.merge(calendar[['service_id', 'fahrtage_pro_woche']], on='service_id', how='left')

# Verknüpfe stop_times mit Fahrtagen pro Woche
stop_times = stop_times.merge(trips[['trip_id', 'fahrtage_pro_woche']], on='trip_id', how='left')

# Entferne Duplikate: gleiche trip_id, stop_id und Ankunftszeit
stop_times_unique = stop_times.drop_duplicates(subset=['trip_id', 'stop_id', 'arrival_time'])

# Berechne Halte pro Woche je stop_id
haltefrequenz = stop_times_unique.groupby('stop_id')['fahrtage_pro_woche'].sum().reset_index()

# Rechne auf durchschnittliche Halte pro Tag um
haltefrequenz['halte_pro_tag'] = (haltefrequenz['fahrtage_pro_woche'] / 7).round(2)

# Mergen mit GeoDaten der Bahnhöfe
bahnhoefe = bahnhoefe.merge(haltefrequenz[['stop_id', 'halte_pro_tag']], on='stop_id', how='left')
bahnhoefe['halte_pro_tag'] = bahnhoefe['halte_pro_tag'].fillna(0)

# Debugging: Überprüfe, ob Stop-IDs korrekt gemappt wurden
print("Verteilung der Haltefrequenz:")
print(bahnhoefe["halte_pro_tag"].describe())

# << Filter: Entferne Bahnhöfe, die nicht in stop_times erscheinen >>
bahnhoefe = bahnhoefe[bahnhoefe["halte_pro_tag"] > 0]

# 3. K-D-Baum für schnellste Distanzberechnung
bahnhoefe_coords = list(zip(bahnhoefe.geometry.x, bahnhoefe.geometry.y))
gemeinde_coords = list(zip(gemeinden_gdf.geometry.x, gemeinden_gdf.geometry.y))
tree = cKDTree(bahnhoefe_coords)
distances, indices = tree.query(gemeinde_coords)
# Hier wird jeweils der nächstgelegene, bediente Bahnhof herangezogen
gemeinden_gdf["distanz_km"] = distances * 111  # grobe Umrechnung von Grad in km
gemeinden_gdf["haltefrequenz"] = [bahnhoefe.iloc[i]["halte_pro_tag"] for i in indices]

# Debugging: Überprüfung der Gemeindeanbindung
print("Beispieldaten für Gemeinden mit Haltefrequenz und Distanz:")
print(gemeinden_gdf[["distanz_km", "haltefrequenz"]].head(20))

# 4. Klassifikation der Anbindung
def klassifiziere_anbindung(dist, halte):
    if dist <= 3 and halte >= 72: # alle 15 min fährt ein Zug zwischen 6 Uhr und 0 Uhr (4*18)
        return "sehr gut"
    elif dist <= 8 and halte >= 36: # alle 30 min fährt ein Zug zwischen 6 Uhr und 0 Uhr (2*18)
        return "gut"
    elif dist <= 12 and halte >= 18: # alle 60 min fährt ein Zug zwischen 6 Uhr und 0 Uhr (1*18)
        return "mäßig"
    else:
        return "schlecht"

gemeinden_gdf["anbindung"] = gemeinden_gdf.apply(lambda row: klassifiziere_anbindung(row["distanz_km"], row["haltefrequenz"]), axis=1)
gemeinden_gdf.to_file(os.path.join(DATA_PATH, "analyse_ergebnis_combined.geojson"), driver="GeoJSON")
"""
# Bahnhöfe in Sachsen
sachsen_grenzen = gpd.read_file(os.path.join(DATA_PATH, "gemeinden_simplify200.geojson"))
# Transformiere Bahnhöfe ins gleiche CRS wie die Sachsen-Grenzen
bahnhoefe = bahnhoefe.to_crs(sachsen_grenzen.crs)
# Filtere nur die Bahnhöfe, die innerhalb von Sachsen liegen
sachsen_union = sachsen_grenzen.geometry.unary_union
bahnhoefe_in_sachsen = bahnhoefe[bahnhoefe.within(sachsen_union)]
gemeinden_in_sachsen = gemeinden_gdf[gemeinden_gdf.within(sachsen_union)]

# 5. Zusammenführen der GeoDataFrames
gemeinden_in_sachsen['type'] = 'Gemeinde'
bahnhoefe_in_sachsen['type'] = 'Bahnhof'
combined_gdf = pd.concat([gemeinden_in_sachsen, bahnhoefe_in_sachsen], ignore_index=True)

# Speichern der Ergebnisse
combined_gdf.to_file(os.path.join(DATA_PATH, "analyse_ergebnis_combined.geojson"), driver="GeoJSON")
"""