import joblib
import ee

class FloodModel:
    def __init__(self, model_path="model.pkl"):
        self.model = joblib.load(model_path)

    def predict_dataframe(self, df):
        return self.model.predict(df)
