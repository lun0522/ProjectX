from sklearn.neighbors import NearestNeighbors
import numpy as np
from dev import testingDB
import mysql.connector
from skimage import io
from core.detector import detect_face, detect_landmarks
from core.comparator import metric
import os
import glob


def build_database(directory=testingDB.dataset_dir):
    try:
        for emotion, emotion_id in zip(testingDB.emotions, range(len(testingDB.emotions))):
            print("Processing {}...".format(emotion))

            files = glob.glob(os.path.join(os.path.join(directory, emotion), "*.jp*g"))
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
                try:
                    processed += 1
                    img_data = io.imread(img_file)
                    faces = detect_face(img_data)

                    if not len(faces) or len(faces) > 1:
                        print("No face / Too many faces found in " + img_file)
                        continue

                    testingDB.store_landmarks(get_database_branch(), emotion_id,
                                              detect_landmarks(img_data, faces[0]).tolist())
                    print("Processed ({}/{})".format(processed, total))

                except RuntimeError as err:
                    print("Failed to process {}".format(img_file))
                    print("Reason: {}".format(err))

    except mysql.connector.Error as err:
        print("Error in MySQL: {}".format(err))

    finally:
        testingDB.commit_change()
        testingDB.cleanup()


def verify():
    pool = testingDB.get_landmarks("Pool")
    landmarks_pool = np.array([row[2] for row in pool])
    neighbors = NearestNeighbors(metric=metric, n_neighbors=3).fit(landmarks_pool)

    validation = testingDB.get_landmarks("Validation")
    total, processed, correct = len(validation), 0, 0

    for _, emotion_id, points in validation:
        match_id = neighbors.kneighbors([points], return_distance=False)[0]
        processed += 1

        log = "Processed ({}/{})".format(processed, total)
        if emotion_id in [pool[eid][1] for eid in match_id]:
            correct += 1
            print(log + "Correct match")
        else:
            print(log + "Wrong match: {} -> {}".format(testingDB.emotions[emotion_id],
                                                       testingDB.emotions[pool[match_id[0]][1]]))

    print("Accuracy: {:.2f}%".format(correct / total * 100.0))


if __name__ == "__main__":
    verify()
