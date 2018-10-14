import mysql.connector


class DatabaseHandler(object):
    def __init__(self, database):
        self.database = database
        self.cnx = mysql.connector.connect(user="root",
                                           password="password",
                                           host="localhost",
                                           database=database)
        self.cursor = self.cnx.cursor(buffered=True)

    def commit(self):
        self.cnx.commit()
        print(f"Database '{self.database}' committed")

    def close(self):
        self.cursor.close()
        self.cnx.close()
        print(f"Database '{self.database}' closed")
