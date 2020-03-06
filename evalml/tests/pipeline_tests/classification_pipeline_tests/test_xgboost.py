import category_encoders as ce
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier as SKRandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from evalml.objectives import PrecisionMicro
from evalml.pipelines import XGBoostBinaryPipeline, XGBoostMulticlassPipeline
from evalml.utils import import_or_raise


def test_xg_init(X_y):
    X, y = X_y

    clf = XGBoostBinaryPipeline(eta=0.2, min_child_weight=3, max_depth=5, impute_strategy='median',
                                percent_features=1.0, number_features=len(X[0]), n_estimators=10, random_state=1)
    expected_parameters = {'impute_strategy': 'median', 'percent_features': 1.0, 'threshold': -np.inf,
                           'eta': 0.2, 'max_depth': 5, 'min_child_weight': 3, 'n_estimators': 10}
    assert clf.parameters == expected_parameters
    assert clf.random_state == 1


def test_xg_multi(X_y_multi):
    X, y = X_y_multi

    xgb = import_or_raise("xgboost")
    imputer = SimpleImputer(strategy='mean')
    enc = ce.OneHotEncoder(use_cat_names=True, return_df=True)
    estimator = xgb.XGBClassifier(random_state=0,
                                  eta=0.1,
                                  max_depth=3,
                                  min_child_weight=1,
                                  n_estimators=10)
    rf_estimator = SKRandomForestClassifier(random_state=0, n_estimators=10, max_depth=3)
    feature_selection = SelectFromModel(estimator=rf_estimator,
                                        max_features=max(1, int(1 * len(X[0]))),
                                        threshold=-np.inf)
    sk_pipeline = Pipeline([("encoder", enc),
                            ("imputer", imputer),
                            ("feature_selection", feature_selection),
                            ("estimator", estimator)])
    sk_pipeline.fit(X, y)
    sk_score = sk_pipeline.score(X, y)

    objective = PrecisionMicro()
    clf = XGBoostMulticlassPipeline(eta=0.1, min_child_weight=1, max_depth=3, impute_strategy='mean', percent_features=1.0, number_features=len(X[0]), n_estimators=10)
    clf.fit(X, y)
    clf_scores = clf.score(X, y, [objective])
    y_pred = clf.predict(X)

    assert((y_pred == sk_pipeline.predict(X)).all())
    assert (sk_score == clf_scores[objective.name])
    assert len(np.unique(y_pred)) == 3
    assert len(clf.feature_importances) == len(X[0])
    assert not clf.feature_importances.isnull().all().all()

    # testing objective parameter passed in does not change results
    clf.fit(X, y, objective)
    y_pred_with_objective = clf.predict(X)
    assert((y_pred == y_pred_with_objective).all())


def test_xg_input_feature_names(X_y):
    X, y = X_y
    # create a list of column names
    col_names = ["col_{}".format(i) for i in range(len(X[0]))]
    X = pd.DataFrame(X, columns=col_names)
    objective = PrecisionMicro()
    clf = XGBoostBinaryPipeline(eta=0.1, min_child_weight=1, max_depth=3, impute_strategy='mean', percent_features=1.0, number_features=len(X.columns), n_estimators=10)
    clf.fit(X, y, objective)
    assert len(clf.feature_importances) == len(X.columns)
    assert not clf.feature_importances.isnull().all().all()
    for col_name in clf.feature_importances["feature"]:
        assert "col_" in col_name