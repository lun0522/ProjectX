from sklearn.neighbors import NearestNeighbors
import numpy as np

# ("landmark name", (start_index, end_index (exclusive)), weight)
landmark_map = [
    ("faceContour",  ( 0, 17), ( 0, 16)),
    ("leftEyebrow",  (17, 22), (17, 21)),
    ("rightEyebrow", (22, 27), (22, 26)),
    ("nose",         (27, 36), (31, 35)),
    ("leftEye",      (36, 42), (36, 39)),
    ("rightEye",     (42, 48), (42, 45)),
    ("outerLip",     (48, 60), (48, 54)),
    ("innerLip",     (60, 68), (60, 64)),
]
landmark_weight = [1.0] * 17 + [10.0] * 10 + [1.0] * 9 + [5.0] * 12 + [1.0] * 12 + [5.0] * 8
landmark_weight = np.array(landmark_weight * 2)


def metric(x1, x2):
    return np.sqrt(np.sum(np.multiply(np.square(np.subtract(x1, x2)), landmark_weight)))


class Comparator(object):
    def __init__(self, train_data, neighbors):
        self.train_data = train_data
        self.neighbors = NearestNeighbors(metric=metric, n_neighbors=neighbors).fit(train_data)

    def __call__(self, landmarks):
        return [(self.train_data[idx][0], self.train_data[idx][1])
                for idx in self.neighbors.kneighbors([landmarks], return_distance=False)[0]]
