import json
import os

from .baseDB import DatabaseHandler

__all__ = ["ModelDatabaseHandler"]

"""
mysql> use model

mysql> DESCRIBE Total;
+--------------+---------+------+-----+---------+----------------+
| Field        | Type    | Null | Key | Default | Extra          |
+--------------+---------+------+-----+---------+----------------+
| id           | int(11) | NO   | PRI | NULL    | auto_increment |
| emotion_id   | int(11) | NO   |     | NULL    |                |
| points       | json    | NO   |     | NULL    |                |
| points_posed | json    | NO   |     | NULL    |                |
+--------------+---------+------+-----+---------+----------------+
"""

dataset_dir = "/Users/lun/Desktop/ProjectX/dataset"
emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
emotions_dir = [os.path.join(dataset_dir, emotion) for emotion in emotions]

query_landmarks = "SELECT * FROM {}"

insert_landmark = " ".join(("INSERT INTO {}",
                            "(emotion_id, points, points_posed)",
                            "VALUES (%s, %s, %s)"))


class ModelDatabaseHandler(DatabaseHandler):
    def __init__(self):
        super().__init__("model")

    def get_landmarks(self, branch):
        self.cursor.execute(query_landmarks.format(branch))
        return [(landmark_id, emotion_id, json.loads(points), json.loads(points_posed))
                for landmark_id, emotion_id, points, points_posed in self.cursor]

    def store_landmarks(self, branch, emotion_id, points, points_posed):
        self.cursor.execute(insert_landmark.format(branch),
                            (emotion_id, json.dumps(points), json.dumps(points_posed)))
        return self.cursor.lastrowid
