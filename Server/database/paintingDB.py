import json

from .baseDB import DatabaseHandler

__all__ = ["PaintingDatabaseHandler"]

"""
mysql> use paintings

mysql> DESCRIBE Download;
+-------+---------------+------+-----+---------+-------+
| Field | Type          | Null | Key | Default | Extra |
+-------+---------------+------+-----+---------+-------+
| id    | int(11)       | NO   | PRI | NULL    |       |
| url   | varchar(2083) | NO   |     | NULL    |       |
| bbox  | json          | YES  |     | NULL    |       |
+-------+---------------+------+-----+---------+-------+

mysql> DESCRIBE Painting;
+-------+---------------+------+-----+---------+-------+
| Field | Type          | Null | Key | Default | Extra |
+-------+---------------+------+-----+---------+-------+
| id    | int(11)       | NO   | PRI | NULL    |       |
| url   | varchar(2083) | NO   |     | NULL    |       |
| bbox  | json          | NO   |     | NULL    |       |
+-------+---------------+------+-----+---------+-------+

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


class PaintingDatabaseHandler(DatabaseHandler):

    _insert_download = " ".join(("INSERT INTO Download",
                                 "(id, url)",
                                 "VALUES (%s, %s)"))

    _update_download = " ".join(("UPDATE Download",
                                 "SET bbox=%s",
                                 "WHERE id=%s"))

    _query_download = " ".join(("SELECT url, bbox",
                                "FROM Download",
                                "WHERE id=%s"))

    _insert_painting = " ".join(("INSERT INTO Painting",
                                 "(id, url, bbox)",
                                 "VALUES (%s, %s, %s)"))

    _insert_landmark = " ".join(("INSERT INTO Landmark",
                                 "(painting_id, bbox, points, points_posed)",
                                 "VALUES (%s, %s, %s, %s)"))

    _query_all_landmarks = " ".join(("SELECT id, painting_id, bbox, points, points_posed",
                                     "FROM Landmark"))

    def __init__(self):
        super().__init__("paintings")

    def did_download(self, index):
        self.cursor.execute(self._query_download, (int(index),))
        return self.cursor.rowcount

    def store_download(self, index, url):
        self.cursor.execute(self._insert_download, (int(index), url))
        return self.cursor.rowcount

    def update_bounding_box(self, index, bounding_box):
        self.cursor.execute(self._update_download, (json.dumps(bounding_box), int(index)))

    def store_painting(self, index):
        self.cursor.execute(self._query_download, (int(index),))
        url, bounding_box = self.cursor[0]
        self.cursor.execute(self._insert_painting, (int(index), url, bounding_box))
        return json.loads(bounding_box)

    def store_landmarks(self, painting_id, bounding_box, landmarks, landmarks_posed):
        self.cursor.execute(self._insert_landmark,
                            (int(painting_id), json.dumps(bounding_box),
                             json.dumps(landmarks), json.dumps(landmarks_posed)))
        return self.cursor.lastrowid

    def get_all_landmarks(self):
        self.cursor.execute(self._query_all_landmarks)
        return [(lid, pid, json.loads(bbox), json.loads(points), json.loads(points_posed))
                for lid, pid, bbox, points, points_posed in self.cursor]
