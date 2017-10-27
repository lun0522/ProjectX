from sklearn.neighbors import NearestNeighbors
import numpy as np
import itertools
import dbHandler
from PIL import Image
import os
import math
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


def rotate_points(angle, points, scale_x=1.0, scale_y=1.0):
    # find the center of points
    points_array = np.array(points)
    center_x = np.average(points_array[:, 0])
    center_y = np.average(points_array[:, 1])

    # rotate each point about the center
    points_array[:, 0] -= center_x
    points_array[:, 1] -= center_y
    new_points = np.empty(shape=points_array.shape)
    new_points[:, 0] = scale_x*(points_array[:, 0]*math.cos(angle) + points_array[:, 1]*math.sin(angle) + center_x)
    new_points[:, 1] = scale_y*(points_array[:, 1]*math.cos(angle) - points_array[:, 0]*math.sin(angle) + center_y)

    return new_points.tolist()


def retrieve_painting(landmarks, face_image):
    # scale the face image
    width, height = 256, 256
    scaled_image = face_image.resize((width, height), Image.ANTIALIAS)

    # do affine transform to align the face
    angle = math.atan2(landmarks[45][1] - landmarks[36][1],
                       landmarks[45][0] - landmarks[36][0])
    rotated_landmarks = rotate_points(angle, landmarks, width/face_image.size[0], height/face_image.size[1])

    # https://stackoverflow.com/questions/17056209/python-pil-affine-transformation
    extremes = [(0, 0), (0, height - 1), (width - 1, 0), (width - 1, height - 1)]
    x_extremes = [ math.cos(angle)*x + math.sin(angle)*y for x, y in extremes]
    y_extremes = [-math.sin(angle)*x + math.cos(angle)*y for x, y in extremes]
    mnx = min(x_extremes)
    mxx = max(x_extremes)
    mny = min(y_extremes)
    mxy = max(y_extremes)
    inv_t = np.linalg.inv(np.matrix([[ math.cos(angle), math.sin(angle), -mnx],
                                     [-math.sin(angle), math.cos(angle), -mny],
                                     [0, 0, 1]]))
    scaled_image = scaled_image.transform((int(round(mxx - mnx)), int(round((mxy - mny)))),
                                          Image.AFFINE,
                                          (inv_t[0, 0], inv_t[0, 1], inv_t[0, 2],
                                           inv_t[1, 0], inv_t[1, 1], inv_t[1, 2]),
                                          Image.BILINEAR)
    scaled_image = scaled_image.crop(((scaled_image.size[0] - width )/2,
                                      (scaled_image.size[1] - height)/2,
                                      (scaled_image.size[0] + width )/2,
                                      (scaled_image.size[1] + height)/2))
    pixels = scaled_image.load()
    for x, y in rotated_landmarks:
        if 0 < x < width and 0 < y < height:
            pixels[x, y] = (0, 0, 255, 255)
    scaled_image.show()


if __name__ == "__main__":
    try:
        while True:
            num = input("Input a number: ")
            knn_search([train_data[int(num)]])

    except KeyboardInterrupt:
        print("")
        dbHandler.cleanup()
