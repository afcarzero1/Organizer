import dataclasses
import datetime
import sqlite3
import os
from typing import Tuple

# Get the absolute path of the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the data.db file relative to the script
db_path = os.path.join(script_dir, "data.db")

conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()


@dataclasses.dataclass
class Slot:
    """A time slot for a schedule.

    Attributes:
        id (int): The unique identifier of the slot.
        type (str): The type of slot, such as "lecture", "lab", or "office hours".
        start (datetime.time): The start time of the slot.
        end (datetime.time): The end time of the slot.
    """
    id: int
    type: str
    start: datetime.time
    end: datetime.time

    def get_duration(self) -> datetime.timedelta:
        """Return the duration of the time slot.

        Returns:
            datetime.timedelta: The duration of the time slot.
        """
        start_datetime = datetime.datetime.combine(datetime.date.today(), self.start)
        end_datetime = datetime.datetime.combine(datetime.date.today(), self.end)
        return end_datetime - start_datetime

    def __str__(self):
        interval_str = f"{self.start.strftime('%H:%M')} - {self.end.strftime('%H:%M')}"
        return interval_str




class ScheduleDatabase:
    COLUMNS_NAMES = ["ID",
                     "TYPE",
                     "START",
                     "END"]

    TABLE_NAME = "schedules_table"

    @staticmethod
    def create_table():
        c.execute(f"CREATE TABLE IF NOT EXISTS {ScheduleDatabase.TABLE_NAME}("
                  f"{ScheduleDatabase.COLUMNS_NAMES[0]} INTEGER PRIMARY KEY AUTOINCREMENT,"
                  f"{ScheduleDatabase.COLUMNS_NAMES[1]} TEXT,"
                  f"{ScheduleDatabase.COLUMNS_NAMES[2]} TEXT,"
                  f"{ScheduleDatabase.COLUMNS_NAMES[3]} TEXT)")

    @staticmethod
    def add_data(type: str,
                 start: datetime.time,
                 end: datetime.time):
        c.execute(f"INSERT INTO {ScheduleDatabase.TABLE_NAME} ("
                  f"{ScheduleDatabase.COLUMNS_NAMES[1]},"
                  f"{ScheduleDatabase.COLUMNS_NAMES[2]},"
                  f"{ScheduleDatabase.COLUMNS_NAMES[3]}) VALUES (?,?,?)",
                  (type, str(start), str(end)))

        conn.commit()

    @staticmethod
    def view_all_data():
        c.execute(f"SELECT * FROM {ScheduleDatabase.TABLE_NAME}")
        data = c.fetchall()
        return data

    @staticmethod
    def delete_data(id):
        c.execute(f"DELETE FROM {ScheduleDatabase.TABLE_NAME} WHERE "
                  f"{ScheduleDatabase.COLUMNS_NAMES[0]}=?", (id,))
        conn.commit()

    @staticmethod
    def transform(data: Tuple):
        start = datetime.datetime.strptime(data[2], '%H:%M:%S').time()
        end = datetime.datetime.strptime(data[3], '%H:%M:%S').time()

        return Slot(data[0], data[1], start, end)
