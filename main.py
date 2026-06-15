import ee
import geemap
import pandas as pd
import geopandas as gpd
import shapely.geometry as sg
import matplotlib.pyplot as plt
from datetime import datetime

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
Analyze = Analyze_ndvi_time_series(roi, START_DATE, END_DATE, composite)

ndvi_collection = collection.map(Analyze.add_ndvi_and_time)

time_series = ndvi_collection.map(Analyze.extract_ndvi_value)

time_series_list = time_series.getInfo()['features']

df_data = []

for feature in time_series_list:
    props = feature['properties']
    if props['ndvi'] is not None:
        df_data.append({
            'date': datetime.fromtimestamp(props['date']['value'] / 1000),
            'decimal_year': props['decimal_year'],
            'ndvi': props['ndvi'],
            'year': props['year'],
            'month': props['month'],
            'day_of_year': props['day_of_year']
        })

ndvi_df = pd.DataFrame(df_data)
ndvi_df = ndvi_df.sort_values('date')

stats = {
    'mean_ndvi': ndvi_df['ndvi'].mean(),
    'std_ndvi': ndvi_df['ndvi'].std(),
    'min_ndvi': ndvi_df['ndvi'].min(),
    'max_ndvi': ndvi_df['ndvi'].max(),
    'data_points': len(ndvi_df)
}

def plot_time_series(df, stats, title="NDVI Time Series"):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    ax1.plot(df['date'], df['ndvi'], 'o-', linewidth=1, markersize=3)
    ax1.set_title(f"{title}\nMean: {stats['mean_ndvi']:.3f}")
    ax1.grid(True)

    monthly_mean = df.groupby(df['date'].dt.month)['ndvi'].mean()
    ax2.bar(monthly_mean.index, monthly_mean.values, color='green')
    ax2.set_title("Monthly NDVI")

    plt.tight_layout()
    plt.show()

# -------------------
# 6. POPULATION DATA
# -------------------
population = pop_data()

farms = ee.FeatureCollection([ee.Feature(roi, {'name': 'Study Area'})])

farms = farms.map(Analyze.add_area)
farms_with_stats = farms.map(Analyze.extract_indices)

results = farms_with_stats.getInfo()['features']

data_summary = pd.DataFrame([f['properties'] for f in results])

print(data_summary)

# -------------------
# FINAL OUTPUT
# -------------------
plot_time_series(ndvi_df, stats, "NDVI Time Series")