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
        print("Database '{}' committed".format(self.database))

    def close(self):
        self.cursor.close()
        self.cnx.close()
        print("Database '{}' closed".format(self.database))
