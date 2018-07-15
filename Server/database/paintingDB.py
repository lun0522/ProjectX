import json

from .baseDB import DatabaseHandler

__all__ = ["PaintingDatabaseHandler"]

"""
mysql> use paintings

mysql> DESCRIBE Download;
+-------+---------------+------+-----+---------+----------------+
| Field | Type          | Null | Key | Default | Extra          |
+-------+---------------+------+-----+---------+----------------+
| id    | int(11)       | NO   | PRI | NULL    | auto_increment |
| title | char(30)      | NO   |     | NULL    |                |
| url   | varchar(2083) | YES  |     | NULL    |                |
+-------+---------------+------+-----+---------+----------------+

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

downloads_dir, paintings_dir, faces_dir, tmp_dir, predictor_path, style_dir, svm_dir = \
    ["/Users/lun/Desktop/ProjectX/" + path for path in
     ["downloads/", "paintings/", "faces/", "temp/",
      "models/predictor.dat", "models/style150.h5", "models/svm.pkl"]]

insert_download = " ".join(("INSERT INTO Download",
                            "(title, url)",
                            "VALUES (%s, %s)"))

update_download = " ".join(("UPDATE Download",
                            "SET url=%s",
                            "WHERE title=%s"))

query_download = " ".join(("SELECT url",
                           "FROM Download",
                           "WHERE title=%s"))

insert_painting = " ".join(("INSERT INTO Painting",
                            "(url)",
                            "VALUES (%s)"))

insert_landmark = " ".join(("INSERT INTO Landmark",
                            "(painting_id, bbox, points, points_posed)",
                            "VALUES (%s, %s, %s, %s)"))

update_landmark = " ".join(("UPDATE Landmark",
                            "SET emotion_id=%s",
                            "WHERE id=%s"))

query_landmarks = " ".join(("SELECT id, painting_id, emotion_id, bbox, points, points_posed",
                            "FROM Landmark"))


class PaintingDatabaseHandler(DatabaseHandler):
    def __init__(self):
        super().__init__("paintings")

    @staticmethod
    def get_painting_filename(index):
        return paintings_dir + str(index).zfill(5) + ".jpg"

    @staticmethod
    def get_face_filename(index):
        return faces_dir + str(index).zfill(5) + ".jpg"

    def store_download_info(self, title, url):
        self.cursor.execute(insert_download, (title, url))

    def remove_redundant_info(self, title):
        self.cursor.execute(update_download, (None, title))

    def did_not_download(self, title):
        self.cursor.execute(query_download, (title,))
        return not self.cursor.rowcount

    def retrieve_download_url(self, title):
        self.cursor.execute(query_download, (title, ))
        return self.cursor.rowcount and [url for (url, ) in self.cursor][0] or None

    def store_painting_info(self, url):
        self.cursor.execute(insert_painting, (url, ))
        return self.cursor.lastrowid

    def store_landmarks(self, landmarks, landmarks_posed, painting_id, bounding_box):
        self.cursor.execute(insert_landmark, (painting_id, json.dumps(bounding_box),
                                              json.dumps(landmarks), json.dumps(landmarks_posed)))
        return self.cursor.lastrowid

    def update_emotion(self, landmark_id, emotion_id):
        self.cursor.execute(update_landmark, (emotion_id, landmark_id))

    def get_all_landmarks(self):
        self.cursor.execute(query_landmarks)
        return [(lid, pid, eid, json.loads(bbox), json.loads(points), json.loads(points_posed))
                for lid, pid, eid, bbox, points, points_posed in self.cursor]
