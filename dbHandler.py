import mysql.connector
import re
import json

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
+-------------+---------+------+-----+---------+----------------+
| Field       | Type    | Null | Key | Default | Extra          |
+-------------+---------+------+-----+---------+----------------+
| id          | int(11) | NO   | PRI | NULL    | auto_increment |
| painting_id | int(11) | NO   | MUL | NULL    |                |
| bbox        | json    | NO   |     | NULL    |                |
| points      | json    | NO   |     | NULL    |                |
+-------------+---------+------+-----+---------+----------------+
"""

downloads_dir = "/Users/lun/Desktop/ProjectX/downloads/"
paintings_dir = "/Users/lun/Desktop/ProjectX/paintings/"
cnx = mysql.connector.connect(user="root",
                              password="password",
                              host="localhost",
                              database="paintings")
cursor = cnx.cursor(buffered=True)

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

query_painting = " ".join(("SELECT url",
                           "FROM Painting",
                           "WHERE id=%s"))

insert_landmark = " ".join(("INSERT INTO Landmark",
                            "(painting_id, bbox, points)",
                            "VALUES (%s, %s, %s)"))

query_landmarks = " ".join(("SELECT painting_id, bbox, points",
                            "FROM Landmark"))


def normalize_title(title):
    # any non-alphanumeric character will be replaced
    normed_title = re.sub("[^0-9a-zA-Z]+", " ", title.strip()).strip()
    if len(normed_title) > 30:
        normed_title = normed_title[0:30].strip()
    return normed_title.replace(" ", "_")


def store_download_info(title, url):
    cursor.execute(insert_download, (title, url))


def remove_redundant_info(title):
    cursor.execute(update_download, (None, title))


def retrieve_download_url(title):
    cursor.execute(query_download, (title, ))
    return cursor.rowcount and [url for (url,) in cursor][0] or None


def store_painting_info(url):
    cursor.execute(insert_painting, (url,))
    return cursor.lastrowid


def retrieve_painting_url(painting_id):
    cursor.execute(query_painting, (painting_id, ))
    return cursor.rowcount and [url for (url, ) in cursor][0] or None


def store_landmarks(painting_id, landmarks, bounding_box):
    cursor.execute(insert_landmark, (painting_id, json.dumps(bounding_box), json.dumps(landmarks)))


def get_all_landmarks():
    cursor.execute(query_landmarks)
    return [(pid, json.loads(bbox), json.loads(points)) for pid, bbox, points in cursor]


def commit_change():
    cnx.commit()
    print("DB changes committed")


def cleanup():
    cursor.close()
    cnx.close()
    print("DB cleaned up")
