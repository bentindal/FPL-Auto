import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

POSITIONS = ['GK', 'DEF', 'MID', 'FWD']


def _build_model(model_type: str, position: str):
    """Build a base model (before Pipeline wrapping)."""
    if model_type == 'linear':
        return LinearRegression()
    if model_type == 'randomforest':
        return RandomForestRegressor(oob_score=True, n_estimators=1000, max_features=100)
    if model_type == 'neuralnetwork':
        return MLPRegressor(hidden_layer_sizes=(100, 100, 100, 100))
    if model_type == 'gradientboost':
        max_features = {'GK': 5, 'DEF': 10, 'MID': 20, 'FWD': 10}[position]
        return GradientBoostingRegressor(
            criterion='squared_error', n_estimators=110,
            learning_rate=0.1, max_depth=3, max_features=max_features,
        )
    raise ValueError(f'Unknown model type: {model_type!r}')


def _build_pipeline(model_type: str, position: str) -> Pipeline:
    """Build a Pipeline with StandardScaler + model.

    The StandardScaler fits only on the training fold to prevent preprocessing leakage.
    During cross-validation, the scaler is refit for each fold using only that fold's
    training data, then applied to the test fold.
    """
    base_model = _build_model(model_type, position)
    return Pipeline([
        ('scaler', StandardScaler()),
        ('regressor', base_model)
    ])


class Predictor:
    """Trains and stores one sklearn Pipeline per position, pluggable by model_type.

    Each Pipeline wraps a StandardScaler + regressor to prevent preprocessing leakage.
    The scaler fits only on each fold's training data during CV and cross-validation.
    """

    TYPES = ('gradientboost', 'linear', 'randomforest', 'neuralnetwork')

    def __init__(self, model_type: str = 'gradientboost'):
        if model_type not in self.TYPES:
            raise ValueError(f'model_type must be one of {self.TYPES}')
        self.model_type = model_type
        self.models: list = []

    def fit(self, training_data: list) -> 'Predictor':
        """Fit one Pipeline per position. training_data is [(X_train, y_train) x4].

        Each Pipeline's StandardScaler fits on the training data, then both scaler
        and regressor are fitted together. This maintains backward compatibility:
        the external API is unchanged, but preprocessing leakage is prevented.
        """
        self.models = [
            _build_pipeline(self.model_type, pos).fit(X, y)
            for (X, y), pos in zip(training_data, POSITIONS)
        ]
        return self

    def predict(self, features: list) -> list:
        """Return rounded predictions for each position.

        Pipeline.predict() automatically applies StandardScaler then calls
        the regressor's predict method, so behavior is identical to pre-Pipeline code.
        """
        return [
            np.round(model.predict(X), 2)
            for model, X in zip(self.models, features)
        ]

    def predict_test(self, test_data: list) -> list:
        """Predict on test data, returning 5-decimal precision."""
        return [
            np.round(model.predict(X), 5)
            for model, (X, _) in zip(self.models, test_data)
        ]

    def feature_importances(self) -> list:
        """Extract feature importances from each Pipeline's regressor.

        Linear models do not have feature_importances_, so None is returned for them.
        This is handled gracefully by evaluate.py (skip display if None).
        """
        return [
            getattr(m.named_steps['regressor'], 'feature_importances_', None)
            for m in self.models
        ]

    def to_dataframes(self, player_names: list, predictions: list) -> list:
        """Zip names + predictions into a list of DataFrames (one per position)."""
        frames = []
        for names, preds in zip(player_names, predictions):
            df = pd.DataFrame({'Name': names, 'xP': preds}).set_index('Name')
            frames.append(df)
        return frames
