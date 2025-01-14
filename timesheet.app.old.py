import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ------------------------------
# DATABASE OPERATIONS
# ------------------------------

# Create a connection to the SQLite database
# `check_same_thread=False` allows usage from within Streamlit
conn = sqlite3.connect("timesheet.db", check_same_thread=False)
c = conn.cursor()

def create_table():
    """
    Create the timesheet table if it doesn't already exist.
    """
    c.execute("""
        CREATE TABLE IF NOT EXISTS timesheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT,
            hours_worked REAL,
            month_name TEXT
        )
    """)
    conn.commit()

def add_data(work_date, hours_worked, month_name):
    """
    Insert a record into the timesheet table.
    """
    c.execute(
        "INSERT INTO timesheet (work_date, hours_worked, month_name) VALUES (?,?,?)",
        (work_date, hours_worked, month_name)
    )
    conn.commit()

def get_months():
    """
    Retrieve the distinct months from the timesheet table.
    """
    c.execute("SELECT DISTINCT month_name FROM timesheet")
    results = c.fetchall()
    return [row[0] for row in results]

def get_timesheet_by_month(month):
    """
    Retrieve all rows that match the selected month.
    """
    c.execute("SELECT work_date, hours_worked, month_name FROM timesheet WHERE month_name = ?", (month,))
    data = c.fetchall()
    return data

# ------------------------------
# STREAMLIT APP
# ------------------------------

def main():
    st.title("Aamir's Timesheet")

    # Initialize the table (create if not exists)
    create_table()

    # Sidebar for navigation
    menu_options = ["View Timesheet", "Log Hours"]
    choice = st.sidebar.selectbox("Menu", menu_options)

    # ---------------
    # VIEW TIMESHEET
    # ---------------
    if choice == "View Timesheet":
        st.subheader("Timesheet")

        # Fetch existing months from the DB
        months = get_months()

        if len(months) == 0:
            st.info("No data available. Please log some hours first.")
        else:
            # Month selector
            selected_month = st.selectbox("Select a month", months)

            # If a month is selected, display data
            if selected_month:
                data = get_timesheet_by_month(selected_month)
                if data:
                    df = pd.DataFrame(data, columns=["Date", "Hours Worked", "Month"])
                    st.dataframe(df)

                    # Provide CSV download functionality
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download Timesheet as CSV",
                        data=csv_data,
                        file_name=f"timesheet_{selected_month}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info(f"No entries found for the month: {selected_month}")

    # -----------
    # LOG HOURS
    # -----------
    elif choice == "Log Hours":
        st.subheader("Log Your Hours")
        
        # Date input (defaults to today's date)
        input_date = st.date_input("Select Date", datetime.now())
        # Number input for hours worked
        hours_worked = st.number_input("Enter Hours", min_value=0.0, format="%.2f")

        # Convert the selected date into a more readable month name
        month_name = input_date.strftime("%B")

        # Button to log the data
        if st.button("Log Hours"):
            add_data(
                work_date=input_date.strftime("%Y-%m-%d"),
                hours_worked=hours_worked,
                month_name=month_name
            )
            st.success("Hours logged successfully!")

if __name__ == '__main__':
    main()
