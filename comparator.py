from sklearn.neighbors import NearestNeighbors
import numpy as np
import itertools
import dbHandler
from PIL import Image
import os
import time

# "landmark name": (start_index, index_range, weight)
landmark_map = {
    "eyebrow"     : ( 0, 10, 1),
    "noseCrest"   : (10,  4, 1),
    "nose"        : (14,  5, 1),
    "eye"         : (19, 12, 1),
    "lips"        : (31, 20, 1),
}


def euclidean_dist(x1, x2):
    return np.sqrt(np.sum(np.square(np.array(x1) - np.array(x2))))


def metric(x1, x2):
    return np.sum([euclidean_dist(x1[start_index * 2: (start_index + index_range) * 2],
                                  x2[start_index * 2: (start_index + index_range) * 2]) * weight
                   for landmark, (start_index, index_range, weight) in landmark_map.items()])


landmarks = dbHandler.get_all_landmarks()
# form an 1-D array of coordinates for each face
train_data = np.array([list(itertools.chain.from_iterable(points))
                       for points in [row[1] for row in landmarks]])
# specify the metric to use and number of neighbors to retrieve
neighbors = NearestNeighbors(metric="euclidean", n_neighbors=5).fit(train_data)


def knn_search(target):
    os.chdir(dbHandler.paintings_dir)
    start = time.time()
    distances, indices = neighbors.kneighbors(target)
    print("time: {:.3f}s".format(time.time() - start))
    for idx in indices[0]:
        if os.path.exists(landmarks[idx][0]):
            img = Image.open(landmarks[idx][0])
            img.show()
        else:
            print("Not exists: {}".format(landmarks[idx][0]))


if __name__ == "__main__":
    try:
        while True:
            num = input("Input a number: ")
            knn_search([train_data[int(num)]])

    except KeyboardInterrupt:
        dbHandler.cleanup()
