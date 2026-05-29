import ee
from .datasets import *

def add_features(img):
    # NDVI
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")

    # NDWI
    ndwi = img.normalizedDifference(["B3", "B8"]).rename("NDWI")

    # DEM + terrain
    dem = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(dem).rename("slope")
    aspect = ee.Terrain.aspect(dem).rename("aspect")

    # Water history
    water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")

    # Lat/Lon
    latlon = ee.Image.pixelLonLat()

    return img.addBands([
        ndvi,
        ndwi,
        slope,
        aspect,
        water,
        latlon
    ])


def build_feature_stack(collection):
    return collection.map(add_features)


def create_composite(collection):
    return collection.median()