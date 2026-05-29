import ee
from config import *

def get_sentinel2(roi):
    return (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(roi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_FILTER))
    )

def get_sentinel1(roi):
    return (
        ee.ImageCollection(S1_COLLECTION)
        .filterBounds(roi)
        .filterDate(START_DATE, END_DATE)
    )

def get_dem():
    return ee.Image(DEM)

def get_water_history():
    return ee.Image(WATER_HISTORY).select("occurrence")