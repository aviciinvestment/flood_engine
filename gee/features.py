import ee
from .datasets import *

def add_features(img):

    # -------------------------
    # Spectral Features
    # -------------------------
    ndvi = img.normalizedDifference(
        ["B8", "B4"]
    ).rename("NDVI")

    ndwi = img.normalizedDifference(
        ["B3", "B8"]
    ).rename("NDWI")

    # -------------------------
    # Terrain Features
    # -------------------------
    dem = ee.Image("USGS/SRTMGL1_003")

    elevation = dem.rename("elevation")

    slope = ee.Terrain.slope(
        dem
    ).rename("slope")

    # -------------------------
    # Climate Features
    # -------------------------
    date = ee.Date(img.get("system:time_start"))

    era5 = (
        ee.ImageCollection(
            "ECMWF/ERA5_LAND/DAILY_AGGR"
        )
        .filterDate(
            date.advance(-15, "day"),
            date.advance(15, "day")
        )
        .mean()
    )

    surface_runoff_sum = era5.select(
        "surface_runoff_sum"
    )

    total_precipitation_sum = era5.select(
        "total_precipitation_sum"
    )

    volumetric_soil_water_layer_1 = era5.select(
        "volumetric_soil_water_layer_1"
    )

    temperature_2m = era5.select(
        "temperature_2m"
    )

    # -------------------------
    # Month Feature
    # -------------------------
    month = ee.Image.constant(
        date.get("month")
    ).rename("month")

    # -------------------------
    # Coordinates
    # -------------------------
    latlon = ee.Image.pixelLonLat()

    latitude = latlon.select(
        "latitude"
    ).rename("latitude")

    longitude = latlon.select(
        "longitude"
    ).rename("longitude")

    # -------------------------
    # Historical Flood Layer
    # -------------------------
    historical_flood_lga = ee.Image.constant(0).rename("historical_flood_lga")

    high_risk_state = ee.Image.constant(0).rename("high_risk_state")
    

    # -------------------------
    # Add Everything
    # -------------------------
    return img.addBands([
        ndvi,
        ndwi,
        elevation,
        slope,
        surface_runoff_sum,
        total_precipitation_sum,
        volumetric_soil_water_layer_1,
        temperature_2m,
        month,
        latitude,
        longitude,
        historical_flood_lga,
        high_risk_state
    ])


def build_feature_stack(collection):
    return collection.map(add_features)


def create_composite(collection):
    return collection.median()

