import dataclasses
from typing import List

import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import NullFormatter
import datetime
from dateutil.relativedelta import relativedelta

from enum import Enum


def diffMonth(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month


@dataclasses.dataclass
class ExpectedTransaction:
    """
    Class representing a transaction that is expected to happen in the future.
    """
    category: str = ""
    initial_date: datetime.datetime = datetime.datetime.now()
    recurrency: relativedelta = relativedelta()
    value: float = 0
    final_date: datetime.datetime = None

    def __post_init__(self):
        """
        Small code for ensuring that the initial date and final date is at 0:00:00
        """
        print(type(self.initial_date))
        if isinstance(self.initial_date, datetime.datetime):
            self.initial_date = self.initial_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif isinstance(self.initial_date, datetime.date):
            self.initial_date = datetime.datetime.combine(self.initial_date, datetime.time(0, 0, 0))
        else:
            raise TypeError("Invalid type for initial_date")

        if self.final_date is not None:
            if isinstance(self.final_date, datetime.datetime):
                self.final_date = self.final_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif isinstance(self.final_date, datetime.date):
                self.final_date = datetime.datetime.combine(self.final_date, datetime.time(0, 0, 0))
            else:
                raise TypeError("Invalid type for final_date")


class Types(Enum):
    """
    Enum representing the type of transaction. It can be either "Expense" or "Income".
    """
    Expense = "Expense"
    Income = "Income"


class BudgetHandler:
    """
    Class handling the budget simulation.

    Attributes:
        simulation_initial_date (datetime.datetime) : Initial date of the simulation
        simulation_final_date (datetime.datetime) : Final date of the simulation
        transactions (Dict[List[ExpectedTransaction]]) : Dictionary containing the transactions.
            The key is the type of transaction.
    """

    def __init__(self,
                 initial_balance=13000,
                 initial_date=datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                 final_date=datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) +
                            relativedelta(months=20)
                 ):
        """
        Constructor of the class.

        Args:
            initial_balance (float) : Initial balance of the simulation
            initial_date (datetime.datetime) : Initial date of the simulation
            final_date (datetime.datetime) : Final date of the simulation
        """
        self.simulation_initial_date: datetime.datetime = initial_date
        self.simulation_final_date: datetime.datetime = final_date

        # Initialize transactions with empty lists. A list is created for each type of transaction
        self.transactions: {[ExpectedTransaction]} = {}
        self._tables_days: {pd.DataFrame} = {}

        # Initialize the dictionary with the types of transactions
        for type_name in Types:
            self.transactions[type_name] = list()
            self._tables_days[type_name] = pd.DataFrame()

        # Set the initial balance
        self.initial_balance = initial_balance
        self.balance: np.ndarray = np.zeros((self.simulation_final_date - self.simulation_initial_date).days + 1)

    @property
    def tables(self):
        return self._tables_days

    def add_expected_transaction(self,
                                 transaction: ExpectedTransaction,
                                 category_type: Types):
        """
        Add a transaction to the list of transactions. It is possible to add new transactions to an already existent category.
        This allows to add transactions incrementally.

        Args:
            transaction (ExpectedTransaction) : The transaction to add category_type (str) : The type of
                transaction. It can be either "Expense" or "Income". Check the :class:`Types` class for more information.
            category_type (str) : The type of transaction. It can be either "Expense" or "Income". Check the :class:`Types`

        """
        assert category_type in Types, f"Invalid category type: {category_type}"
        self.transactions[category_type].append(transaction)

        transaction_arrays: (np.ndarray, np.ndarray) = self._create_transaction_array(transaction)

        # Check if the category already exists. In case it exists simply add up
        if transaction.category in self._tables_days[category_type].columns:
            self._tables_days[category_type][transaction.category] = pd.Series(transaction_arrays[0]) + \
                                                                     self._tables_days[category_type][
                                                                         transaction.category]
        else:
            self._tables_days[category_type][transaction.category] = transaction_arrays[0].tolist()

    def compute_balances(self, recalculateTables=False):
        if recalculateTables:
            self._recalculateTables()

        # Use the tables to compute the balances
        expenses = self._tables_days[Types.Expense].sum(axis=1)
        incomes = self._tables_days[Types.Income].sum(axis=1)
        delta = incomes - expenses

        sim_length = (self.simulation_final_date - self.simulation_initial_date).days + 1
        balance: np.ndarray = np.zeros((self.simulation_final_date - self.simulation_initial_date).days + 1)
        balance[0] = self.initial_balance + delta[0]

        for i in range(1, sim_length):
            balance[i] = balance[i - 1] + delta[i]

        print(max(balance))
        print(min(balance))
        print(balance)
        self.balance = balance
        # Create dates
        self._display_graphic(balance=balance)

        # Display Tables
        self._display_tables()

    def _create_transaction_array(self, transaction: ExpectedTransaction) -> (np.ndarray, np.ndarray):
        """
        Create a numpy array with the values associated to a specific transaction on time.

        Args:
            transaction (ExpectedTransaction) : The transaction to transform

        Returns:
            array_days (np.ndarray) : Array representing the value of the transaction on each day
            array_months (np.ndarray) : Array representing the value of the transaction on each month
        """

        # Create arrays representing each day and month . Add 1 for including start and end.
        # The array represents [(initial_date,value),...,(final_date,value)] or
        # [(initial_month,value),..,(final_month,value)]
        array_days: np.ndarray = np.zeros((self.simulation_final_date - self.simulation_initial_date).days + 1)
        array_months: np.ndarray = np.zeros(diffMonth(self.simulation_final_date, self.simulation_initial_date) + 1)

        # Handle case in which the initial date of transaction is inferior. Put it to the earliest date possible.
        initial_date = transaction.initial_date
        if initial_date < self.simulation_initial_date:
            initial_date = self.simulation_initial_date

        # Handle case in which the final date of transaction is not specified. Put it to the latest date possible.
        if transaction.final_date is None:
            transaction.final_date = self.simulation_final_date + relativedelta(months=1)

        # Compute points where to put transaction
        while initial_date < self.simulation_final_date:

            if initial_date > transaction.final_date:
                break

            # Compute point to use in array
            day_point: int = (initial_date - self.simulation_initial_date).days
            month_point: int = diffMonth(initial_date, self.simulation_initial_date)
            # Add in arrays
            array_days[day_point] = transaction.value
            array_months[month_point] = transaction.value

            # Compute next month
            if transaction.recurrency == None:
                break

            initial_date = initial_date + transaction.recurrency

        return array_days, array_months

    def _recalculateTables(self):
        pass

    def _display_graphic(self, balance: np.ndarray) -> plt.axis:
        dates = self._get_simulation_dates()

        # Create tables
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(dates, balance)

        # Format
        ax.set_xlim([dates[0], dates[-1]])
        ax.set_ylim([0, None])

        # formatters' options
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonthday=9))
        ax.xaxis.set_major_formatter(NullFormatter())
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%b'))

        ax.set_title("Balance evolution")

        return ax

    def _display_tables(self):
        # Get tables from dictionary
        expenses: pd.DataFrame = self._tables_days[Types.Expense]
        incomes: pd.DataFrame = self._tables_days[Types.Income]
        # Group by year and month and sort by them
        monthly_expenses = self._group_by_year_month(expenses)
        monthly_incomes = self._group_by_year_month(incomes)
        # Add total
        monthly_expenses["_Total_"] = monthly_expenses.sum(axis=1)
        monthly_incomes["_Total_"] = monthly_incomes.sum(axis=1)

        # Print

    def get_graphic_balance(self):
        dates = self._get_simulation_dates()

        # Create tables
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(dates, self.balance)

        # Format
        ax.set_xlim([dates[0], dates[-1]])
        ax.set_ylim([0, None])

        # formatters' options
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonthday=9))
        ax.xaxis.set_major_formatter(NullFormatter())
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%b'))

        ax.set_title("Balance evolution")

        return fig


    def get_month_tables(self):
        # Get tables from dictionary
        expenses: pd.DataFrame = self._tables_days[Types.Expense]
        incomes: pd.DataFrame = self._tables_days[Types.Income]
        # Group by year and month and sort by them
        monthly_expenses = self._group_by_year_month(expenses)
        monthly_incomes = self._group_by_year_month(incomes)
        # Add total
        monthly_expenses["_Total_"] = monthly_expenses.sum(axis=1)
        monthly_incomes["_Total_"] = monthly_incomes.sum(axis=1)

        return monthly_expenses, monthly_incomes

    def _group_by_year_month(self, table: pd.DataFrame):

        table.index = self._get_simulation_dates()
        grouped = table.groupby(by=[table.index.year, table.index.month]).sum().sort_index()
        return grouped

    def _get_simulation_dates(self):
        """
        Get the dates of the simulation. It  from the specified initial date to the specified final date.

        Returns:
            dates (pd.DatetimeIndex) : The dates of the simulation
        """
        sim_length = (self.simulation_final_date - self.simulation_initial_date).days + 1
        dates = pd.date_range(self.simulation_initial_date, self.simulation_final_date, sim_length)
        return dates


if __name__ == '__main__':
   pass
