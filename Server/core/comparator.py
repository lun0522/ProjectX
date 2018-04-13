from sklearn.neighbors import NearestNeighbors
import numpy as np


class Comparator(object):
    def __init__(self, train_data, neighbors):
        self.train_data = train_data
        self.neighbors = NearestNeighbors(metric=self.construct_metric([9.0, 5.0, 0.7, 9.3, 8.0, 10.0]),
                                          n_neighbors=neighbors).fit(train_data)

    def __call__(self, landmarks):
        return self.neighbors.kneighbors([landmarks], return_distance=False)[0]

    @staticmethod
    def construct_metric(weight):
        landmark_weight = sum([[weight[i]] * point_count
                               for i, point_count in enumerate([17, 10, 9, 12, 12, 8])], [])
        landmark_weight = np.array(landmark_weight * 2)

        def metric(x1, x2):
            return np.sqrt(np.sum(np.multiply(np.square(np.subtract(x1, x2)), landmark_weight)))

        return metric
