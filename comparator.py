from sklearn.neighbors import NearestNeighbors
import numpy as np
import itertools
import dbHandler
from PIL import Image
import os
import time

# "landmark name": (start_index, index_range, weight)
landmark_map = {
    "leftEyebrow" : ( 0,  5, 1),
    "rightEyebrow": ( 5,  5, 1),
    "noseCrest"   : (10,  4, 1),
    "nose"        : (14,  5, 1),
    "leftEye"     : (19,  6, 1),
    "rightEye"    : (25,  6, 1),
    "outerLips"   : (31, 12, 1),
    "innerLips"   : (43,  8, 1),
}


def euclidean_dist(x1, x2):
    return np.sqrt(np.sum(np.square(np.array(x1) - np.array(x2))))


def metric(x1, x2):
    return np.sum([euclidean_dist(x1[start_index: start_index + index_range],
                                  x2[start_index: start_index + index_range]) * weight
                   for landmark, (start_index, index_range, weight) in landmark_map.items()])


landmarks = dbHandler.get_all_landmarks()
# form an 1-D array of coordinates for each face
train_data = np.array([list(itertools.chain.from_iterable(points))
                       for points in [row[1] for row in landmarks]])
# specify the metric to use and number of neighbors to retrieve
neighbors = NearestNeighbors(metric="euclidean", n_neighbors=5).fit(train_data)

os.chdir("/Users/lun/Desktop/ProjectX/paintings/")

try:
    while True:
        num = input("Input a number: ")
        start = time.time()
        distances, indices = neighbors.kneighbors([train_data[int(num)]])
        print("time: {:.3f}s".format(time.time() - start))
        for idx in indices[0]:
            if os.path.exists(landmarks[idx][0]):
                img = Image.open(landmarks[idx][0])
                img.show()

except KeyboardInterrupt:
    pass
