from types import SimpleNamespace

import numpy as np
import pandas as pd

from ml.clusters import relabel


def test_relabel_numbers_clusters_by_median_growth_highest_first():
    km = SimpleNamespace(labels_=np.array([0, 0, 1, 1, 2, 2]))
    now = pd.DataFrame({"price_growth": [-3.0, -1.0, 5.0, 7.0, 1.0, 2.0]})
    # medians: raw 0 = -2, raw 1 = 6, raw 2 = 1.5
    assert relabel(km, now) == {1: 0, 2: 1, 0: 2}
