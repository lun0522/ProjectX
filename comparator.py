from sklearn.neighbors import NearestNeighbors
import numpy as np
import itertools
import dbHandler
from PIL import Image
import os
import time
import math

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
    return np.sum([euclidean_dist(x1[start_index*2: (start_index + index_range)*2],
                                  x2[start_index*2: (start_index + index_range)*2])*weight
                   for landmark, (start_index, index_range, weight) in landmark_map.items()])


all_landmarks = dbHandler.get_all_landmarks()
# form an 1-D array of coordinates for each face
train_data = np.array([list(itertools.chain.from_iterable(points))
                       for points in [row[1] for row in all_landmarks]])
# specify the metric to use and number of neighbors to retrieve
neighbors = NearestNeighbors(metric="euclidean", n_neighbors=5).fit(train_data)


def knn_search(target):
    os.chdir(dbHandler.paintings_dir)
    start = time.time()
    distances, indices = neighbors.kneighbors(target)
    print("time: {:.3f}s".format(time.time() - start))
    for idx in indices[0]:
        if os.path.exists(all_landmarks[idx][0]):
            img = Image.open(all_landmarks[idx][0])
            img.show()
        else:
            print("Not exists: {}".format(all_landmarks[idx][0]))


def rotate_x(angle, x, y):
    return math.cos(angle)*x + math.sin(angle)*y


def rotate_y(angle, x, y):
    return -math.sin(angle)*x + math.cos(angle)*y


def rotate_point(angle, center, point):
    x = point[0] - center[0]
    y = point[1] - center[1]
    new_x = x*math.cos(angle) - y*math.sin(angle)
    new_y = y*math.cos(angle) + x*math.sin(angle)
    return new_x + center[0], new_y + center[1]


def tilt_points(angle, points):
    # find the center of points
    center = [0.0, 0.0]
    for (x, y) in points:
        center[0] += x
        center[1] += y
    center[0] /= len(points)
    center[1] /= len(points)

    # rotate each point about the center
    return [rotate_point(angle, center, point) for point in points]


def retrieve_painting(landmarks, face_image):
    # scale the face image
    width, height = 256, 256
    scaled_image = face_image.resize((width, height), Image.ANTIALIAS)

    # do affine transform to align the face
    # https://stackoverflow.com/questions/17056209/python-pil-affine-transformation
    angle = math.pi / 2 + math.atan2(landmarks[27][1] - landmarks[30][1], landmarks[27][0] - landmarks[30][0])
    x_extremes = [rotate_x(angle, 0, 0), rotate_x(angle, 0, height - 1),
                  rotate_x(angle, width - 1, 0), rotate_x(angle, width - 1, height - 1)]
    y_extremes = [rotate_y(angle, 0, 0), rotate_y(angle, 0, height - 1),
                  rotate_y(angle, width - 1, 0), rotate_y(angle, width - 1, height - 1)]
    mnx = min(x_extremes)
    mxx = max(x_extremes)
    mny = min(y_extremes)
    mxy = max(y_extremes)
    inv_t = np.linalg.inv(np.matrix([[math.cos(angle), math.sin(angle), -mnx],
                                     [-math.sin(angle), math.cos(angle), -mny],
                                     [0, 0, 1]]))
    scaled_image = scaled_image.transform((int(round(mxx - mnx)), int(round((mxy - mny)))),
                                          Image.AFFINE,
                                          (inv_t[0, 0], inv_t[0, 1], inv_t[0, 2],
                                           inv_t[1, 0], inv_t[1, 1], inv_t[1, 2]),
                                          Image.BILINEAR)
    scaled_image = scaled_image.crop(((scaled_image.size[0] - width)/2,
                                      (scaled_image.size[1] - height)/2,
                                      (scaled_image.size[0] + width)/2,
                                      (scaled_image.size[1] + height)/2))
    scaled_image.show()


if __name__ == "__main__":
    try:
        while True:
            num = input("Input a number: ")
            knn_search([train_data[int(num)]])

    except KeyboardInterrupt:
        print("")
        dbHandler.cleanup()
