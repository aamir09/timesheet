import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# ------------------------------------------------------------------------------
# DATABASE OPERATIONS
# ------------------------------------------------------------------------------

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
            work_date TEXT UNIQUE,
            hours_worked REAL,
            month_name TEXT
        )
    """)
    conn.commit()

def add_data(work_date, hours_worked, month_name):
    """
    Insert or update a record into the timesheet table.
    If an entry exists for the same date, REPLACE it.
    """
    c.execute(
        """
        INSERT OR REPLACE INTO timesheet (id, work_date, hours_worked, month_name)
        VALUES (
            (SELECT id FROM timesheet WHERE work_date = ?),
            ?,
            ?,
            ?
        )
        """,
        (work_date, work_date, hours_worked, month_name)
    )
    conn.commit()

def get_months():
    """
    Retrieve the distinct months from the timesheet table, sorted.
    """
    c.execute("SELECT DISTINCT month_name FROM timesheet ORDER BY month_name")
    results = c.fetchall()
    return [row[0] for row in results]

def get_timesheet_by_month(month):
    """
    Retrieve all rows that match the selected month, ordered by date.
    """
    c.execute(
        "SELECT work_date, hours_worked, month_name FROM timesheet WHERE month_name = ? ORDER BY work_date",
        (month,)
    )
    data = c.fetchall()
    return data

def get_all_dates():
    """
    Retrieve all distinct dates from the timesheet table, ordered by date.
    """
    c.execute("SELECT DISTINCT work_date FROM timesheet ORDER BY work_date")
    data = c.fetchall()
    return [row[0] for row in data]

def get_hours_for_date(date_str):
    """
    Retrieve hours_worked for a particular date.
    """
    c.execute("SELECT hours_worked FROM timesheet WHERE work_date = ?", (date_str,))
    row = c.fetchone()
    return row[0] if row else 0.0

def update_hours_for_date(date_str, new_hours):
    """
    Update the hours_worked for a specific date.
    """
    # Recompute the month name from the date (in case it changed, though unlikely).
    month_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B")
    c.execute(
        "UPDATE timesheet SET hours_worked = ?, month_name = ? WHERE work_date = ?",
        (new_hours, month_name, date_str)
    )
    conn.commit()

# ------------------------------------------------------------------------------
# STREAMLIT APP
# ------------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Raise Diversity Timesheet", layout="centered")

    # -- STEP 1: Read the password from an environment variable
    password_env = os.environ.get("TIMESHEET_PASSWORD")
    if not password_env:
        st.error("No password found in environment variable 'TIMESHEET_PASSWORD'.")
        st.stop()

    # -- STEP 2: Initialize session state for login
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["has_edit_access"] = False

    # -- STEP 3: If not logged in, show login form
    if not st.session_state["logged_in"]:
        st.title("Login to Timesheet App")
        input_user = st.text_input("Username")
        input_pass = st.text_input("Password", type="password")

        if st.button("Login"):
            # Only valid username => 'raisediversity'
            # Only valid password => matches environment variable
            if input_user == "raisediversity" and input_pass == password_env:
                st.session_state["logged_in"] = True
                st.session_state["username"] = input_user
                # For this specific user, grant edit access
                st.session_state["has_edit_access"] = True
                st.rerun()  # Refresh the app
            else:
                st.error("Invalid credentials. Please try again.")
        # Stop execution until the user logs in
        st.stop()

    # -- STEP 4: If logged in, display the rest of the app
    st.title(f"Timesheet App – Logged in as {st.session_state['username']}")

    # Create table if not exists
    create_table()

    # Build menu
    menu_options = ["View Timesheet", "Log Hours"]
    # Only show Edit Hours if user has edit access
    if st.session_state["has_edit_access"]:
        menu_options.append("Edit Hours")

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

            # Display data for the chosen month
            if selected_month:
                data = get_timesheet_by_month(selected_month)
                if data:
                    df = pd.DataFrame(data, columns=["Date", "Hours Worked", "Month"])
                    st.dataframe(df)

                    # CSV download
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download Timesheet",
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

    # -------------
    # EDIT HOURS
    # -------------
    elif choice == "Edit Hours":
        # Double-check the user has permission (should always be True if we got here).
        if not st.session_state["has_edit_access"]:
            st.error("You do not have permission to edit hours.")
            st.stop()

        st.subheader("Edit Hours for a Date")

        all_dates = get_all_dates()
        if all_dates:
            # Select the date you want to edit
            selected_date = st.selectbox("Select a date to edit", all_dates)

            if selected_date:
                # Fetch current hours
                current_hours = get_hours_for_date(selected_date)
                st.write(f"Current hours for {selected_date}: **{current_hours}**")

                # Input to update the hours
                new_hours = st.number_input(
                    "Enter new hours",
                    min_value=0.0,
                    value=float(current_hours),
                    format="%.2f"
                )

                if st.button("Update Hours"):
                    update_hours_for_date(selected_date, new_hours)
                    st.success(f"Updated hours for {selected_date} to {new_hours}!")
        else:
            st.info("No data to edit yet. Please log some hours first.")


if __name__ == "__main__":
    main()
