import json

from .baseDB import DatabaseHandler

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


class ModelDatabaseHandler(DatabaseHandler):

    query_landmarks = "SELECT * FROM {}"

    insert_landmark = " ".join(("INSERT INTO {}",
                                "(emotion_id, points, points_posed)",
                                "VALUES (%s, %s, %s)"))

    def __init__(self):
        super().__init__("model")

    def get_landmarks(self, branch):
        self.cursor.execute(self.query_landmarks.format(branch))
        return [(landmark_id, emotion_id, json.loads(points), json.loads(points_posed))
                for landmark_id, emotion_id, points, points_posed in self.cursor]

    def store_landmarks(self, branch, emotion_id, points, points_posed):
        self.cursor.execute(self.insert_landmark.format(branch),
                            (emotion_id, json.dumps(points), json.dumps(points_posed)))
        return self.cursor.lastrowid
