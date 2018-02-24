import dlib
import os
import glob
import dbHandler
from skimage import io
import mysql.connector
import shutil
import numpy as np

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(dbHandler.predictor_path)


def create_rect(xlo, ylo, xhi, yhi):
    return dlib.rectangle(xlo, ylo, xhi, yhi)


def detect_face(img):
    return [bbox for num, bbox in enumerate(detector(img, 1))]


def detect_landmarks(img, bbox):
    landmarks = np.array([[point.x, point.y] for point in predictor(img, bbox).parts()], dtype=np.float64).transpose()

    # only use coordinates of eyebrows, eyes and the inner lip
    for start, end in ([17, 22], [22, 27], [36, 42], [42, 48], [60, 68]):
        points = landmarks[:, start: end]
        # let the x coordinate of the leftmost point be 0
        # let the mean of y coordinates of all points be 0
        points -= np.array([points[0][0], np.mean(points[1, :])]).reshape(2, 1)
        # let the x coordinate of the rightmost point be 100.0
        # scale all y coordinates at the same time with the same ratio
        if start == 17 or start == 22:
            rightmost = points[0][4]
        elif start == 36 or start == 42:
            rightmost = points[0][3]
        else:
            rightmost = points[0][4]
        points *= 100.0 / rightmost

    landmarks = np.hstack((landmarks[:, 17: 27], landmarks[:, 36: 48], landmarks[:, 60: 68]))
    return np.hstack((landmarks[0, :], landmarks[1, :]))


def detect(directory=dbHandler.downloads_dir):
    if not os.path.exists(dbHandler.paintings_dir):
        os.makedirs(dbHandler.paintings_dir)
    os.chdir(directory)

    try:
        for img_file in sorted(glob.glob("*.jpg")):
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
                print("Found {} face(s) in {}".format(len(faces), title))
                url = dbHandler.retrieve_download_url(title)

                if url:
                    # i.e. row number in database
                    painting_id = dbHandler.store_painting_info(url)

                    # store painting id, landmarks points and bounding box for each face
                    for idx, bbox in enumerate(faces):
                        dbHandler.store_landmarks(painting_id, detect_landmarks(img_data, bbox).tolist(),
                                                  (bbox.left(), bbox.right(), bbox.bottom(), bbox.top()))

                    # move the image to paintings folder
                    shutil.move(directory + img_file, dbHandler.get_painting_filename(painting_id))

                # if no url, delete the image
                else:
                    print("No record in database: {}".format(img_file))
                    os.remove(img_file)

            # if no face, delete the image
            else:
                print("No face found in {}".format(title))
                os.remove(img_file)

            dbHandler.remove_redundant_info(title)

        print("Detection finished.")

    except mysql.connector.Error as err:
        print("Error in MySQL: {}".format(err))

    # ensure to save all changes and do double check if necessary
    finally:
        dbHandler.commit_change()
        dbHandler.cleanup()


if __name__ == "__main__":
    detect()
