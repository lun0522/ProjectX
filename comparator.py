from sklearn.neighbors import NearestNeighbors as NN
import numpy as np
import dbHandler


def compare(x, y):
    return np.sqrt(np.square(x[0] - y[0]) + np.square(x[1] - y[1]))


X = np.array([[-1, -1], [-2, -1], [-3, -2], [1, 1], [2, 1], [3, 2]])
neighbors = NN(n_neighbors=2, metric=compare).fit(X)
distances, indices = neighbors.kneighbors(X)
print(distances)
print(indices)
