import dlib
import os, glob
import dbHandler
from skimage import io
import mysql.connector

default_directory = "/Users/lun/Desktop/ProjectX/paintings/"
detector = dlib.get_frontal_face_detector()


def change_directory(directory=default_directory):
    # specify directory where stores paintings
    if not os.path.exists(directory):
        print("Wrong directory!")
        exit(0)
    os.chdir(directory)


def detect_face(img):
    bbox_list = detector(img, 1)
    return [bbox for num, bbox in enumerate(bbox_list)]


def double_check(directory=default_directory):
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


def detect(directory=default_directory, do_double_check=True):
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

        print("Detection finished.")
        dbHandler.cleanup()

    except mysql.connector.Error as err:
        print("Error in MySQL: {}".format(err))

    # ensure to save all changes and do double check if necessary
    finally:
        dbHandler.commit_change()
        if do_double_check:
            double_check(directory)


if __name__ == "__main__":
    detect()
