import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tailor Tracker", layout="wide")


@st.cache_data
def load_orders():
    # read the orders file and turn the date columns into real dates
    return pd.read_csv("orders.csv", parse_dates=["order_date", "due_date"])


def get_alert(row):
    # delivered orders never need an alert
    if row["status"] == "Delivered":
        return ""
    if row["days_left"] < 0:
        return "OVERDUE"
    if row["days_left"] <= 3:
        return "DUE SOON"
    return ""


def highlight(row):
    # color the whole row red or orange based on the alert
    if row["Alert"] == "OVERDUE":
        color = "background-color: #f8d7da"
    elif row["Alert"] == "DUE SOON":
        color = "background-color: #ffe5b4"
    else:
        color = ""
    return [color] * len(row)


# sidebar menu (we will add more pages here later)
page = st.sidebar.radio("Go to", ["Orders"])

if page == "Orders":
    st.title("Orders")
    orders = load_orders()

    # work out how many days are left until each due date
    today = pd.Timestamp.today().normalize()
    orders["days_left"] = (orders["due_date"] - today).dt.days
    orders["Alert"] = orders.apply(get_alert, axis=1)

    # summary numbers at the top
    col1, col2, col3 = st.columns(3)
    col1.metric("Open orders", int((orders["status"] != "Delivered").sum()))
    col2.metric("Due in 3 days", int((orders["Alert"] == "DUE SOON").sum()))
    col3.metric("Overdue", int((orders["Alert"] == "OVERDUE").sum()))

    # filter by status
    statuses = sorted(orders["status"].unique())
    chosen = st.multiselect("Status", statuses, default=statuses)
    shown = orders[orders["status"].isin(chosen)].sort_values("due_date")

    # pick the columns to show and make the dates look clean
    table = shown[["order_id", "customer", "outfit", "price", "due_date",
                   "days_left", "status", "assigned_to", "Alert"]].copy()
    table["due_date"] = table["due_date"].dt.date

    # delivered orders have no days left, so leave that cell blank
    table["days_left"] = table["days_left"].astype("Int64")
    table.loc[table["status"] == "Delivered", "days_left"] = pd.NA

    st.dataframe(table.style.apply(highlight, axis=1).format(na_rep=""),
                 use_container_width=True, hide_index=True)