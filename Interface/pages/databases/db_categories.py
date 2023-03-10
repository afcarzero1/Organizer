import datetime
import sqlite3
import os

# Get the absolute path of the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the data.db file relative to the script
db_path = os.path.join(script_dir, "data.db")

conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()


class CategoriesDatabase:
    COLUMNS_NAMES = ["ID",
                     "NAME",
                     "PRIORITY",
                     "END"]

    TABLE_NAME = "schedules_table"

    @staticmethod
    def create_table():
        c.execute(f"CREATE TABLE IF NOT EXISTS {CategoriesDatabase.TABLE_NAME}("
                  f"{CategoriesDatabase.COLUMNS_NAMES[0]} INTEGER PRIMARY KEY AUTOINCREMENT,"
                  f"{CategoriesDatabase.COLUMNS_NAMES[1]} TEXT,"
                  f"{CategoriesDatabase.COLUMNS_NAMES[2]} INTEGER,"
                  f"{CategoriesDatabase.COLUMNS_NAMES[3]} TEXT)")

    @staticmethod
    def add_data(name: str,
                 priority: int,
                 end: datetime.time):
        c.execute(f"INSERT INTO {CategoriesDatabase.TABLE_NAME} ("
                  f"{CategoriesDatabase.COLUMNS_NAMES[1]},"
                  f"{CategoriesDatabase.COLUMNS_NAMES[2]},"
                  f"{CategoriesDatabase.COLUMNS_NAMES[3]}) VALUES (?,?,?)",
                  (name, priority, str(end)))

        conn.commit()

    @staticmethod
    def view_all_data():
        c.execute(f"SELECT * FROM {CategoriesDatabase.TABLE_NAME}")
        data = c.fetchall()
        return data

    @staticmethod
    def delete_data(id):
        c.execute(f"DELETE FROM {CategoriesDatabase.TABLE_NAME} WHERE "
                  f"{CategoriesDatabase.COLUMNS_NAMES[0]}=?", (id,))
        conn.commit()