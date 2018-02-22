import dlib
import os
import glob
import dbHandler
from skimage import io
import mysql.connector
import shutil

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(dbHandler.predictor_path)


def change_directory(directory=dbHandler.paintings_dir):
    # specify directory where stores paintings
    if not os.path.exists(directory):
        print("Wrong directory!")
        exit(0)
    os.chdir(directory)


def detect_face(img):
    return [bbox for num, bbox in enumerate(detector(img, 1))]


def create_rect(xlo, ylo, xhi, yhi):
    return dlib.rectangle(xlo, ylo, xhi, yhi)


def detect_face_landmark(img, bbox, scale_x=1.0, scale_y=1.0):
    return [((point.x - bbox.left()) * scale_x,
             (point.y - bbox.top()) * scale_y)
            for point in predictor(img, bbox).parts()]


def detect(directory=dbHandler.downloads_dir):
    if not os.path.exists(dbHandler.paintings_dir):
        os.makedirs(dbHandler.paintings_dir)
    change_directory(directory)

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
                    painting_id = dbHandler.store_painting_info(url)

                    for idx, bbox in enumerate(faces):
                        scale_x = 100.0/(bbox.right() - bbox.left())
                        scale_y = 100.0/(bbox.bottom() - bbox.top())
                        landmarks = detect_face_landmark(img_data, bbox, scale_x, scale_y)
                        dbHandler.store_landmarks(painting_id, landmarks[17:],
                                                  (bbox.left(), bbox.right(),
                                                   bbox.bottom(), bbox.top()))

                    # move the image to paintings folder
                    shutil.move(directory + img_file, dbHandler.get_painting_filename(painting_id))

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
