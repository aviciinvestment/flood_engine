import joblib
model = joblib.load("./model_features.pkl")
print(model)

import ee
import geemap
import pandas as pd
import geopandas as gpd
import shapely.geometry as sg
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns
import rasterio
import pprint
import time
from rasterio.merge import merge
from rasterio.transform import Affine
import numpy as np
import folium
from folium import raster_layers

from matplotlib import cm

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
    [-67.206839, -19.925036], [-67.206839, -19.882425], [-67.167368, -19.882425], [-67.167368, -19.925036], [-67.206839, -19.925036]
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


ee.Classifier.smileRandomForest(numberOfTrees=150, bagFraction=0.5, maxNodes=5, variablesPerSplit=4, minLeafPopulation=1, seed=0)
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


# feature_stack = feature_stack.toFloat()
# task = ee.batch.Export.image.toDrive(
#     image=feature_stack,
#     description='flood_features',
#     folder='FloodAI1',
#     fileNamePrefix='feature_stack',
#     scale=100,
#     region=roi,
#     maxPixels=1e13
# )

# task.start()

# print(task.status())

# while True:
#     status = task.status()
#     pprint.pprint(task.status())

#     if status['state'] in ['COMPLETED', 'FAILED', 'CANCELLED']:
#         break

#     time.sleep(20)




# -----------------------------
# MERGE ALL TILES
# # -----------------------------
# files = [
#     "tile1.tif",
#     "tile2.tif",
#     "tile3.tif",
#     "tile4.tif",
#     "tile5.tif",
#     "tile6.tif",
#     "tile7.tif",
#     "tile8.tif",
#     "tile9.tif",
#     "tile10.tif",
#     "tile11.tif",
#     "tile12.tif"
# ]

# src_files = [rasterio.open(f) for f in files]

# mosaic, transform = merge(src_files)

# # metadata from first tile
# meta = src_files[0].meta.copy()

# meta.update({
#     "height": mosaic.shape[1],
#     "width": mosaic.shape[2],
#     "transform": transform
# })

# # save merged raster
# with rasterio.open(
#     "feature_stack_merged.tif",
#     "w",
#     **meta
# ) as dest:
#     dest.write(mosaic)

# print("Merged raster saved")

# -----------------------------
# READ MERGED FEATURE STACK
# -----------------------------
# with rasterio.open("feature_stack.tif") as src:

#     bands = src.read()

#     rows = src.height
#     cols = src.width

#     transform = src.transform
#     crs = src.crs

# print("Raster shape:", bands.shape)

# # -----------------------------
# # CONVERT TO DATAFRAME
# # -----------------------------
# X = bands.reshape(
#     bands.shape[0],
#     -1
# ).T

# df = pd.DataFrame(
#     X,
#     columns=[
#         'NDVI',
#         'NDWI',
#         'elevation',
#         'slope',
#         'surface_runoff_sum',
#         'total_precipitation_sum',
#         'volumetric_soil_water_layer_1',
#         'temperature_2m',
#         'month',
#         'latitude',
#         'longitude',
#         'historical_flood_lga',
#         'high_risk_state'
#     ]
# )

# print("Feature Matrix Shape:", df.shape)

# # -----------------------------
# # HANDLE NAN VALUES
# # -----------------------------
# df = df.replace([np.inf, -np.inf], np.nan)
# df = df.fillna(0)

# # -----------------------------
# # PREDICT FLOOD RISK
# # -----------------------------
# pred = model.predict(df)

# print("Prediction Shape:", pred.shape)

# # -----------------------------
# # CONVERT BACK TO RASTER
# # -----------------------------
# flood_map = pred.reshape(rows, cols)

# # -----------------------------
# # SAVE PREDICTION RASTER
# # -----------------------------
# with rasterio.open(
#     "flood_prediction.tif",
#     "w",
#     driver="GTiff",
#     height=rows,
#     width=cols,
#     count=1,
#     dtype=flood_map.dtype,
#     crs=crs,
#     transform=transform
# ) as dst:

#     dst.write(flood_map, 1)

# print("Flood prediction raster saved")

# # -----------------------------
# # VISUALIZE
# # -----------------------------
# plt.figure(figsize=(14, 10))

# plt.imshow(
#     flood_map,
#     cmap="RdYlGn_r"
# )

# plt.colorbar(
#     label="Flood Risk"
# )

# plt.title(
#     "Flood Prediction Map"
# )

# plt.axis("off")

# plt.show()

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
# vis = {
#     'min': 0,
#     'max': 1,
#     'palette': ['green', 'yellow', 'orange', 'red']
# }

# Map.addLayer(prediction_img, vis, "Flood Risk Map")

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




# -----------------------------
# READ RASTER
# -----------------------------


# -----------------------------
# LOAD FLOOD PREDICTION RASTER
# -----------------------------
with rasterio.open("flood_prediction.tif") as src:

    flood = src.read(1)

    bounds = src.bounds

print("Flood map shape:", flood.shape)
print("Minimum:", flood.min())
print("Maximum:", flood.max())
print("Unique values:", np.unique(flood))

# -----------------------------
# NORMALIZE DATA
# -----------------------------
flood = flood.astype(np.float32)

if flood.max() != flood.min():

    normalized = (
        flood - flood.min()
    ) / (
        flood.max() - flood.min()
    )

else:
    normalized = np.zeros_like(flood)

# -----------------------------
# APPLY COLOR MAP
# -----------------------------
colored = cm.RdYlGn_r(normalized)

# Remove alpha channel
colored = colored[:, :, :3]

# Convert to uint8 image
colored = (colored * 255).astype(np.uint8)

# -----------------------------
# MAP CENTER
# -----------------------------
center_lat = (bounds.top + bounds.bottom) / 2
center_lon = (bounds.left + bounds.right) / 2

# -----------------------------
# CREATE MAP
# -----------------------------
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles="OpenStreetMap"
)

# -----------------------------
# ADD FLOOD OVERLAY
# -----------------------------
folium.raster_layers.ImageOverlay(
    image=colored,
    bounds=[
        [bounds.bottom, bounds.left],
        [bounds.top, bounds.right]
    ],
    opacity=0.75,
    interactive=True,
    cross_origin=False,
    zindex=1
).add_to(m)

# -----------------------------
# ADD ROI OUTLINE
# -----------------------------
folium.Rectangle(
    bounds=[
        [bounds.bottom, bounds.left],
        [bounds.top, bounds.right]
    ],
    fill=False
).add_to(m)

# -----------------------------
# SAVE MAP
# -----------------------------
m.save("flood_prediction_map.html")

print("✅ Interactive map saved:")
print("flood_prediction_map.html")

# -----------------------------
# OPTIONAL LOCAL PREVIEW
# -----------------------------
plt.figure(figsize=(10, 8))
plt.imshow(colored)
plt.title("Flood Prediction Raster")
plt.axis("off")
plt.show()

# Map.save("map.html")

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