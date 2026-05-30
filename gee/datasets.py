import ee

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def pop_data():
    return (
    ee.ImageCollection("WorldPop/GP/100m/pop") \
    .filterDate(f'{START_DATE}', f'{END_DATE}') \
    .mean() \
    .rename('population')
    )

def get_dem():
    return ee.Image(DEM)

def get_water_history():
    return ee.Image(WATER_HISTORY).select("occurrence")

