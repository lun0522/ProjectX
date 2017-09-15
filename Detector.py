import dlib
import os, glob
import DBHandler
from skimage import io
import mysql.connector

default_directory = "/Users/lun/Desktop/ProjectX/paintings/"
detector = dlib.get_frontal_face_detector()


def detect_face(img):
    bbox_list = detector(img, 1)
    return [bbox for num, bbox in enumerate(bbox_list)]


def detect(directory=default_directory):
    # specify directory where stores paintings
    if not os.path.exists(directory):
        print("Wrong directory!")
        exit(0)
    os.chdir(directory)

    try:
        for img_file in glob.glob("*.jpg"):
            # only process those haven't any record in the database
            title = img_file[0:-4].replace("-", " ")
            if not DBHandler.bbox_did_exist(title):
                img_data = io.imread(img_file)

                # da face detection
                faces = detect_face(img_data)

                # if no face, denote the title of image as "not having face"
                # and delete this image
                if not len(faces):
                    print("No face in {}".format(title))
                    DBHandler.denote_no_face(title)
                    os.remove(img_file)

                # if any face is detected, store its bounding box
                else:
                    print("Found {face_count} face(s) in {img_title}".format(
                        face_count=len(faces), img_title=title))
                    for idx, bbox in enumerate(faces):
                        DBHandler.store_bounding_box(
                            title, bbox.left(), bbox.right(),
                            bbox.bottom(), bbox.top())

    except mysql.connector.Error as err:
        print("Error in MySQL: {}".format(err))

    # ensure to save all changes
    finally:
        DBHandler.commit_change()


if __name__ == "__main__":
    detect()
