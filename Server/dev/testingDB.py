import mysql.connector
import json
import os

"""
mysql> use model

mysql> DESCRIBE Training/Testing/Validation/Pool;
+------------+---------+------+-----+---------+----------------+
| Field      | Type    | Null | Key | Default | Extra          |
+------------+---------+------+-----+---------+----------------+
| id         | int(11) | NO   | PRI | NULL    | auto_increment |
| emotion_id | int(11) | NO   |     | NULL    |                |
| points     | json    | NO   |     | NULL    |                |
+------------+---------+------+-----+---------+----------------+
"""

dataset_dir = "/Users/lun/Desktop/ProjectX/dataset"
emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
emotions_dir = [os.path.join(dataset_dir, emotion) for emotion in emotions]

cnx = mysql.connector.connect(user="root",
                              password="password",
                              host="localhost",
                              database="model")
cursor = cnx.cursor(buffered=True)

query_landmarks = "SELECT * FROM {}"

insert_landmark = " ".join(("INSERT INTO {}",
                            "(emotion_id, points)",
                            "VALUES (%s, %s)"))


def get_landmarks(branch):
    cursor.execute(query_landmarks.format(branch))
    return [(landmark_id, emotion_id, json.loads(points))
            for landmark_id, emotion_id, points in cursor]


def store_landmarks(branch, emotion_id, landmarks):
    cursor.execute(insert_landmark.format(branch), (emotion_id, json.dumps(landmarks)))


def commit_change():
    cnx.commit()
    print("DB changes committed")


def cleanup():
    cursor.close()
    cnx.close()
    print("DB cleaned up")
