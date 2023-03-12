import dataclasses
import datetime
import os.path
from typing import List, Dict, Tuple

from httplib2 import ServerNotFoundError
from ortools.sat.python import cp_model

from Interface.pages.databases import Slot, Task
from Calendar.queries import Querier


@dataclasses.dataclass
class DaySlot:
    """
    A day slot is a combination of a day and a slot

    Attributes:
        day (int) : The day of this slot
        slot (Slot) : The slot associated to it
        hard_length (int) : The hard maximum length of the given slot
    """
    day: int
    slot: Slot
    hard_length: int = 60 * 24
    hard_start_time: datetime.datetime = datetime.time(0, 0, 0)
    hard_end_time: datetime.datetime = datetime.time(23, 59, 59)

    @property
    def id(self):
        return "D" + str(self.day) + "S" + str(self.slot.id)

    def __str__(self):
        return 'Day' + str(self.day) + ':' + str(self.slot)


@dataclasses.dataclass
class TaskEvent:
    """
    A task event is a combination of a task and a day slot

    Attributes:
        start (datetime.datetime) : The start time of the event
        end (datetime.datetime) : The end time of the event
        task (Task) : The task associated to it

    """
    start: datetime.datetime
    end: datetime.datetime
    task: Task


@dataclasses.dataclass
class SlotAssignment:
    slot: DaySlot
    tasks: List[Task]


class PreProcessor:
    """
    A class to preprocess the data before solving the problem
    """
    DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
    APPLICATION_COLORS = ['1', '2', '3', '4', '5']

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
                            tasks: List[Task],
                            days: int) -> List[DaySlot]:
        """
        Generate all the slots with a given number of days. It uses the :class:`Querier` class for getting the upcoming
        events from the calendar.

        Args:
            slots(List[Slot]) : The list of slots to be filled
            tasks(List[Task]) : The list of tasks to complete
            days (int) : The number of days to consider

        Returns:
            all_slots (List[DaySlot]) : All the slots
        """

        # Get the events for the estimated time and a bit more
        credential_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "Calendar", "credentials.json")
        token_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "Calendar", "token.json")

        try:
            calendar_querier = Querier(credentials_path=credential_path, token_path=token_path)
            upcoming_events = calendar_querier.get_next_events(PreProcessor.estimate_days_feasibility(slots, tasks) + 2)
        except ServerNotFoundError:
            print("Check your internet connection")
            exit(-1)

        # Filter only those events that cannot be moved
        upcoming_events = PreProcessor.filter_events(upcoming_events)

        # Divide events by day
        occupied_times = []
        for event in upcoming_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            start_datetime_object = datetime.datetime.strptime(start, PreProcessor.DATE_FORMAT).replace(tzinfo=None)
            end_datetime_object = datetime.datetime.strptime(end, PreProcessor.DATE_FORMAT).replace(tzinfo=None)

            occupied_times.append((start_datetime_object, end_datetime_object))

        # Assign to each day slots not overlapping with the existing events
        all_slots = []
        for day in range(days):
            for slot in slots:
                # Modify starting time if it is the first day
                slot_start = slot.start
                if day == 0:
                    if slot.end < datetime.datetime.now().time():
                        continue
                    elif slot.start < datetime.datetime.now().time():
                        slot_start = datetime.datetime.now().time()

                # Create a new slot with the correct day and avoid overlaps with fixed events
                slot_today = Slot(id=slot.id, type="Work", start=slot_start, end=slot.end)
                free_spots = PreProcessor.find_free_spots(slot_today, occupied_times, day)

                # Add all the slots to the list and set the hard limits
                for cleared_slot in free_spots:
                    clear_slot = Slot(id=slot.id, type="Work", start=cleared_slot[0].time(), end=cleared_slot[1].time())

                    margin_low, margin_high = PreProcessor.compute_margins(clear_slot, occupied_times, day)

                    # Compute the low margin time and the high margin time, also the hard length limit of the slot
                    hard_low = (cleared_slot[0] - datetime.timedelta(minutes=margin_low))
                    hard_high = (cleared_slot[1] + datetime.timedelta(minutes=margin_high))
                    slot_length = int(clear_slot.get_duration().total_seconds() / 60)
                    hard_length = slot_length + margin_high + margin_low

                    # Add the slot to the list
                    all_slots.append(
                        DaySlot(day,
                                clear_slot,
                                hard_length=hard_length,
                                hard_start_time=hard_low,
                                hard_end_time=hard_high)
                    )

        return all_slots

    @staticmethod
    def compute_margins(slot: Slot,
                        events: List[Tuple[datetime.datetime, datetime.datetime]],
                        day: int
                        ) -> Tuple[int, int]:
        """
        Compute the margins of a given slot given all the events in the calendar

        Args:
            slot (Slot) : The slot to check
            events (List[Tuple[datetime.datetime, datetime.datetime]]) : The list of events

        Returns:
            margins (Tuple[int,int]) : The margins of the slot
        """
        slot_date = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=day), datetime.time())

        # Convert slot to datetime
        slot_start = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=day), slot.start)
        slot_end = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=day), slot.end)

        previous_event = None
        for event_start, event_end in events:
            if event_end <= slot_start:
                if previous_event is None or event_end > previous_event[1]:
                    previous_event = (event_start, event_end)

        # Calculate the distance from slot start to previous event end
        if previous_event is None:
            start_margin = int((slot_start - slot_date).total_seconds() / 60)
        else:
            start_margin = int((slot_start - previous_event[1]).total_seconds() / 60)

        # Find the event that starts after the slot ends
        next_event = None
        for event_start, event_end in events:
            if event_start >= slot_end:
                if next_event is None or event_start < next_event[0]:
                    next_event = (event_start, event_end)

        # Calculate the distance from slot end to next event start
        if next_event is None:
            end_margin = int(((slot_date + datetime.timedelta(hours=23, minutes=59)) - slot_end).total_seconds() / 60)
        else:
            end_margin = int((next_event[0] - slot_end).total_seconds() / 60)

        return start_margin, end_margin

    @staticmethod
    def find_free_spots(slot: Slot,
                        events: List[Tuple[datetime.datetime, datetime.datetime]],
                        day: int
                        ) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        """
        Find the free spots in a given slot given all the events in the calendar

        Args:
            slot (Slot) : The slot to check
            events (List[Tuple[datetime.datetime, datetime.datetime]]) : The list of events
            day (int) : The day to check

        Returns:
            free_spots (List[Tuple[datetime.datetime,datetime.datetime]]) : The list of free spots
        """

        # Convert slot to datetime
        slot_start = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=day), slot.start)
        slot_end = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=day), slot.end)

        available_intervals = [(slot_start, slot_end)]

        # Iterate over events and remove overlapping intervals
        for event_start, event_end in events:
            new_intervals = []
            for interval_start, interval_end in available_intervals:
                if event_start <= interval_start < event_end:
                    new_intervals.append((event_end, interval_end))
                elif event_start <= interval_end < event_end:
                    new_intervals.append((interval_start, event_start))
                elif interval_start < event_start and event_end < interval_end:
                    new_intervals.append((interval_start, event_start))
                    new_intervals.append((event_end, interval_end))
                else:
                    new_intervals.append((interval_start, interval_end))
            available_intervals = new_intervals

        # Return the list of available intervals
        return available_intervals

    @staticmethod
    def filter_events(upcoming_events: List[Dict]) -> List[Dict]:
        """
        Get only those events set by user and not by the system.
        :return:
        """
        filtered_events = []
        for event in upcoming_events:

            # Get the color id
            color_id = event.get("colorId", '-1')

            if color_id in PreProcessor.APPLICATION_COLORS:
                continue
            else:
                filtered_events.append(event)

        return filtered_events

    @staticmethod
    def dayslot_to_datetime(slot: DaySlot) -> Tuple[datetime.datetime, datetime.datetime]:
        """
        Convert a DaySlot to a tuple of datetime

        Args:
            slot (DaySlot) : The slot to convert

        Returns:
            (Tuple[datetime.datetime,datetime.datetime]) : The converted slot
        """
        slot_start = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=slot.day),
                                               slot.slot.start)
        slot_end = datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=slot.day), slot.slot.end)

        return (slot_start, slot_end)


class SolverSchedule:
    """
    A solver for setting up the schedule. It organizes tasks to slots.
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
        self.available_slots = PreProcessor.generate_days_slots(all_slots, all_tasks, self.number_days)
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
        Solve the scheduling task until a feasible number of days is found

        """
        status = cp_model.INFEASIBLE

        # While the status is not successful increase the number of days
        while status != cp_model.FEASIBLE and status != cp_model.OPTIMAL:
            status = self._solve_problem(self.number_days)
            self.print_solution()
            self.number_days += 1

    def _solve_problem(self, days: int):
        """
        Solve the scheduling problem for a given number of days

        Args:
            days (int) : The number of days to schedule

        """
        # Initialize the number of slots
        self.available_slots = PreProcessor.generate_days_slots(self.all_slots, self.all_tasks, days)

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

        return self.status

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

            # Define the very hard margin of the slots
            self.model.Add(sum_tasks_slot <= slot.hard_length)

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
        """
        Define the values for the variables of how much we value priority.

        Returns:
            values (dict) : The values for the variables
        """
        MULTIPLIERS = {}
        # This is a very meaningful but abstract representation.
        # todo : learn it using ML from the user! It is very personal
        # depending on that it means priority for user . Ask for feedback to know if they are satisfied from certain
        # suggestions.

        # It means how much value is assigned for completing a task in a given day!. For example completening a task
        # of priority 1 on day 0 gives 100 points, on day 1 gives 50 points, on day 2 gives 40 points, etc. The same
        # for priority 1, 2, 3, 4, 5.
        # priority 0 means it must be executed now
        MULTIPLIERS[0] = [100000, 0, 0, 0, 0, 0]
        MULTIPLIERS[1] = [100, 50, 10, 10, 10, 10]
        MULTIPLIERS[2] = [50, 25, 5, 5, 5, 5]
        MULTIPLIERS[3] = [40, 20, 3, 3, 3, 3]
        MULTIPLIERS[4] = [30, 15, 2, 2, 2, 2]
        MULTIPLIERS[5] = [20, 10, 1, 1, 1, 1]
        MULTIPLIERS[6] = [10, 5, 0.5, 0.5, 0.5, 0.5]

        # Extend with the same value for the next days
        for multiplier in MULTIPLIERS.keys():
            MULTIPLIERS[multiplier] += [MULTIPLIERS[multiplier][-1]] * 10

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
                objective_terms.append(-self.penalties[slot_index])

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

    def get_solution(self) -> List[SlotAssignment]:
        """
        Get the solution of the problem.

        Returns:
            solution (List[SlotAssignment]) : The solution of the problem
        """

        solution = []
        for slot_index, slot in enumerate(self.available_slots):
            assigned_tasks = []
            for task_index, task in enumerate(self.all_tasks):
                if self.solver.BooleanValue(self.x[slot_index, task_index]):
                    assigned_tasks.append(task)
            solution.append(SlotAssignment(slot, assigned_tasks))
        return solution


class SolverOrganizer:
    class Options:
        """
        Options for the solver.
        """

        def __init__(self, hard_constraint_priority: bool = True, soft_margins: bool = True):
            self.hard_constraint_priority = hard_constraint_priority
            self.soft_margins = soft_margins

    def __init__(self, options: Options = Options()):
        """
        self.options = options
        """
        self.options = options

    def solve(self, assignment: SlotAssignment) -> List[TaskEvent]:
        """
        Solve the problem.

        Args:
            assignment (SlotAssignment) : The assignment to solve
        Returns:
            solution (List[SlotAssignment]) : The solution of the problem
        """

        day = datetime.datetime.combine(
            datetime.date.today() + datetime.timedelta(days=assignment.slot.day), datetime.time(0, 0)
        )

        # Compute number of minutes of tasks
        tasks_length = PreProcessor.compute_tasks_minutes(assignment.tasks)
        slot_length = PreProcessor.compute_slots_minutes([assignment.slot.slot])

        # If the tasks is lower than the slot put them closer to midday
        if tasks_length <= slot_length:

            proposal_start1 = datetime.datetime.combine(day, assignment.slot.slot.start)
            proposal_start2 = datetime.datetime.combine(day, assignment.slot.slot.start) \
                              + datetime.timedelta(minutes=slot_length - tasks_length)

            midday = datetime.datetime.combine(day, datetime.time(12, 0))

            # If the first proposal is closer to midday, use it
            if abs(proposal_start1 - midday) < abs(proposal_start2 - midday):
                proposal_start = proposal_start1
            else:
                proposal_start = proposal_start2

        else:

            slot_start = datetime.datetime.combine(day, assignment.slot.slot.start)
            slot_end = datetime.datetime.combine(day, assignment.slot.slot.end)

            hard_start = assignment.slot.hard_start_time
            hard_end = assignment.slot.hard_end_time

            start_position = SolverOrganizer._find_segment_position(int((hard_start - day).total_seconds() / 60),
                                                                    int((hard_end - day).total_seconds() / 60),
                                                                    int((slot_start - day).total_seconds() / 60),
                                                                    int((slot_end - day).total_seconds() / 60),
                                                                    tasks_length)

            proposal_start = day + datetime.timedelta(minutes=start_position)

        # Having the starting time for the tasks just put them in the slot in order

        task_events = []
        for task in assignment.tasks:
            task_start = proposal_start
            proposal_start += datetime.timedelta(minutes=task.estimated_time)

            task_events.append(TaskEvent(task_start, proposal_start, task))

        return task_events

    def solve_all(self, assignments: List[SlotAssignment]) -> List[TaskEvent]:
        """
        Solve the problem.

        Args:
            assignments (List[SlotAssignment]) : The assignments to solve
        Returns:
            solution (List[TaskEvent]) : The solution of the problem
        """

        task_events = []
        for assignment in assignments:
            task_events += self.solve(assignment)

        return task_events

    def set_in_calendar(self,
                        task_events: List[TaskEvent]):
        """
        Set the events in the calendar.

        Args:
            task_events (List[TaskEvent]) : The events to set
        """

        querier = Querier()

        for task_event in task_events:
            summary = task_event.task.name
            description = f"Estimated to last for {task_event.task.estimated_time}"

            querier.set_event(summary, description, task_event.start, task_event.end)

    @staticmethod
    def _find_segment_position(A, B, a, b, d):
        """
        Finds the position of a line segment of length d that maximizes the overlap with the sub-interval (a,b),
        but does not go out of the interval (A,B).

        Args:
        - A, B: float or int - the endpoints of the interval (A,B)
        - a, b: float or int - the endpoints of the sub-interval (a,b)
        - d: float or int - the length of the line segment

        Returns:
        - float or int - the position of the line segment that maximizes the overlap with the sub-interval (a,b)
        """

        # Compute the length of the overlap between the intervals (A,B) and (a,b)
        overlap_length = min(B, b) - max(A, a)

        # Compute the maximum distance that the line segment can be shifted to the right without going out of (A,B)
        max_shift_right = B - d

        # Compute the maximum distance that the line segment can be shifted to the left without going out of (A,B)
        max_shift_left = A

        # If there is no overlap between the intervals (A,B) and (a,b), return the midpoint of the interval (A,B)
        if overlap_length <= 0:
            return (A + B) / 2

        # If the length of the overlap is greater than or equal to the length of the line segment, the line segment can be fully contained in (a,b)
        if overlap_length >= d:
            return max(A, min(max_shift_right, (a + b - d) / 2))

        # If the length of the overlap is less than the length of the line segment, the line segment needs to be partially contained in (a,b)
        else:
            return max(A, min(max_shift_right, b - overlap_length))
