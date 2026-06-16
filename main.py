import ee
import geemap
import pandas as pd
import geopandas as gpd
import shapely.geometry as sg
import matplotlib.pyplot as plt
from datetime import datetime

from gee.auth import initialize_ee
from gee.datasets import get_sentinel2
from gee.features import build_feature_stack, create_composite
from gee.visualization import create_map, Analyze_ndvi_time_series
from gee.flood_model import FloodModel
from config import *

# -------------------
# INIT
# -------------------
initialize_ee()
Map = create_map()

# -------------------
# ROI
# -------------------
roi = ee.Geometry.Polygon([
    [-228.087384, -33.032017],
    [-228.087384, -31.189639],
    [-225.023073, -31.189639],
    [-225.023073, -33.032017],
    [-228.087384, -33.032017]
])

# -------------------
# DATA
# -------------------
collection = get_sentinel2(roi)

feature_collection = build_feature_stack(collection)
composite = create_composite(feature_collection)

feature_stack = composite.select([
    'NDVI','NDWI','elevation','slope',
    'surface_runoff_sum','total_precipitation_sum',
    'volumetric_soil_water_layer_1','temperature_2m',
    'month','latitude','longitude',
    'historical_flood_lga','high_risk_state'
])

# -------------------
# SAMPLE
# -------------------
samples = feature_stack.sample(region=roi, scale=10, numPixels=5000, geometries=True)
features = samples.getInfo()['features']

rows = []
geoms = []

for f in features:
    p = f['properties']

    row = {
        'NDVI': p.get('NDVI'),
        'NDWI': p.get('NDWI'),
        'elevation': p.get('elevation'),
        'slope': p.get('slope'),
        'surface_runoff_sum': p.get('surface_runoff_sum'),
        'total_precipitation_sum': p.get('total_precipitation_sum'),
        'volumetric_soil_water_layer_1': p.get('volumetric_soil_water_layer_1'),
        'temperature_2m': p.get('temperature_2m'),
        'month': p.get('month'),
        'latitude': p.get('latitude'),
        'longitude': p.get('longitude'),
        'historical_flood_lga': p.get('historical_flood_lga'),
        'high_risk_state': p.get('high_risk_state')
    }

    if None not in row.values():
        rows.append(row)
        geoms.append(f['geometry'])

df = pd.DataFrame(rows)

# -------------------
# MODEL
# -------------------
model = FloodModel("flood_xgboost_model.pkl")

feature_cols = [
    'NDVI','NDWI','elevation','slope',
    'surface_runoff_sum','total_precipitation_sum',
    'volumetric_soil_water_layer_1','temperature_2m',
    'month','latitude','longitude',
    'historical_flood_lga','high_risk_state'
]

df['prediction'] = model.predict(df[feature_cols])

print("Prediction done:", df['prediction'].head())

# -------------------
# GEOMETRY FIX
# -------------------
df['geometry'] = [
    sg.Point(lon, lat)
    for lon, lat in zip(df['longitude'], df['latitude'])
]

gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

# -------------------
# MAP RASTER
# -------------------
prediction_img = geemap.geopandas_to_ee(gdf).reduceToImage(
    properties=['prediction'],
    reducer=ee.Reducer.first()
)

Map.addLayer(prediction_img, {
    'min': 0,
    'max': 1,
    'palette': ['green','yellow','orange','red']
}, "Flood Risk")

Map.centerObject(roi, 10)
Map.save("map.html")

# ==========================================================
# 🌊 TIME SERIES (SAFE VERSION - NO CRASH)
# ==========================================================

Analyze = Analyze_ndvi_time_series(roi, START_DATE, END_DATE, composite)

ts_collection = collection.map(Analyze.add_ndvi_and_time)
ts = ts_collection.map(Analyze.extract_ndvi_value)

ts_features = ts.getInfo()['features']

df_ts = []

for f in ts_features:
    p = f['properties']

    df_ts.append({
        'date': datetime.fromtimestamp(p['date']['value'] / 1000),
        'NDVI': p.get('NDVI'),
        'NDWI': p.get('NDWI'),
        'elevation': p.get('elevation'),
        'slope': p.get('slope'),
        'surface_runoff_sum': p.get('surface_runoff_sum'),
        'total_precipitation_sum': p.get('total_precipitation_sum'),
        'volumetric_soil_water_layer_1': p.get('volumetric_soil_water_layer_1'),
        'temperature_2m': p.get('temperature_2m')
    })

df_ts = pd.DataFrame(df_ts)

# -------------------
# CLEAN CORRELATION (FIXED)
# -------------------
corr_features = [
    'NDVI','NDWI','elevation','slope',
    'surface_runoff_sum','total_precipitation_sum',
    'volumetric_soil_water_layer_1','temperature_2m'
]

# keep only existing columns (CRITICAL FIX)
corr_features = [c for c in corr_features if c in df_ts.columns]

corr = df_ts[corr_features].corr()

print("\n📊 CORRELATION (SAFE)")
print(corr)

# -------------------
# SAFE PLOT
# -------------------
def plot_safe(df):

    fig, axs = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)

    if 'NDVI' in df:
        axs[0,0].plot(df['NDVI'])
        axs[0,0].set_title("NDVI")

    if 'NDWI' in df:
        axs[0,1].plot(df['NDWI'])
        axs[0,1].set_title("NDWI")

    if 'surface_runoff_sum' in df:
        axs[1,0].plot(df['surface_runoff_sum'])
        axs[1,0].set_title("Runoff")

    if 'temperature_2m' in df:
        axs[1,1].plot(df['temperature_2m'])
        axs[1,1].set_title("Temperature")

    plt.show()

plot_safe(df_ts)