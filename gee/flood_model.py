import joblib
import ee

class FloodModel:
    def __init__(self, model_path="model.pkl"):
        self.model = joblib.load(model_path)

    def predict_dataframe(self, df):
        return self.model.predict(df)

    def predict_raster(self, feature_image):
        """
        Converts ML model into raster prediction
        """
        return feature_image.classify(self.model)