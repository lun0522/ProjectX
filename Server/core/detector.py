import dlib
import os
import glob
from core import paintingDB
from skimage import io
import mysql.connector
import shutil
import numpy as np


# ("landmark name", (start_index, end_index (exclusive)), weight)
landmark_map = [
    ("faceContour",  ( 0, 17), ( 0, 16)),
    ("leftEyebrow",  (17, 22), (17, 21)),
    ("rightEyebrow", (22, 27), (22, 26)),
    ("nose",         (27, 36), (31, 35)),
    ("leftEye",      (36, 42), (36, 39)),
    ("rightEye",     (42, 48), (42, 45)),
    ("outerLip",     (48, 60), (48, 54)),
    ("innerLip",     (60, 68), (60, 64)),
]
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(paintingDB.predictor_path)


def create_rect(xlo, ylo, xhi, yhi):
    return dlib.rectangle(xlo, ylo, xhi, yhi)


def break_rect(rect):
    return [rect.left(), rect.top(), rect.right(), rect.bottom()]


def detect_face(img):
    return [bbox for num, bbox in enumerate(detector(img, 1))]


def normalize_landmarks(landmarks):
    landmarks = np.array(landmarks, dtype=np.float64).transpose()
    for _, (start, end), (left, right) in landmark_map:
        leftmost, rightmost = left - start, right - start
        points = landmarks[:, start: end]
        # let the x coordinate of the leftmost point be 0.0
        # let the mean of y coordinates of all points be 0.0
        points -= np.array([points[0][leftmost], np.mean(points[1, :])]).reshape(2, 1)
        # let the x coordinate of the rightmost point be 2.0
        # scale all y coordinates at the same time with the same ratio
        points *= 2.0 / points[0][rightmost]
        # let the x coordinate of the leftmost point be -1.0, and that of the rightmost be 1.0
        points[0, :] -= 1.0

    return np.hstack((landmarks[0, :], landmarks[1, :]))


def detect_landmarks(img, bbox):
    landmarks = [[point.x, point.y] for point in predictor(img, bbox).parts()]
    return landmarks, normalize_landmarks(landmarks)


def detect(directory=paintingDB.downloads_dir):
    if not os.path.exists(paintingDB.paintings_dir):
        os.makedirs(paintingDB.paintings_dir)
    if not os.path.exists(paintingDB.faces_dir):
        os.makedirs(paintingDB.faces_dir)
    os.chdir(directory)

    try:
        files = glob.glob("*.jpg")
        total, processed = len(files), 0

        for img_file in sorted(files):
            processed += 1

            # some images are downloaded, but have invalid file size
            # those < 10KB will be deleted, but the url will be preserved in the Download table
            if os.path.getsize(img_file) < 10240:
                print("Invalid file size: {}".format(img_file))
                os.remove(img_file)
                continue

            title = img_file[:-4]
            img_data = io.imread(img_file)

            # do face detection
            faces = detect_face(img_data)

            # if any face is detected, store its bounding box
            # and do face landmark detection
            if len(faces):
                print("({}/{}) Found {} face(s) in {}".format(processed, total, len(faces), title))
                url = paintingDB.retrieve_download_url(title)

                if url:
                    # i.e. row number in database
                    painting_id = paintingDB.store_painting_info(url)

                    # store painting id, landmarks points and bounding box for each face
                    # also crop down and save the face part
                    for idx, bbox in enumerate(faces):
                        face_id = paintingDB.store_landmarks(
                            detect_landmarks(img_data, bbox)[1].tolist(),
                            painting_id, break_rect(bbox))

                        face_width, face_height = bbox.right() - bbox.left(), bbox.bottom() - bbox.top()
                        cropped = img_data[max(bbox.top() - face_height // 2, 0):
                                           min(bbox.bottom() + face_height // 2, img_data.shape[0]),
                                           max(bbox.left() - face_width // 2, 0):
                                           min(bbox.right() + face_width // 2, img_data.shape[1])]
                        io.imsave(paintingDB.get_face_filename(face_id), cropped)

                    # move the image to paintings folder
                    shutil.move(directory + img_file, paintingDB.get_painting_filename(painting_id))

                # if no url, delete the image
                else:
                    print("No url record in database: {}".format(img_file))
                    os.remove(img_file)

            # if no face, delete the image
            else:
                print("No face found in {}".format(title))
                os.remove(img_file)

            paintingDB.remove_redundant_info(title)

        print("Detection finished.")

    except mysql.connector.Error as err:
        print("Error in MySQL: {}".format(err))

    # ensure to save all changes and do double check if necessary
    finally:
        paintingDB.commit_change()
        paintingDB.cleanup()


if __name__ == "__main__":
    detect()
