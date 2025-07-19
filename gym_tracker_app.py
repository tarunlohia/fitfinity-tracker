import streamlit as st
import pandas as pd
import gspread
import base64
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# ---------------- GOOGLE SHEET SETUP ----------------
SHEET_ID = "1t6L2WkMQJwz9HTaMiyGqTwinuc1v2EWtUMqJlNPmoYc"
MEMBERS_TAB = "Current Members"
RENEWALS_TAB = "Renewal History"

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("creds.json", scopes=scope)
client = gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_worksheet():
    sheet = client.open_by_key(SHEET_ID)
    members_ws = sheet.worksheet(MEMBERS_TAB)
    renewals_ws = sheet.worksheet(RENEWALS_TAB)
    return members_ws, renewals_ws

members_ws, renewals_ws = get_worksheet()

# ---------------- UTILITY FUNCTIONS ----------------
def load_data():
    df = pd.DataFrame(members_ws.get_all_records())
    if not df.empty:
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors='coerce')
        df["End Date"] = pd.to_datetime(df["End Date"], errors='coerce')
        df["Renewed On"] = pd.to_datetime(df["Renewed On"], errors='coerce')
    return df

def save_member(data):
    members_ws.append_row([str(item) for item in data])

def save_renewal(data):
    renewals_ws.append_row([str(item) for item in data])

def get_status(end_date):
    today = datetime.today().date()
    if pd.isnull(end_date):
        return "Unknown"
    if end_date < today:
        return "Expired"
    elif today <= end_date <= today + timedelta(days=7):
        return "Expiring Soon"
    else:
        return "Active"

def delete_member(member_id):
    all_members = members_ws.get_all_records()
    for idx, member in enumerate(all_members):
        if str(member["Member ID"]) == str(member_id):
            members_ws.delete_rows(idx + 2)
            return True
    return False

def update_member(member_id, field, new_value):
    headers = members_ws.row_values(1)
    field_index = headers.index(field) + 1
    all_members = members_ws.get_all_records()
    for idx, member in enumerate(all_members):
        if str(member["Member ID"]) == str(member_id):
            members_ws.update_cell(idx + 2, field_index, new_value)
            return True
    return False

# ------------------- FITFINITY THEME HEADER -------------------
def load_base64_image(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
        return base64.b64encode(data).decode()

image_path = "logo.jpg"
image_base64 = load_base64_image(image_path)

st.markdown(f'''
    <div style="text-align:center;">
        <img src="data:image/png;base64,{image_base64}" alt="Logo" style="width:200px; margin-bottom:10px;">
        <h1 style="color:white; white-space:nowrap;">FITFINITY Membership Tracker</h1>
    </div>
''', unsafe_allow_html=True)

st.markdown("""<style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    .stButton>button { background-color: #FFFFFF; color: #000000; }
    .stTextInput>div>input,
    .stSelectbox>div>div>div,
    .stDateInput>div>input {
        background-color: #1c1c1c;
        color: white;
    }
    .stExpanderHeader {
        font-weight: bold;
        font-size: 16px;
    }
</style>""", unsafe_allow_html=True)

# ---------------- MAIN UI ----------------
tab1, tab2 = st.tabs(["\U0001F4CA Dashboard", "\u2795 Add / Renew"])

with tab1:
    st.header("Member Summary")
    df = load_data()

    if df.empty:
        st.info("No member data available.")
    else:
        df["Status"] = df["End Date"].dt.date.apply(get_status)

        col1, col2, col3 = st.columns(3)
        col1.metric("\u2705 Active Members", df[df["Status"] == "Active"].shape[0])
        col2.metric("\u26A0\uFE0F Expiring Soon", df[df["Status"] == "Expiring Soon"].shape[0])
        col3.metric("\u274C Expired", df[df["Status"] == "Expired"].shape[0])

        with st.expander("\U0001F4CB Full Member List"):
            df_display = df.copy()
            date_cols = ["Start Date", "End Date", "Renewed On"]
            for col in date_cols:
                df_display[col] = df_display[col].dt.strftime('%d-%b-%Y')
            st.dataframe(df_display)

        st.subheader("\U0001F50D Search Member")
        search_query = st.text_input("Enter Member ID, Name or Phone")

        if search_query:
            search_result = df[
                df.apply(lambda row: search_query.lower() in str(row["Member ID"]).lower()
                                        or search_query.lower() in row["Name"].lower()
                                        or search_query.lower() in str(row["Phone"]).lower(), axis=1)
            ]

            if not search_result.empty:
                for _, row in search_result.iterrows():
                    with st.expander(f"\U0001F464 {row['Name']} - ID: {row['Member ID']}"):
                        st.markdown(f"**Phone:** {row['Phone']}")
                        st.markdown(f"**Start Date:** {row['Start Date'].strftime('%d-%b-%Y') if pd.notnull(row['Start Date']) else 'N/A'}")
                        st.markdown(f"**End Date:** {row['End Date'].strftime('%d-%b-%Y') if pd.notnull(row['End Date']) else 'N/A'}")
                        st.markdown(f"**Status:** {row['Status']}")
                        st.markdown(f"**Renewed On:** {row['Renewed On'].strftime('%d-%b-%Y') if pd.notnull(row['Renewed On']) else 'N/A'}")

                        st.markdown("---")
                        st.markdown("### \u270F\uFE0F Edit Member")
                        field = st.selectbox("Select field to edit", ["Name", "Phone", "Start Date", "End Date", "Duration"], key=f"edit_{row['Member ID']}")
                        new_value = st.text_input("Enter new value", key=f"val_{row['Member ID']}")
                        if st.button(f"Update {field} for {row['Name']}", key=f"update_{row['Member ID']}"):
                            if update_member(row['Member ID'], field, new_value):
                                st.success("Member updated successfully!")
                            else:
                                st.error("Failed to update member.")

                        st.markdown("### \U0001F5D1\uFE0F Delete Member")
                        if st.button(f"Delete Member {row['Name']}", key=f"delete_{row['Member ID']}"):
                            if delete_member(row['Member ID']):
                                st.success("Member deleted successfully!")
                            else:
                                st.error("Failed to delete member.")
            else:
                st.warning("No matching member found.")

with tab2:
    option = st.radio("Choose action", ["New Member", "Renew Membership"])

    if option == "New Member":
        st.subheader("\u2795 Add New Member")
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        start_date = st.date_input("Start Date", datetime.today())
        duration = st.selectbox("Duration", ["3 Months", "6 Months", "12 Months"])

        if st.button("Add Member"):
            if not name or not phone:
                st.warning("Please enter all required fields.")
            else:
                months = int(duration.split()[0])
                end_date = start_date + pd.DateOffset(months=months)
                status = get_status(end_date.date())
                df_existing = load_data()
                member_id = 101 if df_existing.empty else int(df_existing["Member ID"].max()) + 1
                row = [member_id, name, phone, start_date.strftime('%d-%b-%Y'), duration,
                       end_date.strftime('%d-%b-%Y'), status, "", ""]
                save_member(row)
                st.success("Member added successfully!")

    else:
        st.subheader("\U0001F501 Renew Membership")
        df = load_data()
        names = df["Name"].tolist()
        selected_name = st.selectbox("Select Member", names)

        if selected_name:
            member_row = df[df["Name"] == selected_name].iloc[0]
            st.write(f"Current End Date: {member_row['End Date'].strftime('%d-%b-%Y') if pd.notnull(member_row['End Date']) else 'N/A'}")

            renewal_date = st.date_input("Renewal Date", datetime.today())
            renewal_duration = st.selectbox("Renewal Duration", ["3 Months", "6 Months", "12 Months"])

            if st.button("Renew Membership"):
                months = int(renewal_duration.split()[0])
                new_end_date = renewal_date + pd.DateOffset(months=months)
                status = get_status(new_end_date.date())
                renew_row = [
                    str(member_row["Member ID"]), selected_name, member_row["Phone"],
                    renewal_date.strftime('%d-%b-%Y'), renewal_date.strftime('%d-%b-%Y'),
                    renewal_duration, new_end_date.strftime('%d-%b-%Y'), ""
                ]
                save_renewal(renew_row)

                members = members_ws.get_all_records()
                for idx, mem in enumerate(members):
                    if mem["Name"] == selected_name:
                        members_ws.update_cell(idx + 2, 4, renewal_date.strftime('%d-%b-%Y'))
                        members_ws.update_cell(idx + 2, 5, renewal_duration)
                        members_ws.update_cell(idx + 2, 6, new_end_date.strftime('%d-%b-%Y'))
                        members_ws.update_cell(idx + 2, 7, status)
                        members_ws.update_cell(idx + 2, 8, renewal_date.strftime('%d-%b-%Y'))
                        break
                st.success("Membership renewed successfully!")
