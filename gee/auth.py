import ee
from config import PROJECT_ID

def initialize_ee():
    try:
        ee.Authenticate()
        ee.Initialize(
            project=PROJECT_ID,
            opt_url="https://earthengine-highvolume.googleapis.com"
        )
        print("✔ Earth Engine Initialized")
    except Exception as e:
        print("❌ EE Init Failed:", e)
        raise