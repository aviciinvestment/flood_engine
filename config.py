from datetime import date, timedelta, datetime
today = date.today().strftime('%Y-%m-%d')
two_weeks_ago = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')

PROJECT_ID = "global-standard-474515-c2"

START_DATE = F"{two_weeks_ago}"
END_DATE = f"{today}"

CLOUD_FILTER = 20

S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
S1_COLLECTION = "COPERNICUS/S1_GRD"

DEM = "USGS/SRTMGL1_003"
WATER_HISTORY = "JRC/GSW1_4/GlobalSurfaceWater"