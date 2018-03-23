from sklearn.neighbors import NearestNeighbors
import numpy as np

# ("landmark name", (start_index, end_index (exclusive)), weight)
landmark_map = [
    ("faceContour",  ( 0, 17), ( 0, 16), 1.0),
    ("leftEyebrow",  (17, 22), (17, 21), 3.0),
    ("rightEyebrow", (22, 27), (22, 26), 3.0),
    ("nose",         (27, 36), (31, 35), 3.0),
    ("leftEye",      (36, 42), (36, 39), 7.0),
    ("rightEye",     (42, 48), (42, 45), 7.0),
    ("outerLip",     (48, 60), (48, 54), 1.0),
    ("innerLip",     (60, 68), (60, 64), 7.0),
]


def euclidean_dist(x1, y1, x2, y2):
    return np.sqrt(np.sum((np.square(np.subtract(x1, x2)),
                           np.square(np.subtract(y1, y2))), axis=1))


def metric(a1, a2):
    return np.sum([weight * np.sum(euclidean_dist(
        a1[start_index: end_index], a1[start_index + 68: end_index + 68],
        a2[start_index: end_index], a2[start_index + 68: end_index + 68]))
                   for _, (start_index, end_index), _, weight in landmark_map])


class Comparator(object):
    def __init__(self, train_data, neighbors):
        self.train_data = train_data
        self.neighbors = NearestNeighbors(metric=metric, n_neighbors=neighbors).fit(train_data)

    def __call__(self, landmarks):
        return [(self.train_data[idx][0], self.train_data[idx][1])
                for idx in self.neighbors.kneighbors([landmarks], return_distance=False)[0]]
