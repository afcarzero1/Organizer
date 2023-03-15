from Handler.BudgetHandler import Types,BudgetHandler, ExpectedTransaction
import streamlit as st
from dateutil.relativedelta import relativedelta

st.set_page_config(
    page_title="Budget",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

import st_aggrid as ag


@st.cache_resource
def create_budget_handler() -> BudgetHandler:
    budget_handler = BudgetHandler()

    return budget_handler


def main():
    st.title("Expected Transaction Input Form")

    # Instantiate the budget handler
    budget_handler = create_budget_handler()

    col1, col2 = st.columns((1, 4))

    with col1:
        typec = st.selectbox("Type", [Types.Expense.value, Types.Income.value])
        category = st.text_input("Category")
        initial_date = st.date_input("Initial Date")
        recurrency_years = st.number_input("Recurrency (years)", min_value=0, max_value=100, step=1)
        recurrency_months = st.number_input("Recurrency (months)", min_value=0, max_value=11, step=1)
        recurrency_days = st.number_input("Recurrency (days)", min_value=0, max_value=30, step=1)
        recurrency = relativedelta(years=recurrency_years, months=recurrency_months, days=recurrency_days)
        value = st.number_input("Value", min_value=0., step=1.)
        final_date = st.date_input("Final Date (optional)", None)
        if recurrency_days == 0 and recurrency_months == 0 and recurrency_years == 0:
            recurrency = None
        print(type(typec))
        transaction = ExpectedTransaction(category=category,
                                          initial_date=initial_date,
                                          recurrency=recurrency,
                                          value=value,
                                          final_date=final_date)
        if st.button("Add Transaction"):


            if typec == Types.Expense.value:
                typec = Types.Expense
            else:
                typec = Types.Income

            budget_handler.add_expected_transaction(transaction, typec)
            budget_handler.compute_balances()
            st.success("Transaction added successfully.")

    with col2:

        fig = budget_handler.get_graphic_balance()
        st.pyplot(fig)

        expense_table,income_table = budget_handler.get_month_tables()

        print(expense_table)
        print(income_table)

        st.header("Expenses")
        st.table(expense_table.style.set_properties(**{'font-size': '12pt', 'font-family': 'Calibri'}).set_caption("Your Title"))

        pass

    st.write("Transaction Details:")
    st.write(transaction)


if __name__ == "__main__":
    main()
