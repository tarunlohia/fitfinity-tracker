import streamlit as st
import pandas as pd
import gspread
import base64
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# ---------------- GOOGLE SHEET SETUP ----------------
SHEET_ID = "1t6L2WkMQJwz9HTaMiyGqTwinuc1v2EWtUMqJlNPmoYc"
MEMBERS_TAB = "Current Members"
RENEWALS_TAB = "Renewal History"

# Use credentials from Streamlit Secrets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["google"]["creds"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
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

# ------------------- HEADER -------------------
def load_base64_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

image_path = "d74072e2-84e6-4aec-b17e-feb6fb563480.png"
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

# ✅ You can now copy this entire code and replace it in GitHub directly.
