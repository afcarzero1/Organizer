import sys

sys.path.insert(0, "./pages/databases")

import datetime
import time

import streamlit as st
import pandas as pd
from st_aggrid import GridOptionsBuilder

#from db_funcs import DataBasehandler
from PIL import Image
import plotly.express as px
import st_aggrid as ag
from db_tasks import DataBasehandler


def color_df(val):
    if val == "Done":
        color = "green"
    elif val == "Doing":
        color = "orange"
    else:
        color = "red"

    return f'background-color: {color}'


st.set_page_config(
    page_title="ToDo",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)


## HELPER FUNCTIONS ##
@st.cache_data
def get_images():
    top_image = Image.open('static/banner_top.png')
    bottom_image = Image.open('static/banner_bottom.png')
    main_image = Image.open('static/main_banner.png')

    return top_image, bottom_image, main_image


@st.cache_data
def create_table_wrapper():
    DataBasehandler.create_table()


def get_data(data_changed: int) -> pd.DataFrame:
    result = DataBasehandler.view_all_data()
    clean_df = pd.DataFrame(result, columns=DataBasehandler.COLUMNS_NAMES)

    return clean_df


# Set the images
top_image, bottom_image, main_image = get_images()

st.image(main_image, use_column_width='always')
st.title("📄 ToDo App 🗣")

st.sidebar.image(top_image, use_column_width='auto')
choice = st.sidebar.selectbox("Menu", ["Create Task ✅", "Update Task 👨‍💻", "Delete Task ❌", "View Tasks' Status 👨‍💻"])
st.sidebar.image(bottom_image, use_column_width='auto')
create_table_wrapper()

## DIVISION BY PAGES ##

if choice == "Create Task ✅":
    result = DataBasehandler.view_all_data()
    print(result)
    clean_df = pd.DataFrame(result, columns=DataBasehandler.COLUMNS_NAMES)
    print(clean_df)
    table = ag.AgGrid(clean_df,
                      fit_columns_on_grid_load=True)
    st.subheader("Add Item")
    col1, col2 = st.columns(2)

    with col1:
        task = st.text_area("Task To Do")
        task_category = st.selectbox("Category", ["Personal"])
        task_estimated_time = st.slider("Estimated Time",
                                        min_value=0.5,
                                        max_value=3.,
                                        value=0.5,
                                        step=0.5)

    with col2:
        task_status = st.selectbox("Status", ["ToDo", "Doing", "Done"])
        task_priority = st.selectbox("Priority", ["High", "Middle", "Low"])

        task_due_date = st.date_input("Due Date")

    if st.button("Add Task"):
        DataBasehandler.add_data(task=task,
                                 task_status=task_status,
                                 task_priority=DataBasehandler.str_to_priority(task_priority),
                                 task_due_date=task_due_date,
                                 task_estimated_time=task_estimated_time,
                                 task_category=task_category
                                 )

        st.success("Added Task \"{}\" ✅".format(task))
        st.balloons()
        st.experimental_rerun()

elif choice == "Update Task 👨‍💻":
    st.subheader("Edit Items")

    result = DataBasehandler.view_all_data()
    clean_df = pd.DataFrame(result, columns=DataBasehandler.COLUMNS_NAMES)

    # Build the table
    gb = GridOptionsBuilder.from_dataframe(clean_df)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    table_selection = ag.AgGrid(clean_df,
                                gridOptions=gb.build(),
                                checkbox_selection=True,
                                fit_columns_on_grid_load=True)

    task_to_modify = table_selection['selected_rows']
    if len(task_to_modify) > 0:
        task_to_modify = task_to_modify[0]
        print(task_to_modify)

        col1, col2 = st.columns(2)

        with col1:
            task = st.text_area("Task To Do", task_to_modify[DataBasehandler.COLUMNS_NAMES[1]])
            task_category = st.selectbox("Category", ["Personal"])
            task_estimated_time = st.slider("Estimated Time",
                                            min_value=0.5,
                                            max_value=5.,
                                            value=float(task_to_modify[DataBasehandler.COLUMNS_NAMES[5]]),
                                            step=0.5)

        with col2:
            task_status = st.selectbox("Status",
                                       ["ToDo", "Doing", "Done"],
                                       DataBasehandler.str_to_status(task_to_modify[DataBasehandler.COLUMNS_NAMES[3]])
                                       )
            task_priority = st.selectbox("Priority",
                                         ["High", "Middle", "Low"],
                                         DataBasehandler.str_to_priority(
                                             task_to_modify[DataBasehandler.COLUMNS_NAMES[2]]))

            print(task_to_modify[DataBasehandler.COLUMNS_NAMES[4]])
            print(type(task_to_modify[DataBasehandler.COLUMNS_NAMES[4]]))
            date_obj = datetime.datetime.strptime(task_to_modify[DataBasehandler.COLUMNS_NAMES[4]], "%Y-%m-%d")
            task_due_date = st.date_input("Date", date_obj)

        if st.button("Update"):
            st.warning("Updating Selected Tasks")
            id = task_to_modify[DataBasehandler.COLUMNS_NAMES[0]]

            DataBasehandler.edit_task_data(id, task, task_priority, task_status, task_due_date,
                                           task_estimated_time, task_category)

            time.sleep(5)
            st.experimental_rerun()





elif choice == "Delete Task ❌":
    st.subheader("Delete")
    result = DataBasehandler.view_all_data()
    clean_df = pd.DataFrame(result, columns=DataBasehandler.COLUMNS_NAMES)

    # Build the table
    gb = GridOptionsBuilder.from_dataframe(clean_df)
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    table_selection = ag.AgGrid(clean_df,
                                gridOptions=gb.build(),
                                checkbox_selection=True,
                                fit_columns_on_grid_load=True)

    print(table_selection['selected_rows'])

    if st.button("Delete task"):
        st.warning("Deleting Selected Tasks")
        for task in table_selection["selected_rows"]:
            DataBasehandler.delete_data(task[DataBasehandler.COLUMNS_NAMES[0]])

        time.sleep(5)
        st.experimental_rerun()

    with st.expander("View Data"):
        pass


else:
    result = DataBasehandler.view_all_data()
    print(result)
    clean_df = pd.DataFrame(result, columns=DataBasehandler.COLUMNS_NAMES)
    print(clean_df)
    table = ag.AgGrid(clean_df,
                      fit_columns_on_grid_load=True)
    with st.expander("View All 📝"):
        pass

    with st.expander("Task Status 📝"):
        pass
        # task_df = clean_df['Status'].value_counts().to_frame()
        # task_df = task_df.reset_index()
        # st.dataframe(task_df)

        # p1 = px.pie(task_df, names='index', values='Status', color='index',
        #            color_discrete_map={'ToDo': 'red',
        #                                'Done': 'green',
        #                                'Doing': 'orange'})
        # st.plotly_chart(p1, use_container_width=True)
