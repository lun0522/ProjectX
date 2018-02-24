from sklearn.neighbors import NearestNeighbors
import numpy as np
from dbHandler import get_all_landmarks

# ("landmark name", (start_index, end_index (exclusive)), weight)
landmark_map = [
    ("leftEyebrow", (0, 5), 1.0),
    ("rightEyebrow", (5, 10), 1.0),
    ("leftEye", (10, 16), 1.0),
    ("rightEye", (16, 22), 1.0),
    ("innerLip", (22, 30), 4.0),
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
