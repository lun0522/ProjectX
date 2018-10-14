import json
import os.path

from . import paintings_dir, faces_dir
from .baseDB import DatabaseHandler

__all__ = ["PaintingDatabaseHandler"]

"""
mysql> use paintings

mysql> DESCRIBE Painting;
+-------+---------------+------+-----+---------+----------------+
| Field | Type          | Null | Key | Default | Extra          |
+-------+---------------+------+-----+---------+----------------+
| id    | int(11)       | NO   | PRI | NULL    | auto_increment |
| url   | varchar(2083) | NO   |     | NULL    |                |
+-------+---------------+------+-----+---------+----------------+

mysql> DESCRIBE Landmark;
+--------------+---------+------+-----+---------+----------------+
| Field        | Type    | Null | Key | Default | Extra          |
+--------------+---------+------+-----+---------+----------------+
| id           | int(11) | NO   | PRI | NULL    | auto_increment |
| painting_id  | int(11) | NO   | MUL | NULL    |                |
| bbox         | json    | NO   |     | NULL    |                |
| points       | json    | NO   |     | NULL    |                |
| points_posed | json    | NO   |     | NULL    |                |
+--------------+---------+------+-----+---------+----------------+
"""

_query_painting = " ".join(("SELECT id",
                            "FROM Painting",
                            "WHERE title=%s"))

_insert_painting = " ".join(("INSERT INTO Painting",
                             "(url)",
                             "VALUES (%s)"))

_insert_landmark = " ".join(("INSERT INTO Landmark",
                             "(painting_id, bbox, points, points_posed)",
                             "VALUES (%s, %s, %s, %s)"))

_update_landmark = " ".join(("UPDATE Landmark",
                             "SET emotion_id=%s",
                             "WHERE id=%s"))

_query_landmarks = " ".join(("SELECT id, painting_id, emotion_id, bbox, points, points_posed",
                             "FROM Landmark"))


class PaintingDatabaseHandler(DatabaseHandler):
    def __init__(self):
        super().__init__("paintings")

    @staticmethod
    def get_painting_filename(index):
        return os.path.join(paintings_dir, str(index).zfill(5) + ".jpg")

    @staticmethod
    def get_face_filename(index):
        return os.path.join(faces_dir, str(index).zfill(5) + ".jpg")

    def did_not_download(self, title):
        self.cursor.execute(_query_painting, (title,))
        return not self.cursor.rowcount

    def store_painting_info(self, url):
        self.cursor.execute(_insert_painting, (url,))
        return self.cursor.lastrowid

    def store_landmarks(self, landmarks, landmarks_posed, painting_id, bounding_box):
        self.cursor.execute(_insert_landmark, (painting_id, json.dumps(bounding_box),
                                               json.dumps(landmarks), json.dumps(landmarks_posed)))
        return self.cursor.lastrowid

    def update_emotion(self, landmark_id, emotion_id):
        self.cursor.execute(_update_landmark, (emotion_id, landmark_id))

    def get_all_landmarks(self):
        self.cursor.execute(_query_landmarks)
        return [(lid, pid, eid, json.loads(bbox), json.loads(points), json.loads(points_posed))
                for lid, pid, eid, bbox, points, points_posed in self.cursor]
