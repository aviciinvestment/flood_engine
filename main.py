import ee
import geemap
import pandas as pd

from gee.auth import initialize_ee
from gee.datasets import get_sentinel2,pop_data
from gee.features import build_feature_stack, create_composite
from gee.visualization import create_map, Analyze_ndvi_time_series
from gee.flood_model import FloodModel
from config import *
import matplotlib.pyplot as plt

# -------------------
# 1. INIT SYSTEM
# -------------------
initialize_ee()

# -------------------
# 2. ROI (DRAW OR MANUAL)
# -------------------
Map = create_map()

roi = ee.Geometry.Polygon([[-228.087384, -33.032017], [-228.087384, -31.189639], [-225.023073, -31.189639], [-225.023073, -33.032017], [-228.087384, -33.032017]])
coords = roi.coordinates().getInfo()
print(coords)
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
    'NDVI','NDWI','occurrence', 'aspect', 'longitude', 'latitude'
])


samples = feature_stack.sample(
    region=roi,
    scale=5,
    numPixels=5000,
    geometries=True
)





samples_dict = samples.getInfo()

rows = []

for feature in samples_dict['features']:
    rows.append(feature['properties'])

df = pd.DataFrame(rows)

print(df)



df = df.rename(columns={
    'longitude': 'lon',
    'latitude': 'lat',
    'occurrence': 'jrc_perm_water'
})

df = df[[
    'lon',
    'lat',
    'jrc_perm_water',
    'NDVI',
    'NDWI',
    'aspect'
]]
# -------------------
# 5. LOAD MODEL
# -------------------
model = FloodModel("model.pkl")

# -------------------
# 6. RASTER FLOOD PREDICTION
# -------------------
flood_map = model.predict_dataframe(df)


print(pd.DataFrame(flood_map))


# NDVI visualization
ndvi_vis = {
    'bands': ['NDVI'],
    'min': -0.2,
    'max': 0.8,
    'palette': ['blue', 'white', 'green']
}

# Water index visualization
ndwi_vis = {
    'bands': ['NDWI'],
    'min': -0.3,
    'max': 0.5,
    'palette': ['white', 'blue']
}


Map.addLayer(feature_stack.select('NDVI'), ndvi_vis, 'NDVI')
Map.addLayer(feature_stack.select('NDWI'), ndwi_vis, 'NDWI')
Map.centerObject(roi, zoom=10)


Map
Map.save("map.html")

# -------------------
# 7. VISUALIZATION

# -------------------
Analyze_ndvi_time_series = Analyze_ndvi_time_series(roi, START_DATE, END_DATE, composite)

# Apply NDVI calculation to collection
ndvi_collection = collection.map(Analyze_ndvi_time_series.add_ndvi_and_time)

    # Extract time series data
time_series = ndvi_collection.map(Analyze_ndvi_time_series.extract_ndvi_value)

# Convert to pandas DataFrame for analysis
time_series_list = time_series.getInfo()['features']
df_data = []


for feature in time_series_list:
    props = feature['properties']
    if props['ndvi'] is not None:  # Filter out null values
        df_data.append({
            'date': datetime.fromtimestamp(props['date']['value'] / 1000),
            'decimal_year': props['decimal_year'],
            'ndvi': props['ndvi'],
            'year': props['year'],
            'month': props['month'],
            'day_of_year': props['day_of_year']
        })

df = pd.DataFrame(df_data)
df = df.sort_values('date')
datas = df.copy()

# Calculate statistics
stats = {
    'mean_ndvi': df['ndvi'].mean(),
    'std_ndvi': df['ndvi'].std(),
    'min_ndvi': df['ndvi'].min(),
    'max_ndvi': df['ndvi'].max(),
    'data_points': len(df)
}


def plot_time_series(df, stats, title="NDVI Time Series"):
    """
    Create time series plot with trend analysis.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Main time series plot
    ax1.plot(df['date'], df['ndvi'], 'o-', linewidth=1, markersize=3, alpha=0.7)
    ax1.set_title(f"{title}\nMean: {stats['mean_ndvi']:.3f} ± {stats['std_ndvi']:.3f}")
    ax1.set_xlabel('Date')
    ax1.set_ylabel('NDVI')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=stats['mean_ndvi'], color='r', linestyle='--', alpha=0.5, label='Mean')
    ax1.legend()
    
    # Monthly aggregation
    monthly_mean = df.groupby(df['date'].dt.month)['ndvi'].mean()
    ax2.bar(monthly_mean.index, monthly_mean.values, alpha=0.7, color='green')
    ax2.set_title('Monthly Average NDVI')
    ax2.set_xlabel('Month')
    ax2.set_ylabel('Mean NDVI')
    ax2.set_xticks(range(1, 13))
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    return fig

print(f"Analyzing NDVI time series from {two_weeks_ago} to {today}")
print("This may take a few minutes...")
    

    
# Print results
print("\n📊 Time Series Analysis Results:")
print(f"Data points: {stats['data_points']}")
print(f"Mean NDVI: {stats['mean_ndvi']:.3f}")
print(f"Standard deviation: {stats['std_ndvi']:.3f}")
print(f"Range: {stats['min_ndvi']:.3f} to {stats['max_ndvi']:.3f}")


 
# Seasonal analysis
print("\n🌱 Seasonal Analysis:")
seasonal_stats = df.groupby(df['date'].dt.month)['ndvi'].agg(['mean', 'std', 'count'])
print(seasonal_stats)
    
print("\n✅ Time series analysis completed successfully!")

print(datas)


# ------------------------------------------
# Population / Demography dataset
# ------------------------------------------
population =pop_data()

# Step 1 — your roi as a proper FeatureCollection
farms = ee.FeatureCollection([
    ee.Feature(roi, {'name': 'Study Farm'})
])



farms = farms.map(Analyze_ndvi_time_series.add_area)



farms_with_stats = farms.map(Analyze_ndvi_time_series.extract_indices)

# Step 4 — convert to pandas
results = farms_with_stats.getInfo()['features']
print(results)

data_summary= pd.DataFrame([
     f['properties'] for f in results
 ])

print(data_summary)

 
# Create visualization
plot_time_series(df, stats, "Agricultural Area NDVI Time Series")