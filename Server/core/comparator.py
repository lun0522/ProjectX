from sklearn.neighbors import NearestNeighbors
from dev.verifier import Verifier


class Comparator(object):
    def __init__(self, train_data, neighbors):
        self.train_data = train_data
        self.neighbors = NearestNeighbors(metric=Verifier.construct_metric([9.0, 5.0, 0.7, 9.3, 8.0, 10.0]),
                                          n_neighbors=neighbors).fit(train_data)

    def __call__(self, landmarks):
        return self.neighbors.kneighbors([landmarks], return_distance=False)[0]
