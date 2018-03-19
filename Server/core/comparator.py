from sklearn.neighbors import NearestNeighbors
import numpy as np
from core.paintingDB import get_all_landmarks

# ("landmark name", (start_index, end_index (exclusive)), weight)
landmark_map = [
    ("faceContour",  ( 0, 17), ( 0, 16), 1.0),
    ("leftEyebrow",  (17, 22), (17, 21), 2.0),
    ("rightEyebrow", (22, 27), (22, 26), 2.0),
    ("nose",         (27, 36), (31, 35), 1.0),
    ("leftEye",      (36, 42), (36, 39), 1.0),
    ("rightEye",     (42, 48), (42, 45), 1.0),
    ("outerLip",     (48, 60), (48, 54), 1.0),
    ("innerLip",     (60, 68), (60, 64), 4.0),
]


def euclidean_dist(x1, y1, x2, y2):
    return np.sqrt(np.sum((np.square(np.subtract(x1, x2)),
                           np.square(np.subtract(y1, y2))), axis=1))


def metric(a1, a2):
    return np.sum([weight * np.sum(euclidean_dist(
        a1[start_index: end_index], a1[start_index + 30: end_index + 30],
        a2[start_index: end_index], a2[start_index + 30: end_index + 30]))
                   for landmark, (start_index, end_index), weight in landmark_map])


all_landmarks = get_all_landmarks()
train_data = np.array([row[2] for row in all_landmarks])
neighbors = NearestNeighbors(metric=metric, n_neighbors=3).fit(train_data)


def retrieve_painting(landmarks):
    return [(all_landmarks[idx][0], all_landmarks[idx][1])
            for idx in neighbors.kneighbors([landmarks], return_distance=False)[0]]
