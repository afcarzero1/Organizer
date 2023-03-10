import dataclasses
from typing import Any, List, Dict

from Interface.pages.databases import DataBasehandler, ScheduleDatabase, Task, Slot
import pandas as pd

from ortools.sat.python import cp_model
from termcolor import colored

from organizer import SolverSchedule


def main():
    # Fetch the database
    all_tasks = DataBasehandler.view_all_data()
    all_slots = ScheduleDatabase.view_all_data()

    # Filter them
    all_tasks = [DataBasehandler.transform(data) for data in all_tasks]
    all_slots = [ScheduleDatabase.transform(data) for data in all_slots]

    all_tasks = [task for task in all_tasks if task.status == "ToDo"]
    all_slots = [slot for slot in all_slots if slot.type == "Work"]

    # Solve the problem of assignment
    scheduler = SolverSchedule(all_tasks, all_slots)
    scheduler.solve_problems()
    assignments = scheduler.get_solution()

    # Organize solution with hard constraints

if __name__ == '__main__':
    main()
