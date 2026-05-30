import geemap
import ee
import matplotlib.pyplot as plt
from .auth import initialize_ee
from .datasets import pop_data

def create_map():
    m = geemap.Map(
        basemap="CyclOSM",
        zoom=3
    )
    return m


def add_layer(m, image, vis, name):
    m.addLayer(image, vis, name)
    return m



datas = None
class Analyze_ndvi_time_series:
    def __init__(self,geometry, start_date, end_date, median):
        self.geometry = geometry
        self.start_date = start_date
        self.end_date = end_date 
        self.median = median
        self.population = pop_data()

        initialize_ee()
    
    def add_ndvi_and_time(self, image):
        # Calculate NDVI
        ndvi = image.normalizedDifference(['B5', 'B4']).rename('NDVI')
        
        # Add time properties
        date = ee.Date(image.get('system:time_start'))
        years = date.difference(ee.Date('1970-01-01'), 'year')
        
        return (image.addBands(ndvi)
                    .set('date', date)
                    .set('year', date.get('year'))
                    .set('month', date.get('month'))
                    .set('day_of_year', date.getRelative('day', 'year'))
                    .set('decimal_year', years))
    
    def extract_ndvi_value(self, image):
        # Calculate mean NDVI over the geometry
        ndvi_mean = image.select('NDVI').reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry = self.geometry,
            scale=30,
            maxPixels=1e9
        )
        
        # Return feature with date and NDVI value
        return ee.Feature(None, {
            'date': image.get('date'),
            'decimal_year': image.get('decimal_year'),
            'ndvi': ndvi_mean.get('NDVI'),
            'year': image.get('year'),
            'month': image.get('month'),
            'day_of_year': image.get('day_of_year')
        })
    
    # Step 2 — add area calculation
    def add_area(self, feature):
        area = feature.geometry().area(maxError=1).divide(10000)  # hectares
        return feature.set('area_ha', area)
    
    # Step 3 — extract NDVI/NDWI + population values
    def extract_indices(self,feature):

        image_stack = self.median.select(['NDVI', 'NDWI']) \
            .addBands(self.population)

        stats = image_stack.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=feature.geometry(),
            scale=100,
            maxPixels=1e13
        )

        return feature.set({
            'ndvi_mean': stats.get('NDVI'),
            'ndwi_mean': stats.get('NDWI'),
            'population': stats.get('population',0)
        })
    

    
