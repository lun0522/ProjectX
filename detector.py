import dlib
import os
import glob
import dbHandler
from skimage import io
import mysql.connector

predictor_path = "/Users/lun/Desktop/ProjectX/shape_predictor_68_face_landmarks.dat"

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(predictor_path)


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


def double_check(directory=dbHandler.paintings_dir):
    change_directory(directory)

    try:
        # check whether any image with no face is still stored in the disk
        for img_file in glob.glob("*.jpg"):
            title = dbHandler.filename_to_title(img_file)
            if not dbHandler.bbox_has_face(title):
                print("Has no face but is still in disk: {}".format(title))
                os.remove(img_file)

        print("Double check finished.")

    except mysql.connector.Error as err:
        print("Error in double check: {}".format(err.msg))


def detect(directory=dbHandler.paintings_dir, do_double_check=True):
    change_directory(directory)

    try:
        for img_file in glob.glob("*.jpg"):
            # some images are downloaded, but have invalid file size
            # those < 1KB will be deleted
            if os.path.getsize(img_file) < 1024:
                print("Invalid file size: {}".format(img_file))
                os.remove(img_file)
                continue

            # only process those haven't any record in the database
            title = dbHandler.filename_to_title(img_file)
            if not dbHandler.bbox_did_exist(title):
                img_data = io.imread(img_file)

                # da face detection
                faces = detect_face(img_data)

                # if no face, denote the title of image as "not having face"
                # and delete this image
                if not len(faces):
                    print("No face found in {}".format(title))
                    dbHandler.denote_no_face(title)
                    os.remove(img_file)

                # if any face is detected, store its bounding box
                else:
                    print("Found {face_count} face(s) in {img_title}".format(
                        face_count=len(faces), img_title=title))
                    for idx, bbox in enumerate(faces):
                        dbHandler.store_bounding_box(
                            title, bbox.left(), bbox.right(),
                            bbox.bottom(), bbox.top())

                        scale_x = 100.0 / (bbox.right() - bbox.left())
                        scale_y = 100.0 / (bbox.bottom() - bbox.top())
                        landmarks = detect_face_landmark(img_data, bbox, scale_x, scale_y)
                        dbHandler.store_landmarks(title, landmarks[17:])

        print("Detection finished.")

    except mysql.connector.Error as err:
        print("Error in MySQL: {}".format(err))

    # ensure to save all changes and do double check if necessary
    finally:
        if do_double_check:
            double_check(directory)

        dbHandler.commit_change()
        dbHandler.cleanup()


if __name__ == "__main__":
    detect()
