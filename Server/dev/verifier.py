from sklearn.neighbors import NearestNeighbors
import numpy as np
from dev import testingDB
import mysql.connector
from skimage import io
from skimage.transform import resize
from core.detector import detect_face, detect_landmarks, create_rect
from core.comparator import metric
from icrawler.builtin import GoogleImageCrawler
import os
import glob
import shutil


def crawl_image(keyword, capacity, directory):
    tmp_dir = os.path.join(directory, "tmp")
    if os.path.exists(tmp_dir):
        print("Tmp directory already exists")
        return
    os.makedirs(tmp_dir)

    google_crawler = GoogleImageCrawler(storage={"root_dir": tmp_dir})
    google_crawler.crawl(keyword=keyword, max_num=capacity)

    files = glob.glob(os.path.join(tmp_dir, "*.jp*g"))
    total, processed = len(files), 0

    for img_file in files:
        try:
            processed += 1

            img_data = io.imread(img_file)
            if len(img_data.shape) != 3:
                print("Not supported format: " + img_file)
                continue

            faces = detect_face(img_data)
            if not len(faces) or len(faces) > 1:
                print("No face / Too many faces: " + img_file)
                continue

            cropped = img_data[max(faces[0].top(), 0): min(faces[0].bottom(), img_data.shape[0]),
                               max(faces[0].left(), 0): min(faces[0].right(), img_data.shape[1])]
            if cropped.shape[0] < 128:
                print("Face too small: " + img_file)
                continue
            elif cropped.shape[0] > 256:
                cropped = resize(cropped, [256, 256, cropped.shape[2]])
            io.imsave(os.path.join(directory, str(processed).zfill(3) + ".jpg"), cropped)

            print("Processed ({}/{})".format(processed, total))

        except RuntimeError as err:
            print("Failed to process {}".format(img_file))
            print("Reason: {}".format(err))

    shutil.rmtree(tmp_dir)


def build_database(directory=testingDB.dataset_dir):
    try:
        for emotion, emotion_id in zip(testingDB.emotions, range(len(testingDB.emotions))):
            print("Processing {}...".format(emotion))

            files = glob.glob(os.path.join(os.path.join(directory, emotion), "*.jpg"))
            total, processed = len(files), 0
            branch = [[name, int(count)] for name, count in
                      zip(["Pool", "Validation", "Testing", "Training"],
                          [total * i for i in [0.5, 0.1, 0.1, 0.3]])]

            def get_database_branch():
                branch[-1][1] -= 1
                branch_name = branch[-1][0]
                if not branch[-1][1] and len(branch) > 1:
                    branch.pop()
                return branch_name

            for img_file in files:
                processed += 1
                img_data = io.imread(img_file)
                landmarks = detect_landmarks(img_data, create_rect(0, 0, img_data.shape[1], img_data.shape[0]))
                testingDB.store_landmarks(get_database_branch(), emotion_id, landmarks.tolist())

                print("Processed ({}/{})".format(processed, total))

    except mysql.connector.Error as err:
        print("Error in MySQL: {}".format(err))

    finally:
        testingDB.commit_change()
        testingDB.cleanup()


def verify_model():
    pool = testingDB.get_landmarks("Pool")
    landmarks_pool = np.array([row[2] for row in pool])

    neighbors = NearestNeighbors(metric=metric, n_neighbors=1).fit(landmarks_pool)
    validation = testingDB.get_landmarks("Validation")
    total, processed, match = len(validation), 0, 0

    for _, emotion_id, points in validation:
        processed += 1
        log = "Processed ({}/{})".format(processed, total)

        match_id = neighbors.kneighbors([points], return_distance=False)[0][0]
        if emotion_id == pool[match_id][1]:
            match += 1
            print(log + "Hit")
        else:
            print(log + "Miss")

    print("Accuracy: {:.2f}%".format(match / total * 100.0))


if __name__ == "__main__":
    verify_model()
