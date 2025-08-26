import json
import re
from datetime import datetime, date
from dateutil import parser as dateparser

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============== Helpers ==============

def money_to_float(x):
    if x is None or x == "":
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x)
    s = re.sub(r"[^\d.\-]", "", s)  # remove currency symbols / commas
    try:
        return float(s) if s != "" else 0.0
    except ValueError:
        return 0.0

def num_or_zero(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def to_date(x):
    if x is None or str(x).strip() == "":
        return None
    try:
        return dateparser.parse(str(x), dayfirst=True).date()
    except Exception:
        return None

# ============== Auth / Sheets ==============

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    # Try to get credentials from environment variable first (for Render)
    import os
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")

    # If not in environment, try secrets (for local development)
    if not creds_json:
        try:
            creds_json = st.secrets["GOOGLE_CREDENTIALS_JSON"]
        except:
            st.error("No Google credentials found. Please set GOOGLE_CREDENTIALS_JSON environment variable.")
            return None

    creds_dict = json.loads(creds_json)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=300, show_spinner=False)
def load_all_data():
    gc = get_gspread_client()

    if gc is None:
        st.error("Failed to initialize Google Sheets client. Please check your credentials.")
        return None

    # Embedded sheet ID
    SHEET_ID = "1G_q_d4Kg35PWBWb49f5FWmoYAnA4k0TYAg4QzIM4N24"
    sh = gc.open_by_key(SHEET_ID)

    ws_raw = sh.worksheet("Raw Material Master")
    ws_in  = sh.worksheet("Stock In")
    ws_out = sh.worksheet("Stock Out")

    # Get all records
    raw_data = ws_raw.get_all_records()
    in_data = ws_in.get_all_records()
    out_data = ws_out.get_all_records()

    # Normalize column names
    raw_headers = [c.strip() for c in raw_data[0].keys()] if raw_data else []
    in_headers = [c.strip() for c in in_data[0].keys()] if in_data else []
    out_headers = [c.strip() for c in out_data[0].keys()] if out_data else []

    # Calculate totals
    total_in = sum(num_or_zero(record.get("Quantity", record.get("Quantity In", 0))) for record in in_data)
    total_out = sum(num_or_zero(record.get("Quantity Out", 0)) for record in out_data)

    # Calculate inventory value
    total_value = 0
    alert_count = 0

    for record in raw_data:
        current_stock = num_or_zero(record.get("Current Stock", 0))
        unit_cost = money_to_float(record.get("Cost per Unit", record.get("Avg. Cost per Unit", 0)))
        reorder_level = money_to_float(record.get("Reorder Level", 0))

        # Calculate inventory value
        total_value += current_stock * unit_cost

        # Check for alerts
        if (current_stock <= reorder_level or
            str(record.get("Re-Order Required", "")).strip().upper() == "YES" or
            current_stock == 0):
            alert_count += 1

    return {
        "total_products": len(raw_data),
        "total_in": total_in,
        "total_out": total_out,
        "total_value": total_value,
        "alert_count": alert_count,
        "raw_data": raw_data,
        "in_data": in_data,
        "out_data": out_data
    }

# ============== UI ==============

st.set_page_config(page_title="Inventory Dashboard", page_icon="📦", layout="wide")

# Load data
try:
    data = load_all_data()

    if data is None:
        st.error("Unable to load data. Please check your Google Sheets connection and credentials.")
        st.stop()

    # Header
    col_logo, col_title, col_alerts, col_refresh = st.columns([0.5, 4, 1.5, 1])
    with col_logo:
        st.markdown("### 📦")
    with col_title:
        st.markdown("## Inventory Dashboard")
    with col_alerts:
        bell = "🔔" if data["alert_count"] > 0 else "🔕"
        st.markdown(f"### {bell} {data['alert_count']}")
        with st.expander(f"View Alerts ({data['alert_count']})", expanded=False):
            if data["alert_count"] == 0:
                st.success("✅ All good — no items need reorder!")
            else:
                st.warning(f"⚠️ **{data['alert_count']} items need attention**")
                # Show simple alert list
                alert_items = []
                for record in data["raw_data"]:
                    current_stock = num_or_zero(record.get("Current Stock", 0))
                    reorder_level = money_to_float(record.get("Reorder Level", 0))
                    if (current_stock <= reorder_level or
                        str(record.get("Re-Order Required", "")).strip().upper() == "YES" or
                        current_stock == 0):
                        alert_items.append({
                            "Product": record.get("Product Name", record.get("RM ID", "Unknown")),
                            "Current Stock": current_stock,
                            "Reorder Level": reorder_level,
                            "Status": "Out of Stock" if current_stock == 0 else "Below Reorder Level"
                        })

                for item in alert_items:
                    st.write(f"• **{item['Product']}**: {item['Current Stock']} units ({item['Status']})")

    with col_refresh:
        if st.button("🔄 Refresh"):
            load_all_data.clear()
            st.toast("Data refreshed!")
            st.rerun()

    st.markdown("---")

    # KPI Cards
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Products", f"{data['total_products']:,}")
    k2.metric("Total Stock In", f"{int(data['total_in']):,}")
    k3.metric("Total Stock Out", f"{int(data['total_out']):,}")
    k4.metric("Inventory Value", f"₹{data['total_value']:,.0f}")
    k5.metric("Items Needing Reorder", f"{data['alert_count']}")

    st.markdown("---")

    # Simple data display
    tab1, tab2 = st.tabs(["📊 Inventory Overview", "📋 Raw Data"])

    with tab1:
        st.markdown("### Current Inventory Status")

        # Simple table display
        if data["raw_data"]:
            # Create simple table data
            table_data = []
            for record in data["raw_data"]:
                current_stock = num_or_zero(record.get("Current Stock", 0))
                reorder_level = money_to_float(record.get("Reorder Level", 0))
                unit_cost = money_to_float(record.get("Cost per Unit", record.get("Avg. Cost per Unit", 0)))

                status = "🟢 OK"
                if current_stock == 0:
                    status = "🔴 Out of Stock"
                elif current_stock <= reorder_level:
                    status = "🟡 Below Reorder Level"
                elif str(record.get("Re-Order Required", "")).strip().upper() == "YES":
                    status = "🟠 Manual Reorder"

                table_data.append({
                    "Product": record.get("Product Name", record.get("RM ID", "Unknown")),
                    "Current Stock": current_stock,
                    "Reorder Level": reorder_level,
                    "Unit Cost": f"₹{unit_cost:,.2f}",
                    "Status": status
                })

            # Display as simple table
            for item in table_data:
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                col1.write(f"**{item['Product']}**")
                col2.write(item['Current Stock'])
                col3.write(item['Reorder Level'])
                col4.write(item['Unit Cost'])
                col5.write(item['Status'])
                st.markdown("---")
        else:
            st.info("No inventory data available.")

    with tab2:
        st.markdown("### Raw Data")

        # Show raw data in expandable sections
        with st.expander("Raw Material Master Data", expanded=False):
            if data["raw_data"]:
                for record in data["raw_data"]:
                    st.json(record)
            else:
                st.info("No raw material data available.")

        with st.expander("Stock In Data", expanded=False):
            if data["in_data"]:
                for record in data["in_data"]:
                    st.json(record)
            else:
                st.info("No stock in data available.")

        with st.expander("Stock Out Data", expanded=False):
            if data["out_data"]:
                for record in data["out_data"]:
                    st.json(record)
            else:
                st.info("No stock out data available.")

    # Footer
    st.markdown("---")
    st.markdown("*Dashboard automatically refreshes every 5 minutes. Click 'Refresh' for immediate updates.*")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Please check your Google Sheets connection and credentials.")

    # Helpful setup instructions
    st.markdown("### 🔧 Setup Instructions:")
    st.markdown("""
    1. **For Render Deployment:**
       - Go to your Render service settings
       - Add environment variable: `GOOGLE_CREDENTIALS_JSON`
       - Paste your Google service account JSON credentials

    2. **For Local Development:**
       - Create `.streamlit/secrets.toml` file
       - Add: `GOOGLE_CREDENTIALS_JSON = '{"your": "credentials"}'`

    3. **Google Sheets Setup:**
       - Share your Google Sheet with the service account email
       - Ensure the sheet has tabs: 'Raw Material Master', 'Stock In', 'Stock Out'
    """)
