from sklearn.neighbors import NearestNeighbors
import numpy as np
from dev import testingDB
import mysql.connector
from skimage import io
from skimage.transform import resize
from core.detector import detect_face, detect_landmarks, create_rect
from icrawler.builtin import GoogleImageCrawler
import os
import glob
import shutil
from multiprocessing import Manager


def examine(params):
    try:
        verifier, weight, count, total = params
        match_rate = verifier.verify_model(verifier.construct_metric(weight), False)
        count.value += 1
        print("({}/{}) {} -> {:.2f}%".format(count.value, total, weight, match_rate * 100.0))
        return weight, match_rate

    except KeyboardInterrupt:
        pass


class Verifier(object):
    def __init__(self):
        pool = testingDB.get_landmarks("Pool")
        self.emotions_pool = [row[1] for row in pool]
        self.landmarks_pool = np.array([row[2] for row in pool])
        self.training = testingDB.get_landmarks("Training")

    @staticmethod
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

    @staticmethod
    def build_database(directory=testingDB.dataset_dir):
        try:
            copied = 0
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
                    bounding_box = create_rect(0, 0, img_data.shape[1], img_data.shape[0])
                    landmarks = detect_landmarks(img_data, bounding_box)[1].tolist()
                    testingDB.store_landmarks(get_database_branch(), emotion_id, landmarks)

                    copied += 1
                    testingDB.store_landmarks("Total", emotion_id, landmarks)
                    shutil.copy(img_file, os.path.join(os.path.join(directory, "total"),
                                                       str(copied).zfill(5) + ".jpg"))

                    print("Processed ({}/{})".format(processed, total))

        except mysql.connector.Error as err:
            print("Error in MySQL: {}".format(err))

        finally:
            testingDB.commit_change()
            testingDB.cleanup()

    def verify_model(self, metric, verbose=True):
        neighbors = NearestNeighbors(metric=metric, n_neighbors=1).fit(self.landmarks_pool)
        total, processed, match = len(self.training), 0, 0

        for _, emotion_id, points in self.training:
            processed += 1
            match_id = neighbors.kneighbors([points], return_distance=False)[0][0]
            if emotion_id == self.emotions_pool[match_id]:
                match += 1
                if verbose:
                    print("Processed ({}/{})".format(processed, total) + "Hit")
            else:
                if verbose:
                    print("Processed ({}/{})".format(processed, total) + "Miss")

        if verbose:
            print("Accuracy: {:.2f}%".format(match / total * 100.0))
        return match / total

    @staticmethod
    def construct_metric(weight):
        landmark_weight = sum([[weight[i]] * point_count
                               for i, point_count in enumerate([17, 10, 9, 12, 12, 8])], [])
        landmark_weight = np.array(landmark_weight * 2)

        def metric(x1, x2):
            return np.sqrt(np.sum(np.multiply(np.square(np.subtract(x1, x2)), landmark_weight)))

        return metric

    def exhaustive_search(self, batch_size=20):
        pool = Manager().Pool()
        count = Manager().Value("d", 0)
        highest_match = 0.0
        best_weight = None

        searching = True
        while searching:
            try:
                count.value = 0
                weight = np.random.rand(batch_size, 6)
                for weight, match_rate in pool.map(examine, [(self, weight[i], count, batch_size)
                                                             for i in range(batch_size)]):
                    if match_rate > highest_match:
                        highest_match = match_rate
                        best_weight = weight

                print(">>> Best weight: {} -> {:.2f}%".format(best_weight, highest_match * 100.0))

            except KeyboardInterrupt:
                searching = False


if __name__ == "__main__":
    Verifier.build_database()
