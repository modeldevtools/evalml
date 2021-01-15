import pandas as pd

from evalml.pipelines.components.transformers.transformer import Transformer
from evalml.utils.gen_utils import (
    _convert_to_woodwork_structure,
    _convert_woodwork_types_wrapper
)


class DelayedFeatureTransformer(Transformer):
    """Transformer that delayes input features and target variable for time series problems."""
    name = "Delayed Feature Transformer"
    hyperparameter_ranges = {}
    needs_fitting = False

    def __init__(self, max_delay=2, delay_features=True, delay_target=True, gap=1,
                 random_state=0, **kwargs):
        """Creates a DelayedFeatureTransformer.

        Arguments:
            max_delay (int): Maximum number of time units to delay each feature.
            delay_features (bool): Whether to delay the input features.
            delay_target (bool): Whether to delay the target.
            gap (int): The number of time units between when the features are collected and
                when the target is collected. For example, if you are predicting the next time step's target, gap=1.
                This is only needed because when gap=0, we need to be sure to start the lagging of the target variable
                at 1.
            random_state (int, np.random.RandomState): Seed for the random number generator. There is no randomness
                in this transformer.
        """
        self.max_delay = max_delay
        self.delay_features = delay_features
        self.delay_target = delay_target

        # If 0, start at 1
        self.start_delay_for_target = int(gap == 0)

        parameters = {"max_delay": max_delay, "delay_target": delay_target, "delay_features": delay_features,
                      "gap": gap}
        parameters.update(kwargs)
        super().__init__(parameters=parameters, random_state=random_state)

    def fit(self, X, y=None):
        """Fits the DelayFeatureTransformer."""

    def transform(self, X, y=None):
        """Computes the delayed features for all features in X and y.

        For each feature in X, it will add a column to the output dataframe for each
        delay in the (inclusive) range [1, max_delay]. The values of each delayed feature are simply the original
        feature shifted forward in time by the delay amount. For example, a delay of 3 units means that the feature
        value at row n will be taken from the n-3rd row of that feature

        If y is not None, it will also compute the delayed values for the target variable.

        Arguments:
            X (ww.DataTable, pd.DataFrame or None): Data to transform. None is expected when only the target variable is being used.
            y (ww.DataColumn, pd.Series, or None): Target.

        Returns:
            ww.DataTable: Transformed X.
        """
        if X is None:
            X = pd.DataFrame()
        X = _convert_to_woodwork_structure(X)
        X = _convert_woodwork_types_wrapper(X.to_dataframe())
        if y is not None:
            y = _convert_to_woodwork_structure(y)
            y = _convert_woodwork_types_wrapper(y.to_series())

        if self.delay_features and not X.empty:
            X = X.assign(**{f"{col}_delay_{t}": X[col].shift(t)
                            for t in range(1, self.max_delay + 1)
                            for col in X})

        # Handle cases where the target was passed in
        if self.delay_target and y is not None:
            X = X.assign(**{f"target_delay_{t}": y.shift(t)
                            for t in range(self.start_delay_for_target, self.max_delay + 1)})

        return _convert_to_woodwork_structure(X)