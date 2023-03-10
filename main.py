import dataclasses
from typing import Any, List, Dict

from Interface.pages.databases import DataBasehandler, ScheduleDatabase, Task, Slot
import pandas as pd

from ortools.sat.python import cp_model
from termcolor import colored


@dataclasses.dataclass
class DaySlot:
    day: int
    slot: Slot

    @property
    def id(self):
        return "D" + str(self.day) + "S" + str(self.slot.id)

    def __str__(self):
        return 'Day' + str(self.day) + ':' + str(self.slot)


class PreProcessor:
    @staticmethod
    def compute_slots_minutes(slots: List[Slot]
                              ) -> int:
        """
        Compute the number of minutes available in slots.

        Args:
            slots(List[Slot]) : The list of slots

        Returns:
            minutes (int) : The number of minutes available
        """
        return sum([int(slot.get_duration().total_seconds() / 60) for slot in slots])

    @staticmethod
    def compute_tasks_minutes(tasks: List[Task]
                              ) -> int:
        """
        Get the number of minutes necessary to complete all tasks.

        Args:
            tasks (List[Task]) : The list of tasks

        Returns:
            minutes (int) : The number of minutes necessary to complete
        """
        return sum([task.estimated_time for task in tasks])

    @staticmethod
    def estimate_days_feasibility(slots: List[Slot],
                                  tasks: List[Task]
                                  ) -> int:
        """
        Estimate the number of days necessary for the tasks to be feasible

        Args:
            slots(List[Slot]) : The list of slots
            tasks(List[Task]) : The list of tasks to complete

        Returns:
            number_days (int) : The number of days
        """
        number_minutes_tasks = PreProcessor.compute_tasks_minutes(tasks)
        number_minutes_slots = PreProcessor.compute_slots_minutes(slots)
        # Add days necessary to complete the task until
        day = 1
        slots_minutes = number_minutes_slots
        while slots_minutes < number_minutes_tasks:
            slots_minutes += number_minutes_slots
            day += 1

        return day

    @staticmethod
    def generate_days_slots(slots: List[Slot],
                            days: int) -> List[DaySlot]:
        """
        Generate all the slots with a given number of days

        Args:
            slots(List[Slot]) : The list of slots
            days (int) : The number of days to duplicate

        Returns:
            all_slots (List[DaySlot]) : All the slots
        """
        all_slots = []
        for day in range(days):
            for slot in slots:
                all_slots.append(DaySlot(day, slot))

        return all_slots

    @staticmethod
    def filter_slots():
        pass


class SolverSchedule:
    """
    A solver for setting up the schedule
    """

    MAX_PRIORITY = 10

    @dataclasses.dataclass
    class Options:
        soft_margins: bool = True
        hard_constraint_priority: bool = False

    def __init__(self,
                 all_tasks: List[Task],
                 all_slots: List[Slot],
                 options: Options = Options()):

        """
        Initialize the solver

        Args:
            all_tasks (List[Task]) : The list of tasks to complete
            all_slots (List[Slot]) : The list of slots available

        """
        self.all_tasks = all_tasks
        self.all_slots = all_slots
        self.number_days = PreProcessor.estimate_days_feasibility(all_slots, all_tasks)
        self.available_slots = PreProcessor.generate_days_slots(all_slots, self.number_days)
        self.options = options

        # Initialize variables
        self.x = {}
        self.penalties = {}
        self.strict = {}

        # Create model and solver
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Define the problem
        self.define_variables()
        self.status = cp_model.UNKNOWN

    def solve_problems(self):
        """
        Solve the scheduling task

        """
        # Re-initialize the variables
        self.x = {}
        self.strict = {}
        self.penalties = {}

        # Define the problem
        self.model = cp_model.CpModel()
        self.x = self.define_variables()
        self.define_constraints()
        objective_terms = self.define_objective()

        # Solve it
        self.model.Maximize(sum(objective_terms))
        self.solver = cp_model.CpSolver()
        self.status = self.solver.Solve(self.model)

        # Print the solution
        self.print_solution()

    def define_variables(self):
        """
        Define the variables for the constrained problem in the model

        Returns:
            variables (dict) : The variables
        """
        # Create variables for every slot and task
        self.x = {}
        self.strict = {}
        self.penalties = {}
        for slot in range(len(self.available_slots)):
            for task in range(len(self.all_tasks)):
                var = self.model.NewBoolVar(f"x[{self.available_slots[slot].id},{task}]")
                self.x[slot, task] = var

            # Variable defining if the task fills strictly in the slot, and a penality in case it does not
            if self.options.soft_margins:
                self.strict[slot] = self.model.NewBoolVar(f"strict[{slot}]")
                self.penalties[slot] = self.model.NewIntVar(0, max([task.estimated_time for task in self.all_tasks]),
                                                            f"penalties[{slot}]")
        return self.x

    def define_constraints(self):
        """
        Define all the constraints
        :return:
        """
        # Add Constraints
        # Each task is assigned to exactly one slot.
        for task in range(len(self.all_tasks)):
            self.model.AddExactlyOne(self.x[slot, task] for slot in range(len(self.available_slots)))

        # Add constraint about length of tasks not overpassing slot size
        for index_slot, slot in enumerate(self.available_slots):
            # Define the sum of the duration of the tasks assigned to a slot
            sum_tasks_slot = (sum(self.x[index_slot, task] * self.all_tasks[task].estimated_time
                                  for task in range((len(self.all_tasks)))))

            if self.options.soft_margins:
                # The sum of the duration of the tasks assigned to a slot cannot exceed the duration of the slot. When the
                # constraint is strict
                self.model.Add(sum_tasks_slot <= int(slot.slot.get_duration().total_seconds() / 60)). \
                    OnlyEnforceIf(self.strict[index_slot])

                self.model.Add(self.penalties[index_slot] == 0).OnlyEnforceIf(self.strict[index_slot])

                # When the constraint is not strict we enforce a penalty
                self.model.Add(sum_tasks_slot > int(slot.slot.get_duration().total_seconds() / 60)). \
                    OnlyEnforceIf(self.strict[index_slot].Not())

                violation = sum_tasks_slot - int(slot.slot.get_duration().total_seconds() / 60)
                self.model.Add(self.penalties[index_slot] >= violation). \
                    OnlyEnforceIf(self.strict[index_slot].Not())
            else:
                self.model.Add(sum_tasks_slot <= int(slot.slot.get_duration().total_seconds() / 60))

        if self.options.hard_constraint_priority:
            # Add constraint about priority of tasks
            pass

    def define_values(self) -> Dict:
        MULTIPLIERS = {}
        # This is a very meaningful but abstract representation.
        # todo : learn it using ML from the user! It is very personal
        # depending on that it means priority for user . Ask for feedback to know if they are satisfied from certain
        # suggestions.

        # It means how much value is assigned for completing a task in a given day!. For example completening a task
        # of priority 1 on day 0 gives 100 points, on day 1 gives 50 points, on day 2 gives 40 points, etc. The same
        # for priority 1, 2, 3, 4, 5.
        # priority 0 means it must be executed now
        MULTIPLIERS[0] = [1000, 0, 0, 0, 0, 0]
        MULTIPLIERS[1] = [100, 50, 10, 10, 10, 10]
        MULTIPLIERS[2] = [50, 25, 5, 5, 5, 5]
        MULTIPLIERS[3] = [40, 20, 3, 3, 3, 3]
        MULTIPLIERS[4] = [30, 15, 2, 2, 2, 2]
        MULTIPLIERS[5] = [20, 10, 1, 1, 1, 1]
        MULTIPLIERS[6] = [10, 5, 0.5, 0.5, 0.5, 0.5]

        return MULTIPLIERS

    def define_objective(self):
        objective_terms = []

        MULTIPLIERS = self.define_values()
        values = {}
        # Define the values of each assignment based on the priority of the task and the day of the slot
        for slot_index, slot in enumerate(self.available_slots):
            for task_index, task in enumerate(self.all_tasks):
                values[slot_index, task_index] = MULTIPLIERS[task.priority][slot.day]

        # Maximize the amount of tasks to be completed, prioritizing the most important ones to be in closer slots.
        for task_index, task in enumerate(self.all_tasks):
            for slot_index, slot in enumerate(self.available_slots):
                term = self.x[slot_index, task_index] * values[slot_index, task_index]
                objective_terms.append(term)

        # # Minimize the number of minutes left free in the slots (fill tightly)
        # for slot_index, slot in enumerate(self.available_slots):
        #     # Get the duration of the slot and subtract the time of the tasks
        #     term = slot.slot.get_duration().total_seconds() / 60 - \
        #            sum([self.x[slot_index, task_index] * task.estimated_time
        #                 for task_index, task in enumerate(self.all_tasks)])
        #
        #     # Add the term to the objective, our aim is to minimize this free time
        #     objective_terms.append(-term)

        # Minimize the number of penalties. Multiplied for making a very strong penalty

        if self.options.soft_margins:
            for slot_index, slot in enumerate(self.available_slots):
                objective_terms.append(-self.penalties[slot_index])  # * MAX_PRIORITY * self.number_days)

        return objective_terms

    def print_solution(self):
        # Print the solution
        if self.status == cp_model.OPTIMAL or self.status == cp_model.FEASIBLE:
            print("Optimal : ", self.status == cp_model.OPTIMAL)
            print(f'Total \"points\" = {self.solver.ObjectiveValue()}\n')
            for slot_index, slot in enumerate(self.available_slots):
                print(f'Slot {slot}:')
                assigned_minutes = 0
                assigned_tasks = 0
                for task_index, task in enumerate(self.all_tasks):
                    if self.solver.BooleanValue(self.x[slot_index, task_index]):
                        print(f'\t{assigned_tasks + 1})Task {task}.' +
                              f'\tValue = {(self.MAX_PRIORITY - task.priority) * (self.number_days - slot.day)}')
                        assigned_minutes += task.estimated_time
                        assigned_tasks += 1
                print("")
                print("\tAssigned minutes: ", assigned_minutes, '/', int(slot.slot.get_duration().total_seconds() / 60))
                print("\tPenalty: ", self.solver.Value(self.penalties[slot_index]))
                print("\tStrict: ", self.solver.BooleanValue(self.strict[slot_index]))
                print("\n\n")



        else:
            print('No solution found.')


def main():
    # Fetch the database
    all_tasks = DataBasehandler.view_all_data()
    all_slots = ScheduleDatabase.view_all_data()

    # Filter them
    all_tasks = [DataBasehandler.transform(data) for data in all_tasks]
    all_slots = [ScheduleDatabase.transform(data) for data in all_slots]

    all_slots = [slot for slot in all_slots if slot.type == "Work"]

    # Solve the problem
    print(colored("[AVAILABLE SLOTS]", "blue"))
    print(all_slots)

    print(colored("SOLVING", "red"))

    scheduler = SolverSchedule(all_tasks, all_slots)
    scheduler.solve_problems()


if __name__ == '__main__':
    main()
