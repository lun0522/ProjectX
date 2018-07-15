import os
import glob
import shutil
from multiprocessing import Manager

import numpy as np
from sklearn.neighbors import NearestNeighbors
from skimage import io
from skimage.transform import resize
from icrawler.builtin import GoogleImageCrawler
from mysql.connector import Error as sqlError
from sklearn.svm import SVC
from sklearn.externals import joblib

from core import detector
from core.comparator import Comparator
from database import paintingDB
from database.modelDB import dataset_dir, emotions, ModelDatabaseHandler


def examine(params):
    try:
        trainer, weight, neighbors, processed, total = params
        match_rate = trainer.verify_model(Comparator.construct_metric(weight),
                                          neighbors=neighbors, verbose=False)
        processed.value += 1
        print("({}/{}) {} -> {:.2f}%".format(processed.value, total, weight, match_rate * 100.0))
        return weight, match_rate

    except KeyboardInterrupt:
        pass


class Trainer(object):
    def __init__(self, pool_branch="Pool", training_branch="Training"):
        db_handler = ModelDatabaseHandler()
        pool = db_handler.get_landmarks(pool_branch)
        self.emotions_pool = np.array([row[1] for row in pool])
        self.landmarks_pool = np.array([row[3] for row in pool])
        training = db_handler.get_landmarks(training_branch)
        self.emotions_training = [row[1] for row in training]
        self.landmarks_training = np.array([row[3] for row in training])

    @staticmethod
    def crawl_image(keyword, capacity, directory):
        tmp_dir = os.path.join(directory, "tmp")
        if os.path.exists(tmp_dir):
            print("Tmp directory already exists")
            exit(-1)
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

                faces = detector.detect_face(img_data)
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
                io.imsave(os.path.join(directory, str(processed).zfill(5) + ".jpg"), cropped)

                print("Processed ({}/{})".format(processed, total))

            except RuntimeError as err:
                print("Failed to process {}".format(img_file))
                print("Reason: {}".format(err))

        shutil.rmtree(tmp_dir)

    @staticmethod
    def build_database(directory=dataset_dir):
        total_dir = os.path.join(directory, "total")
        if os.path.exists(total_dir):
            print("Total directory already exists")
            exit(-1)
        os.makedirs(total_dir)

        db_handler = ModelDatabaseHandler()
        try:
            copied = 0
            for emotion, emotion_id in zip(emotions, range(len(emotions))):
                print("Processing {}...".format(emotion))

                files = glob.glob(os.path.join(os.path.join(directory, emotion), "*.jpg"))
                total, processed = len(files), 0
                branch = [[name, int(count)] for name, count in
                          zip(["Training", "Test"], [total * i for i in [0.8, 0.2]])]

                def get_database_branch():
                    branch[-1][1] -= 1
                    branch_name = branch[-1][0]
                    if not branch[-1][1] and len(branch) > 1:
                        branch.pop()
                    return branch_name

                for img_file in files:
                    processed += 1
                    img_data = io.imread(img_file)
                    bounding_box = detector.create_rect(0, 0, img_data.shape[1], img_data.shape[0])
                    landmarks = detector.detect_landmarks(img_data, bounding_box)
                    normalized = detector.normalize_landmarks(landmarks).tolist()
                    posed = detector.pose_landmarks(landmarks).tolist()

                    copied += 1
                    db_handler.store_landmarks(get_database_branch(), emotion_id, normalized, posed)
                    db_handler.store_landmarks("Total", emotion_id, normalized, posed)
                    # shutil.copy(img_file, os.path.join(total_dir, str(copied).zfill(5) + ".jpg"))

                    print("Processed ({}/{})".format(processed, total))

        except sqlError as err:
            print("Error in MySQL: {}".format(err))

        finally:
            db_handler.commit_change()

    def verify_model(self, metric, neighbors=1, verbose=True):
        neighbors = NearestNeighbors(metric=metric, n_neighbors=neighbors).fit(self.landmarks_pool)
        total, processed, match = len(self.emotions_training), 0, 0

        for emotion_id, points_posed in zip(self.emotions_training, self.landmarks_training):
            processed += 1
            match_id = neighbors.kneighbors([points_posed], return_distance=False)[0]
            match_emotions = self.emotions_pool[match_id].tolist()
            if emotion_id == max(match_emotions, key=match_emotions.count):
                match += 1
                if verbose:
                    print("Processed ({}/{})".format(processed, total) + "Hit")
            else:
                if verbose:
                    print("Processed ({}/{})".format(processed, total) + "Miss")

        if verbose:
            print("Accuracy: {:.2f}%".format(match / total * 100.0))
        return match / total

    def exhaustive_search(self, neighbors=1, batch_size=20):
        pool = Manager().Pool()
        counter = Manager().Value("d", 0)
        best_weight, highest_match = None, 0.0

        searching = True
        while searching:
            try:
                counter.value = 0
                weights = np.random.rand(batch_size, 6)
                results = pool.map(examine, [(self, weights[i], neighbors, counter, batch_size)
                                             for i in range(batch_size)])
                index = np.argmax(np.array([row[1] for row in results]))
                if results[index][1] > highest_match:
                    best_weight, highest_match = results[index]

                print(">>> Best weight: {} -> {:.2f}%".format(best_weight, highest_match * 100.0))

            except KeyboardInterrupt:
                searching = False


def train_svm(directory=paintingDB.svm_dir):
    db_handler = ModelDatabaseHandler()
    training_pool = db_handler.get_landmarks("Training")
    test_pool = db_handler.get_landmarks("Test")

    def generate_train_data():
        np.random.shuffle(training_pool)
        label = np.array([row[1] for row in training_pool])
        data = np.array([row[3] for row in training_pool])
        return data, label

    test_label = np.array([row[1] for row in test_pool])
    test_data = np.array([row[3] for row in test_pool])

    svm = SVC(kernel='linear', probability=True, tol=1e-3)
    training_data, training_label = generate_train_data()
    svm.fit(training_data, training_label)

    accuracy = svm.score(test_data, test_label)
    print("Accuracy: {}%".format(accuracy * 100))

    joblib.dump(svm, directory)


if __name__ == "__main__":
    Trainer.build_database()
