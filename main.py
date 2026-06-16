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
# -------------------
df_plot = df.copy()

# ensure no NaNs break plots
df_plot = df_plot.dropna()

# -------------------
# 1. FEATURE DISTRIBUTIONS
# -------------------
def plot_distributions(df):

    features = [
        'NDVI',
        'NDWI',
        'elevation',
        'total_precipitation_sum',
        'volumetric_soil_water_layer_1'
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    for i, col in enumerate(features):
        if col in df.columns:
            axes[i].hist(df[col], bins=30, alpha=0.7)
            axes[i].set_title(f"{col} distribution")
            axes[i].grid(True)

    plt.tight_layout()
    plt.show()


# -------------------
# 2. FLOOD VS NON-FLOOD COMPARISON
# -------------------
def plot_flood_vs_nonflood(df):

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    sns.boxplot(x='prediction', y='NDVI', data=df, ax=axes[0,0])
    axes[0,0].set_title("NDVI vs Flood Risk")

    sns.boxplot(x='prediction', y='NDWI', data=df, ax=axes[0,1])
    axes[0,1].set_title("NDWI vs Flood Risk")

    sns.boxplot(x='prediction', y='elevation', data=df, ax=axes[1,0])
    axes[1,0].set_title("Elevation vs Flood Risk")

    sns.boxplot(x='prediction', y='volumetric_soil_water_layer_1', data=df, ax=axes[1,1])
    axes[1,1].set_title("Soil Moisture vs Flood Risk")

    plt.tight_layout()
    plt.show()


# -------------------
# 3. CORRELATION HEATMAP (IMPORTANT)
# -------------------
def plot_correlation(df):

    cols = [
        'NDVI', 'NDWI', 'elevation',
        'total_precipitation_sum',
        'volumetric_soil_water_layer_1',
        'prediction'
    ]

    corr = df[cols].corr()

    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title("Feature Correlation Heatmap")
    plt.show()


# -------------------
# RUN ALL PLOTS
# -------------------
plot_distributions(df_plot)
plot_flood_vs_nonflood(df_plot)
plot_correlation(df_plot)