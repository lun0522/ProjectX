from sklearn.neighbors import NearestNeighbors
import numpy as np
from dev import testingDB
import mysql.connector
from skimage import io
from core.detector import detect_face, detect_landmarks
from core.comparator import metric
import os
import glob


def build_database(directory):
    try:
        files = glob.glob(os.path.join(directory, "*.jpg"))
        total, processed = len(files), 0
        branch = list(zip(["Pool", "Validation", "Testing", "Training"],
                          [total * i for i in [0.5, 0.1, 0.1, 0.3]]))

        def get_database_branch():
            branch[-1][1] -= 1
            branch_name = branch[-1][0]
            if not branch[-1][1]:
                branch.pop()
            return branch_name

        for img_file in files:
            processed += 1
            img_data = io.imread(img_file)
            faces = detect_face(img_data)

            if not len(faces):
                print("No face found in " + img_file)
                continue

            # TODO: read emotion id from somewhere
            testingDB.store_landmarks(get_database_branch(), 0,
                                      detect_landmarks(img_data, faces[0]).tolist())
            print("Processed ({}/{})".format(processed, total))

    except mysql.connector.Error as err:
        print("Error in MySQL: {}".format(err))

    finally:
        testingDB.commit_change()
        testingDB.cleanup()


def verify():
    pool = testingDB.get_landmarks("Pool")
    landmarks_pool = np.array([row[2] for row in pool])
    neighbors = NearestNeighbors(metric=metric, n_neighbors=1).fit(landmarks_pool)

    validation = testingDB.get_landmarks("Validation")
    total, correct = len(validation), 0
    for _, emotion_id, points in validation:
        match_id = neighbors.kneighbors([points], return_distance=False)[0][0]
        if emotion_id == pool[match_id][1]:
            correct += 1
        else:
            print("Wrong match: {} -> {}".format(emotion_id, pool[match_id][1]))

    print("Accuracy: {.2f}%".format(correct / total * 100.0))


if __name__ == "__main__":
    verify()
