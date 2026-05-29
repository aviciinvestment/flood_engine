import ee
import geemap

from gee.auth import initialize_ee
from gee.datasets import get_sentinel2
from gee.features import build_feature_stack, create_composite
from gee.visualization import create_map
from gee.flood_model import FloodModel

# -------------------
# 1. INIT SYSTEM
# -------------------
initialize_ee()

# -------------------
# 2. ROI (DRAW OR MANUAL)
# -------------------
Map = create_map()

roi = ee.Geometry.Rectangle([24.5, -2.5, 26.5, -1.0])

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
    "NDVI", "NDWI", "occurrence",
    "slope", "aspect",
    "longitude", "latitude"
])

# -------------------
# 5. LOAD MODEL
# -------------------
model = FloodModel("model.pkl")

# -------------------
# 6. RASTER FLOOD PREDICTION
# -------------------
flood_map = model.predict_raster(feature_stack)

# -------------------
# 7. VISUALIZATION
# -------------------
vis = {
    "min": 0,
    "max": 1,
    "palette": ["white", "yellow", "red"]
}

Map.addLayer(composite.select("NDVI"), {"min":0, "max":1}, "NDVI")
Map.addLayer(flood_map, vis, "Flood Risk Map")

Map.centerObject(roi, 10)

# -------------------
# 8. SHOW MAP
# -------------------
Map