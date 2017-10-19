from sklearn.neighbors import NearestNeighbors as NN
import numpy as np
import dbHandler


def compare(x, y):
    return np.sqrt(np.square(x[0] - y[0]) + np.square(x[1] - y[1]))


all_landmarks = np.array(dbHandler.get_all_landmarks())
neighbors = NN(n_neighbors=2, metric=compare).fit(all_landmarks)
distances, indices = neighbors.kneighbors(all_landmarks)

print(distances)
print(indices)
