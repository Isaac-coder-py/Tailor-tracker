import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Tailor Tracker", layout="wide")

TODAY = pd.Timestamp.today().normalize()


@st.cache_data
def load_orders():
    # read the orders file and turn the date columns into real dates
    return pd.read_csv("orders.csv",
                       parse_dates=["order_date", "due_date", "delivered_date"])


def get_timing(row):
    # was the order delivered early, on time, or late?
    if row["status"] == "Delivered":
        if row["delivered_date"] < row["due_date"]:
            return "Early"
        if row["delivered_date"] > row["due_date"]:
            return "Late"
        return "On time"
    # not delivered yet: late only if the due date has already passed
    if row["due_date"] < TODAY:
        return "Late"
    return "Not due yet"


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
    # color the whole row red or orange, with dark text so it stays readable
    if row["Alert"] == "OVERDUE":
        color = "background-color: #f8d7da; color: #000000"
    elif row["Alert"] == "DUE SOON":
        color = "background-color: #ffe5b4; color: #000000"
    else:
        color = ""
    return [color] * len(row)


# sidebar menu (we will add more pages here later)
page = st.sidebar.radio("Go to", ["Dashboard", "Orders"])

if page == "Dashboard":
    st.title("Dashboard")
    orders = load_orders()
    orders["timing"] = orders.apply(get_timing, axis=1)

    # the main numbers
    total_orders = len(orders)
    revenue = orders.loc[orders["status"] == "Delivered", "price"].sum()
    late_pct = (orders["timing"] == "Late").mean() * 100
    early_pct = (orders["timing"] == "Early").mean() * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total orders", total_orders)
    col2.metric("Total revenue", f"₦{revenue:,.0f}")
    col3.metric("Late orders", f"{late_pct:.0f}%")
    col4.metric("Early orders", f"{early_pct:.0f}%")
    st.caption("Late means delivered after the due date, or still not delivered "
               "after the due date. Early means delivered before the due date. "
               "Percentages are out of all orders. Revenue counts delivered orders only.")

    # pie chart of order timing
    st.subheader("Order timing")
    slices = ["Early", "On time", "Late", "Not due yet"]
    counts = orders["timing"].value_counts().reindex(slices, fill_value=0).reset_index()
    counts.columns = ["timing", "orders"]
    pie = alt.Chart(counts).mark_arc().encode(
        theta="orders:Q",
        color=alt.Color("timing:N", sort=slices,
                        scale=alt.Scale(domain=slices,
                                        range=["#2e8b57", "#4682b4", "#d9534f", "#9e9e9e"])),
        tooltip=["timing", "orders"],
    )
    st.altair_chart(pie, use_container_width=True)

    # average rating for each tailor (only delivered orders have ratings)
    st.subheader("Tailor ratings")
    ratings = (orders.dropna(subset=["rating"])
               .groupby("assigned_to")["rating"]
               .agg(["mean", "count"])
               .reset_index())
    ratings.columns = ["Tailor", "Average rating (out of 5)", "Orders rated"]
    ratings["Average rating (out of 5)"] = ratings["Average rating (out of 5)"].round(1)
    ratings = ratings.sort_values("Average rating (out of 5)", ascending=False)
    st.dataframe(ratings, hide_index=True, use_container_width=True)

if page == "Orders":
    st.title("Orders")
    orders = load_orders()

    # work out how many days are left until each due date
    orders["days_left"] = (orders["due_date"] - TODAY).dt.days
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

    # delivered orders have no days left, so show "Done" instead of a number
    table["days_left"] = table["days_left"].astype(str)
    table.loc[table["status"] == "Delivered", "days_left"] = "Done"

    st.dataframe(table.style.apply(highlight, axis=1),
                 use_container_width=True, hide_index=True)
