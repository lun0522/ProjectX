import mysql.connector

cnx = mysql.connector.connect(user='root',
                              password='password',
                              host='localhost',
                              database='paintings')
cursor = cnx.cursor(buffered=True)

add_bbox = ("INSERT INTO bounding_box"
            "(title, has_face, xlo, xhi, ylo, yhi)"
            "VALUES (%s, %s, %s, %s, %s, %s)")
add_no_face = ("INSERT INTO bounding_box"
            "(title, has_face)"
            "VALUES (%s, %s)")
query_bbox = ("SELECT id "
              "FROM bounding_box "
              "WHERE title=%s")


def store_bounding_box(title, xlo, xhi, ylo, yhi):
    cursor.execute(add_bbox, (title, 1, xlo, xhi, ylo, yhi))


def denote_no_face(title):
    cursor.execute(add_no_face, (title, 0))


def bbox_did_exist(title):
    cursor.execute(query_bbox, (title, ))
    return cursor.rowcount


def commit_change():
    cnx.commit()


def cleanup():
    cursor.close()
    cnx.close()


if __name__ == "__main__":
    cleanup()
