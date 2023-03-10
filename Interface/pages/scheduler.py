import datetime
import sys
import time

sys.path.insert(0, "./pages/databases")
sys.path.insert(0, "./databases")
import streamlit as st
from db_schedule import ScheduleDatabase
import pandas as pd
import st_aggrid as ag

st.set_page_config(
    page_title="Scheduler",
    page_icon="⏰",
)


@st.cache_data
def create_database_wrapper():
    ScheduleDatabase.create_table()


def check_data(start_time: datetime.time,
               end_time: datetime.time,
               existing_data: pd.DataFrame
               ) -> bool:
    """
    Check if the data is consistent and can be added.

    Args:
        start_time (datetime.time) : The starting time to be added
        end_time (datetime.time) : the ending time
        existing_data (pd.Dataframe) : Dataframe with already existing intervals

    """

    def check_overlap(time1_start, time1_end, time2_start, time2_end):
        # Check if time1 overlaps with time2
        if time1_start < time2_end and time1_end > time2_start:
            return True

        # Check if time2 overlaps with time1
        if time2_start < time1_end and time2_end > time1_start:
            return True

        if time1_start == time2_start or time1_end == time2_end:
            return False

        # If neither comparison indicates an overlap, then there is no overlap
        return False

    if end_time <= start_time:
        return False

    starting_times = existing_data["START"]
    ending_times = existing_data["END"]

    for existing_st, existing_et in zip(starting_times, ending_times):
        existing_st = datetime.datetime.strptime(existing_st, '%H:%M:%S').time()
        existing_et = datetime.datetime.strptime(existing_et, '%H:%M:%S').time()

        if check_overlap(start_time, end_time,
                         existing_st, existing_et):
            return False

    return True


#  Create the database
create_database_wrapper()

st.header("Scheduler ⏰")
st.write("Introduce here the schedule you would like to have")

result = ScheduleDatabase.view_all_data()
clean_df = pd.DataFrame(result, columns=ScheduleDatabase.COLUMNS_NAMES)

# Build the table
gb = ag.GridOptionsBuilder.from_dataframe(clean_df)
gb.configure_selection(selection_mode="single", use_checkbox=True)
table_selection = ag.AgGrid(clean_df,
                            gridOptions=gb.build(),
                            checkbox_selection=True,
                            fit_columns_on_grid_load=True)


if len(table_selection['selected_rows']) > 0:
    if st.button("Delete"):
        for selected_row in table_selection['selected_rows']:
            ScheduleDatabase.delete_data(selected_row[ScheduleDatabase.COLUMNS_NAMES[0]])

        st.warning("Deleted")
        time.sleep(2)
        st.experimental_rerun()

with st.expander("Create New Schedule"):
    start_date = st.time_input("Start")
    end_date = st.time_input("End")
    sch_type = st.selectbox("Type", ["Work", "Free"])

    print(start_date)
    print(end_date)
    print(type(start_date))

    # Add some checks here
    if st.button("Add"):
        if check_data(start_date, end_date, clean_df):
            ScheduleDatabase.add_data(sch_type, start_date, end_date)
            st.success("Data was added!")
            time.sleep(2)
            st.experimental_rerun()
        else:
            st.error("There is an overlap! (or data is invalid)")
