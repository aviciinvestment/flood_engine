import ee
import geemap
import pandas as pd
import geopandas as gpd
import shapely.geometry as sg
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns

from gee.auth import initialize_ee
from gee.datasets import get_sentinel2, pop_data
from gee.features import build_feature_stack, create_composite
from gee.visualization import create_map, Analyze_ndvi_time_series
from gee.flood_model import FloodModel
from config import *

# -------------------
# 1. INIT SYSTEM
# -------------------
initialize_ee()

# -------------------
# 2. ROI
# -------------------
Map = create_map()

roi = ee.Geometry.Polygon([
    [-228.087384, -33.032017],
    [-228.087384, -31.189639],
    [-225.023073, -31.189639],
    [-225.023073, -33.032017],
    [-228.087384, -33.032017]
])

# -------------------
# 3. LOAD DATA
# -------------------
collection = get_sentinel2(roi)

# -------------------
# 4. FEATURE ENGINEERING
# -------------------
feature_collection = build_feature_stack(collection)
composite = create_composite(feature_collection)

feature_stack = composite.select([
    'NDVI',
    'NDWI',
    'elevation',
    'slope',
    'surface_runoff_sum',
    'total_precipitation_sum',
    'volumetric_soil_water_layer_1',
    'temperature_2m',
    'month',
    'latitude',
    'longitude',
    'historical_flood_lga',
    'high_risk_state'
])

# -------------------
# SAMPLE DATA
# -------------------
samples = feature_stack.sample(
    region=roi,
    scale=5,
    numPixels=5000,
    geometries=True
)

samples_dict = samples.getInfo()

rows = []
geoms = []

for feature in samples_dict['features']:
    rows.append(feature['properties'])
    geoms.append(feature['geometry'])

df = pd.DataFrame(rows)

# -------------------
# FEATURE SELECTION
# -------------------
feature_cols = [
    'NDVI',
    'NDWI',
    'elevation',
    'slope',
    'surface_runoff_sum',
    'total_precipitation_sum',
    'volumetric_soil_water_layer_1',
    'temperature_2m',
    'month',
    'latitude',
    'longitude',
    'historical_flood_lga',
    'high_risk_state'
]

# -------------------
# LOAD MODEL
# -------------------
model = FloodModel("flood_xgboost_model.pkl")

# -------------------
# PREDICTION (TABULAR)
# -------------------
df['prediction'] = model.predict(df[feature_cols])

print(df[['prediction']].head())
print(df)

# -------------------
# GEOMETRY FIX (✅ CORRECTED)
# -------------------
def ee_geom_to_shapely(g):
    coords = g['coordinates']

    if g['type'] == 'Point':
        return sg.Point(coords)

    elif g['type'] == 'Polygon':
        return sg.Polygon(coords[0])

    return None

df['geometry'] = [ee_geom_to_shapely(g) for g in geoms]

# ✅ FIX: ADD CRS (THIS WAS YOUR ERROR)
gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

# -------------------
# RASTER CONVERSION
# -------------------
prediction_img = geemap.geopandas_to_ee(gdf).reduceToImage(
    properties=['prediction'],
    reducer=ee.Reducer.first()
)

# -------------------
# VISUALIZATION
# -------------------
vis = {
    'min': 0,
    'max': 1,
    'palette': ['green', 'yellow', 'orange', 'red']
}

Map.addLayer(prediction_img, vis, "Flood Risk Map")

# # NDVI
# Map.addLayer(
#     feature_stack.select('NDVI'),
#     {'min': -0.2, 'max': 0.8, 'palette': ['blue', 'white', 'green']},
#     'NDVI'
# )

# # NDWI
# Map.addLayer(
#     feature_stack.select('NDWI'),
#     {'min': -0.3, 'max': 0.5, 'palette': ['white', 'blue']},
#     'NDWI'
# )

# # Elevation
# Map.addLayer(
#     feature_stack.select('elevation'),
#     {'min': 0, 'max': 2000, 'palette': ['green', 'yellow', 'brown']},
#     'Elevation'
# )

# # Slope
# Map.addLayer(
#     feature_stack.select('slope'),
#     {'min': 0, 'max': 45, 'palette': ['white', 'orange', 'red']},
#     'Slope'
# )

# # Runoff
# Map.addLayer(
#     feature_stack.select('surface_runoff_sum'),
#     {'min': 0, 'max': 100, 'palette': ['white', 'blue']},
#     'Runoff'
# )

# # Precipitation
# Map.addLayer(
#     feature_stack.select('total_precipitation_sum'),
#     {'min': 0, 'max': 200, 'palette': ['white', 'cyan', 'blue']},
#     'Precipitation'
# )

# # Soil moisture
# Map.addLayer(
#     feature_stack.select('volumetric_soil_water_layer_1'),
#     {'min': 0, 'max': 1, 'palette': ['yellow', 'green', 'darkgreen']},
#     'Soil Moisture'
# )

# # Temperature
# Map.addLayer(
#     feature_stack.select('temperature_2m'),
#     {'min': 270, 'max': 320, 'palette': ['blue', 'yellow', 'red']},
#     'Temperature'
# )

Map.centerObject(roi, 10)

Map.save("map.html")

# -------------------
# 5. NDVI TIME SERIES
# -------------------
# -------------------
# 5. STABLE MULTI-FEATURE TIME SERIES
# -------------------



# -------------------
# CLEAN DATA (SAFE)
## SAFE COPY
# -------------------
df = df.copy()
df = df.dropna()

# -------------------
# YOUR FULL FEATURE SET
# -------------------
feature_cols = [
    'NDVI',
    'NDWI',
    'elevation',
    'slope',
    'surface_runoff_sum',
    'total_precipitation_sum',
    'volumetric_soil_water_layer_1',
    'temperature_2m',
    'month',
    'latitude',
    'longitude',
    'historical_flood_lga',
    'high_risk_state'
]

# ensure only existing columns
feature_cols = [c for c in feature_cols if c in df.columns]

# -------------------
# 1. FEATURE CORRELATION (FULL MODEL VIEW)
# -------------------
plt.figure(figsize=(12, 8))
corr = df[feature_cols + ['prediction']].corr()

sns.heatmap(corr, cmap='coolwarm', annot=False)
plt.title("Flood Feature Correlation Matrix (Full Model View)")
plt.show()

# -------------------
# 2. FEATURE IMPORTANCE VIEW (prediction relationships)
# -------------------
important_features = [
    'NDVI', 'NDWI',
    'elevation', 'slope',
    'surface_runoff_sum',
    'total_precipitation_sum',
    'volumetric_soil_water_layer_1',
    'temperature_2m'
]

fig, axes = plt.subplots(2, 4, figsize=(16, 8))
axes = axes.flatten()

for i, col in enumerate(important_features):
    if col in df.columns:
        sns.boxplot(x='prediction', y=col, data=df, ax=axes[i])
        axes[i].set_title(f"{col} vs Flood Risk")

plt.tight_layout()
plt.show()

# -------------------
# 3. TIME SERIES DATAFRAME (SAFE AGGREGATION)
# -------------------
# This ONLY makes sense if multiple samples exist per month
time_series_df = (
    df.groupby('month')
    .agg({
        'NDVI': 'mean',
        'NDWI': 'mean',
        'total_precipitation_sum': 'mean',
        'volumetric_soil_water_layer_1': 'mean',
        'temperature_2m': 'mean',
        'surface_runoff_sum': 'mean'
    })
    .reset_index()
)

print("\n📊 TIME SERIES DATAFRAME (MONTHLY AGGREGATION)")
print(time_series_df.head())

# -------------------
# 4. TIME SERIES VISUALIZATION
# -------------------
plt.figure(figsize=(12, 6))

plt.plot(time_series_df['month'], time_series_df['NDVI'], label='NDVI')
plt.plot(time_series_df['month'], time_series_df['NDWI'], label='NDWI')
plt.plot(time_series_df['month'], time_series_df['total_precipitation_sum'], label='Rainfall')
plt.plot(time_series_df['month'], time_series_df['volumetric_soil_water_layer_1'], label='Soil Moisture')

plt.title("Seasonal Environmental Patterns (Monthly Averages)")
plt.xlabel("Month")
plt.ylabel("Value")
plt.legend()
plt.grid()
plt.show()

# -------------------
# 5. FLOOD RISK DISTRIBUTION
# -------------------
plt.figure(figsize=(6,4))
sns.countplot(x='prediction', data=df)
plt.title("Flood Risk Distribution")
plt.show()