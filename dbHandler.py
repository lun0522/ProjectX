import mysql.connector
import re
import json

"""
mysql> use paintings

mysql> describe Boundingbox;
+----------+---------------+------+-----+---------+----------------+
| Field    | Type          | Null | Key | Default | Extra          |
+----------+---------------+------+-----+---------+----------------+
| bid      | int(11)       | NO   | PRI | NULL    | auto_increment |
| title    | char(30)      | NO   |     | NULL    |                |
| url      | varchar(2083) | YES  |     | NULL    |                |
| has_face | tinyint(1)    | NO   |     | NULL    |                |
| bbox     | json          | YES  |     | NULL    |                |
+----------+---------------+------+-----+---------+----------------+

mysql> describe File;
+-------+---------------+------+-----+---------+----------------+
| Field | Type          | Null | Key | Default | Extra          |
+-------+---------------+------+-----+---------+----------------+
| fid   | int(11)       | NO   | PRI | NULL    | auto_increment |
| url   | varchar(2083) | NO   |     | NULL    |                |
+-------+---------------+------+-----+---------+----------------+

mysql> describe Landmark;
+--------+---------+------+-----+---------+----------------+
| Field  | Type    | Null | Key | Default | Extra          |
+--------+---------+------+-----+---------+----------------+
| lid    | int(11) | NO   | PRI | NULL    | auto_increment |
| bid    | int(11) | NO   | MUL | NULL    |                |
| fid    | int(11) | NO   | MUL | NULL    |                |
| points | json    | NO   |     | NULL    |                |
+--------+---------+------+-----+---------+----------------+
"""

downloads_dir = "/Users/lun/Desktop/ProjectX/downloads/"
paintings_dir = "/Users/lun/Desktop/ProjectX/paintings/"
cnx = mysql.connector.connect(user="root",
                              password="password",
                              host="localhost",
                              database="paintings")
cursor = cnx.cursor(buffered=True)

insert_bbox = " ".join(("INSERT INTO Boundingbox",
                        "(title, url, has_face, bbox)",
                        "VALUES (%s, %s, %s, %s)"))

update_url_in_bbox = " ".join(("UPDATE Boundingbox",
                               "SET url=%s",
                               "WHERE title=%s"))

query_face_in_bbox = " ".join(("SELECT has_face",
                               "FROM Boundingbox",
                               "WHERE title=%s"))

query_url_in_bbox = " ".join(("SELECT url",
                              "FROM Boundingbox",
                              "WHERE title=%s"))

delete_bbox = " ".join(("DELETE FROM Boundingbox",
                        "WHERE title=%s"))

insert_file = " ".join(("INSERT INTO File",
                        "(url)",
                        "VALUES (%s)"))

insert_landmark = " ".join(("INSERT INTO Landmark",
                            "(bid, fid, points)",
                            "VALUES (%s, %s, %s)"))

query_landmarks = " ".join(("SELECT bid, fid, points",
                            "FROM landmarks"))


def normalize_title(title):
    # any non-alphanumeric character will be replaced
    normed_title = re.sub("[^0-9a-zA-Z]+", " ", title.strip()).strip()
    if len(normed_title) > 30:
        normed_title = normed_title[0:30].strip()
    return normed_title.replace(" ", "_")


def store_bounding_box(title, url, has_face, xlo=0, xhi=0, ylo=0, yhi=0):
    if has_face:
        cursor.execute(insert_bbox, (title, url, 1, json.dumps((xlo, xhi, ylo, yhi))))
    else:
        cursor.execute(insert_bbox, (title, url, 0, None))
    return cursor.lastrowid


def remove_url(title):
    cursor.execute(update_url_in_bbox, (None, title))


def bounding_box_did_exist(title):
    cursor.execute(query_face_in_bbox, (title, ))
    return cursor.rowcount


def bounding_box_has_face(title):
    cursor.execute(query_face_in_bbox, (title,))
    if cursor.rowcount > 1:
        return True
    elif cursor.rowcount == 1:
        return [has_face for (has_face, ) in cursor][0]
    else:
        raise mysql.connector.Error(msg="{} does not exist in the database!".format(title))


def delete_bounding_box(title):
    cursor.execute(query_url_in_bbox, (title,))
    if cursor.rowcount:
        img_url = [url for (url, ) in cursor][0]
        cursor.execute(delete_bbox, (title,))
        return img_url
    else:
        return None


def store_file_info(url):
    cursor.execute(insert_file, (url,))
    return cursor.lastrowid


def store_landmarks(bbox_id, file_id, landmarks):
    cursor.execute(insert_landmark, (bbox_id, file_id, json.dumps(landmarks)))
    return cursor.lastrowid


def get_all_landmarks():
    cursor.execute(query_landmarks)
    return [(bid, fid, json.loads(points)) for bid, fid, points in cursor]


def commit_change():
    cnx.commit()
    print("DB changes committed")


def cleanup():
    cursor.close()
    cnx.close()
    print("DB cleaned up")
