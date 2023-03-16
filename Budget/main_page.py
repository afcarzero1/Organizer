import numpy as np

from Handler.BudgetHandler import Types, BudgetHandler, ExpectedTransaction
import streamlit as st
from dateutil.relativedelta import relativedelta

st.set_page_config(
    page_title="Budget",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def create_budget_handler() -> BudgetHandler:
    budget_handler = BudgetHandler()

    return budget_handler

def display_metrics(budget_handler: BudgetHandler):

    col1, col2, col3, col4 = st.columns((1, 1, 1, 1))

    with col1:
        st.metric("Minimum Balance", np.min(budget_handler.balance), delta = np.min(budget_handler.balance) - budget_handler.initial_balance)

    with col2:
        st.metric("Maximum Balance", np.max(budget_handler.balance), delta = np.max(budget_handler.balance) - budget_handler.initial_balance)

    with col3:
        st.metric("Total Expenses",budget_handler.total_expenses)

    with col4:
        st.metric("Total Incomes",budget_handler.total_incomes)


def main():
    # Instantiate the budget handler
    budget_handler = create_budget_handler()

    st.title("Expected Transaction Input Form")

    st.header("General Parameters")

    # Initial balance
    col1, col2, col3 = st.columns((1, 1, 1))
    with col1:
        initial_balance = st.number_input("Initial Balance", min_value=0., step=100., value=10000.)
        budget_handler.initial_balance = initial_balance

    with col2:
        start_date = st.date_input("Start Date", value=budget_handler.start_date)
        budget_handler.start_date = start_date

    with col3:
        end_date = st.date_input("End Date", value=budget_handler.end_date)
        budget_handler.end_date = end_date

    col1, col2 = st.columns((2, 4))

    with col1:
        st.header("Add Transaction")
        typec = st.selectbox("Type", [Types.Expense.value, Types.Income.value])
        category = st.text_input("Category")
        initial_date = st.date_input("Initial Date")

        # Handle recurrency of the transaction

        subcol1, subcol2, subcol3 = st.columns((1, 1, 1))
        with subcol1:
            recurrency_years = st.number_input("Recurrency (years)", min_value=0, max_value=100, step=1)
        with subcol2:
            recurrency_months = st.number_input("Recurrency (months)", min_value=0, max_value=11, step=1)
        with subcol3:
            recurrency_days = st.number_input("Recurrency (days)", min_value=0, max_value=30, step=1)

        recurrency = relativedelta(years=recurrency_years, months=recurrency_months, days=recurrency_days)

        # Value of the transaction
        value = st.number_input("Value", min_value=0., step=1.)

        # Final date
        agree = st.checkbox('Final Date?')
        if agree:
            final_date = st.date_input("Final Date (optional)", None)
        else:
            final_date = None

        # Handle case of not recurrencies
        if recurrency_days == 0 and recurrency_months == 0 and recurrency_years == 0:
            recurrency = None

        # Create the transaction
        transaction = ExpectedTransaction(category=category,
                                          initial_date=initial_date,
                                          recurrency=recurrency,
                                          value=value,
                                          final_date=final_date)

        # Add the transaction
        if st.button("Add Transaction"):
            # Convert the type to the enum
            if typec == Types.Expense.value:
                typec = Types.Expense
            else:
                typec = Types.Income

            budget_handler.add_expected_transaction(transaction, typec)
            budget_handler.compute_balances()
            st.success("Transaction added successfully.")

    with col2:
        # Get the graphic of the balance
        fig = budget_handler.get_graphic_balance()
        display_metrics(budget_handler)
        st.pyplot(fig)

        # Get the tables
        expense_table, income_table = budget_handler.get_month_tables()

        with st.expander("Expenses"):
            st.table(expense_table.style.set_properties(**{'font-size': '12pt', 'font-family': 'Calibri'}).set_caption(
                "Expenses"))

        with st.expander("Incomes"):
            st.table(income_table.style.set_properties(**{'font-size': '12pt', 'font-family': 'Calibri'}).set_caption(
                "Your Title"))

    st.write("Transaction Details:")
    st.write(transaction)


if __name__ == "__main__":
    main()
