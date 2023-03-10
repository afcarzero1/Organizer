import dataclasses
import datetime
import sqlite3
import os
from dataclasses import dataclass
from typing import Tuple

# Get the absolute path of the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the data.db file relative to the script
db_path = os.path.join(script_dir, "data.db")

conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()


@dataclass
class Task:
    """A task to be completed.

    Attributes:
        id (int): The unique identifier of the task.
        name (str): The name of the task.
        priority (int): The priority of the task, from 1 (highest) to 5 (lowest).
        status (str): The current status of the task, such as "Not started", "In progress", or "Completed".
        due_date (datetime.date): The due date of the task, if any.
        estimated_time (int): The estimated time required to complete the task, if known.
        category (str): The category of the task, such as "Work", "Personal", or "Errands".
    """
    id: int
    name: str
    priority: int
    status: str
    due_date: datetime.date
    estimated_time: int
    category: str

    def __str__(self):
        return f"{self.category[:20]}_{self.name[:20]} ,mins : {self.estimated_time}, priority: {self.priority}"


class DataBasehandler:
    COLUMNS_NAMES = ["ID",
                     "TASK",
                     "TASK_PRIORITY",
                     "TASK_STATUS",
                     "TASK_DUE_DATE",
                     "TASK_ESTIMATED_TIME",
                     "TASK_CATEGORY"]

    TABLE_NAME = "tasks_table"

    @staticmethod
    def create_table():
        """
        Create the tables in the database

        """
        c.execute(f'CREATE TABLE IF NOT EXISTS {DataBasehandler.TABLE_NAME}('
                  'id INTEGER PRIMARY KEY AUTOINCREMENT,'
                  'task TEXT,'
                  'task_priority INTEGER,'
                  'task_status TEXT,'
                  'task_due_date DATE,'
                  'task_estimated_time FLOAT,'
                  'task_category TEXT)')

    @staticmethod
    def add_data(task: str,
                 task_priority: int,
                 task_status: str,
                 task_due_date: datetime.datetime,
                 task_estimated_time: float,
                 task_category: str):
        c.execute(
            f'INSERT INTO {DataBasehandler.TABLE_NAME}'
            '(task, '
            'task_priority,'
            ' task_status, '
            'task_due_date, '
            'task_estimated_time, '
            'task_category) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (task, task_priority, task_status, task_due_date, task_estimated_time, task_category))
        conn.commit()

    @staticmethod
    def view_all_data():
        """
        Get all the data in the database
        :return:
        """
        c.execute(f'SELECT * FROM {DataBasehandler.TABLE_NAME}')
        data = c.fetchall()
        return data

    @staticmethod
    def view_all_task_names():
        c.execute(f'SELECT DISTINCT task FROM {DataBasehandler.TABLE_NAME}')
        data = c.fetchall()
        return data

    @staticmethod
    def get_task(task):
        c.execute(f'SELECT * FROM {DataBasehandler.TABLE_NAME} WHERE task=?', (task,))
        data = c.fetchall()
        return data

    @staticmethod
    def get_task_by_status(task_status):
        c.execute(f'SELECT * FROM {DataBasehandler.TABLE_NAME} WHERE task_status=?', (task_status,))
        data = c.fetchall()
        return data

    @staticmethod
    def edit_task_data(
            task_id: int,
            new_task: str,
            new_task_priority: int,
            new_task_status: str,
            new_task_date: datetime.datetime,
            new_task_estimated_time: float,
            new_task_category: str
    ):
        c.execute(
            f"UPDATE {DataBasehandler.TABLE_NAME} SET "
            f"task=?, "
            f"task_priority=?,"
            f" task_status=?, "
            f"task_due_date=?, "
            f"task_estimated_time=?, "
            f"task_category=? "
            "WHERE id = ?",
            (new_task, new_task_priority, new_task_status, new_task_date, new_task_estimated_time, new_task_category,
             task_id))
        conn.commit()

    @staticmethod
    def delete_data(id):
        c.execute(f'DELETE FROM {DataBasehandler.TABLE_NAME} WHERE id=?', (id,))
        conn.commit()

    @staticmethod
    def str_to_priority(priority: str) -> int:
        if priority == "Immediate":
            return 0
        if priority == "High":
            return 1
        elif priority == "Middle":
            return 2
        else:
            return 3

    @staticmethod
    def str_to_status(status: str) -> int:
        if status == "ToDo":
            return 0
        elif status == "Doing":
            return 1
        else:
            return 2

    @staticmethod
    def transform(data: Tuple) -> Task:
        due_date = datetime.datetime.strptime(data[4], "%Y-%m-%d")
        estimated_time = int(data[5] * 60)

        return Task(data[0], data[1], data[2], data[3], due_date, estimated_time, data[6])
