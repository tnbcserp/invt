import json
import re
from datetime import datetime, date
from dateutil import parser as dateparser

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============== Helpers ==============

def money_to_float(x):
    if pd.isna(x):
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
    if pd.isna(x) or str(x).strip() == "":
        return pd.NaT
    try:
        return dateparser.parse(str(x), dayfirst=True).date()
    except Exception:
        return pd.NaT

def highlight_stock(row):
    """Apply conditional formatting to inventory rows"""
    colors = [''] * len(row)

    # Check if out of stock
    if row.get('Current Stock', 0) == 0:
        colors = ['background-color: #ffebee; color: #c62828'] * len(row)  # Light red background
    # Check if below reorder level or re-order required
    elif (row.get('Current Stock', 0) <= row.get('Reorder Level', 0) or
          str(row.get('Re-Order Required', '')).strip().upper() == 'YES'):
        colors = ['background-color: #fff3e0; color: #ef6c00'] * len(row)  # Light orange background

    return colors

# ============== Auth / Sheets ==============

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    creds_json = st.secrets["GOOGLE_CREDENTIALS_JSON"]
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

    # Embedded sheet ID
    SHEET_ID = "1G_q_d4Kg35PWBWb49f5FWmoYAnA4k0TYAg4QzIM4N24"
    sh = gc.open_by_key(SHEET_ID)

    ws_raw = sh.worksheet("Raw Material Master")
    ws_in  = sh.worksheet("Stock In")
    ws_out = sh.worksheet("Stock Out")

    df_raw = pd.DataFrame(ws_raw.get_all_records())
    df_in  = pd.DataFrame(ws_in.get_all_records())
    df_out = pd.DataFrame(ws_out.get_all_records())

    # Normalize column names
    df_raw.columns = [c.strip() for c in df_raw.columns]
    df_in.columns  = [c.strip() for c in df_in.columns]
    df_out.columns = [c.strip() for c in df_out.columns]

    # Convert money columns
    for col in ["Avg. Cost per Unit", "Cost per Unit", "Reorder Level"]:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(money_to_float)

    # Ensure Quantity columns exist
    df_in["Quantity"] = df_in.get("Quantity", df_in.get("Quantity In", 0))
    df_out["Quantity Out"] = df_out.get("Quantity Out", 0)

    # Convert Quantity columns to numeric to avoid TypeError
    df_in["Quantity"] = pd.to_numeric(df_in["Quantity"], errors="coerce").fillna(0)
    df_out["Quantity Out"] = pd.to_numeric(df_out["Quantity Out"], errors="coerce").fillna(0)

    # Parse dates
    if "Date" in df_in.columns:
        df_in["Date"] = df_in["Date"].apply(to_date)
    if "Date" in df_out.columns:
        df_out["Date"] = df_out["Date"].apply(to_date)

    # Derive keys
    key_col = "RM ID" if "RM ID" in df_raw.columns else "Product Name"

    def key_series(df, possible_cols):
        for c in possible_cols:
            if c in df.columns:
                return df[c].astype(str).str.strip()
        return pd.Series([""] * len(df))

    df_in["_key"]  = key_series(df_in,  ["RM ID", "Product ID", "Product Name"])
    df_out["_key"] = key_series(df_out, ["RM ID", "Product ID", "Product Name"])
    df_raw["_key"] = key_series(df_raw, [key_col])

    # Totals
    in_totals  = df_in.groupby("_key", dropna=False)["Quantity"].sum().reset_index().rename(columns={"Quantity":"InQty"})
    out_totals = df_out.groupby("_key", dropna=False)["Quantity Out"].sum().reset_index().rename(columns={"Quantity Out":"OutQty"})

    # Merge into master
    inv = df_raw.merge(in_totals, on="_key", how="left").merge(out_totals, on="_key", how="left")
    inv["InQty"]  = inv["InQty"].fillna(0).apply(num_or_zero)
    inv["OutQty"] = inv["OutQty"].fillna(0).apply(num_or_zero)
    inv["Current Stock"] = inv["InQty"] - inv["OutQty"]

    # Unit Cost & Inventory Value
    inv["Unit Cost"] = inv.apply(
        lambda r: r["Cost per Unit"] if r.get("Cost per Unit", 0) else r.get("Avg. Cost per Unit", 0),
        axis=1
    )
    inv["Inventory Value"] = inv["Current Stock"] * inv["Unit Cost"]

    # Enhanced Alert Detection
    inv["Reorder Level"] = inv.get("Reorder Level", 0)
    inv["Re-Order Required"] = inv.get("Re-Order Required", "")

    # Condition 1: Current Stock <= Reorder Level
    inv["Below Reorder Level"] = inv["Current Stock"] <= inv["Reorder Level"]

    # Condition 2: Re-Order Required = "Yes"
    inv["Manual Reorder Flag"] = inv["Re-Order Required"].astype(str).str.strip().str.upper() == "YES"

    # Condition 3: Current Stock = 0 (Out of Stock)
    inv["Out of Stock"] = inv["Current Stock"] == 0

    # Combined alert condition
    inv["Needs Reorder"] = (inv["Below Reorder Level"] | inv["Manual Reorder Flag"] | inv["Out of Stock"])

    # Alert severity
    def get_alert_severity(row):
        if row["Out of Stock"]:
            return "Critical"
        elif row["Manual Reorder Flag"]:
            return "High"
        elif row["Below Reorder Level"]:
            return "Medium"
    else:
            return "None"

    inv["Alert Severity"] = inv.apply(get_alert_severity, axis=1)

    # Trend frames
    in_trend = df_in.copy()
    if "Date" in in_trend.columns:
        in_trend = in_trend.dropna(subset=["Date"]).groupby("Date")["Quantity"].sum().reset_index(name="Stock In")
    out_trend = df_out.copy()
    if "Date" in out_trend.columns:
        out_trend = out_trend.dropna(subset=["Date"]).groupby("Date")["Quantity Out"].sum().reset_index(name="Stock Out")

    return {
        "df_raw": df_raw,
        "df_in": df_in,
        "df_out": df_out,
        "inventory": inv,
        "in_trend": in_trend,
        "out_trend": out_trend
    }

def append_stock_in(row_dict):
    gc = get_gspread_client()
    sh = gc.open_by_key("1G_q_d4Kg35PWBWb49f5FWmoYAnA4k0TYAg4QzIM4N24")
    ws = sh.worksheet("Stock In")
    headers = ws.row_values(1)
    values = [row_dict.get(h, "") for h in headers]
    ws.append_row(values, value_input_option="USER_ENTERED")

def append_stock_out(row_dict):
    gc = get_gspread_client()
    sh = gc.open_by_key("1G_q_d4Kg35PWBWb49f5FWmoYAnA4k0TYAg4QzIM4N24")
    ws = sh.worksheet("Stock Out")
    headers = ws.row_values(1)
    values = [row_dict.get(h, "") for h in headers]
    ws.append_row(values, value_input_option="USER_ENTERED")

# ============== Alert Management ==============

def initialize_session_state():
    """Initialize session state for alert tracking"""
    if "alerts_history" not in st.session_state:
        st.session_state["alerts_history"] = []
    if "last_alert_snapshot" not in st.session_state:
        st.session_state["last_alert_snapshot"] = None

def update_alerts_history(current_alerts):
    """Update alert history and detect changes"""
    current_timestamp = datetime.now()

    # Create current alert snapshot
    current_snapshot = {
        "timestamp": current_timestamp,
        "alerts": current_alerts.copy(),
        "alert_count": len(current_alerts)
    }

    # Check if alerts have changed
    if st.session_state["last_alert_snapshot"] is None:
        # First time loading
        st.session_state["last_alert_snapshot"] = current_snapshot
        if len(current_alerts) > 0:
            st.session_state["alerts_history"].append(current_snapshot)
    else:
        last_snapshot = st.session_state["last_alert_snapshot"]

        # Check if alerts have changed
        if (len(current_alerts) != last_snapshot["alert_count"] or
            not current_alerts.equals(last_snapshot["alerts"])):

            st.session_state["alerts_history"].append(current_snapshot)
            st.session_state["last_alert_snapshot"] = current_snapshot

            # Keep only last 10 alert snapshots
            if len(st.session_state["alerts_history"]) > 10:
                st.session_state["alerts_history"] = st.session_state["alerts_history"][-10:]

# ============== UI ==============

st.set_page_config(page_title="Inventory Dashboard", page_icon="📦", layout="wide")

# Initialize session state
initialize_session_state()

# Load data
data = load_all_data()
inv = data["inventory"]

# Get current alerts
current_alerts = inv[inv["Needs Reorder"] == True].copy()
alerts_count = len(current_alerts)

# Update alert history
update_alerts_history(current_alerts)

# Header with notification bell
col_logo, col_title, col_alerts, col_refresh = st.columns([0.5, 4, 1.5, 1])
with col_logo:
    st.markdown("### 📦")
with col_title:
    st.markdown("## Inventory Dashboard")
with col_alerts:
    # Notification bell with count
    bell = "🔔" if alerts_count > 0 else "🔕"
    st.markdown(f"### {bell} {alerts_count}")

    # Alert details expander
    with st.expander(f"View Alerts ({alerts_count})", expanded=False):
        if alerts_count == 0:
            st.success("✅ All good — no items need reorder!")
        else:
            # Group alerts by severity
            critical_alerts = current_alerts[current_alerts["Alert Severity"] == "Critical"]
            high_alerts = current_alerts[current_alerts["Alert Severity"] == "High"]
            medium_alerts = current_alerts[current_alerts["Alert Severity"] == "Medium"]

            if len(critical_alerts) > 0:
                st.error(f"🚨 **Critical: {len(critical_alerts)} items out of stock**")
                show_cols = [c for c in ["RM ID", "Product Name", "Unit", "Current Stock", "Reorder Level"] if c in critical_alerts.columns]
                st.dataframe(critical_alerts[show_cols], use_container_width=True)

            if len(high_alerts) > 0:
                st.warning(f"⚠️ **High Priority: {len(high_alerts)} items flagged for reorder**")
                show_cols = [c for c in ["RM ID", "Product Name", "Unit", "Current Stock", "Reorder Level"] if c in high_alerts.columns]
                st.dataframe(high_alerts[show_cols], use_container_width=True)

            if len(medium_alerts) > 0:
                st.info(f"ℹ️ **Medium Priority: {len(medium_alerts)} items below reorder level**")
                show_cols = [c for c in ["RM ID", "Product Name", "Unit", "Current Stock", "Reorder Level"] if c in medium_alerts.columns]
                st.dataframe(medium_alerts[show_cols], use_container_width=True)

            # Show alert history
            if len(st.session_state["alerts_history"]) > 1:
                st.markdown("---")
                st.markdown("**Alert History:**")
                history_df = pd.DataFrame([
                    {
                        "Time": snapshot["timestamp"].strftime("%H:%M:%S"),
                        "Alert Count": snapshot["alert_count"]
                    }
                    for snapshot in st.session_state["alerts_history"]
                ])
                st.dataframe(history_df, use_container_width=True)

with col_refresh:
    if st.button("🔄 Refresh"):
        load_all_data.clear()
        st.toast("Data refreshed!")
        st.rerun()

st.markdown("---")

# KPI Cards
total_items = inv.shape[0]
total_value = inv["Inventory Value"].sum()
total_in = inv["InQty"].sum()
total_out = inv["OutQty"].sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Products", f"{total_items:,}")
k2.metric("Total Stock In", f"{int(total_in):,}")
k3.metric("Total Stock Out", f"{int(total_out):,}")
k4.metric("Inventory Value", f"₹{total_value:,.0f}")
k5.metric("Items Needing Reorder", f"{alerts_count}", delta=f"{alerts_count - len(st.session_state['alerts_history'][-2]['alerts']) if len(st.session_state['alerts_history']) > 1 else 0}")

st.markdown("---")

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Inventory Overview", "📈 Trends", "➕ Add Stock", "📋 Alert History"])

with tab1:
    st.markdown("### Current Inventory Status")

    # Filters
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        show_alerts_only = st.checkbox("Show alerts only", value=False)
    with col_filter2:
        severity_filter = st.selectbox("Alert Severity", ["All", "Critical", "High", "Medium", "None"])
    with col_filter3:
        search_term = st.text_input("Search products", "")

    # Apply filters
    filtered_inv = inv.copy()

    if show_alerts_only:
        filtered_inv = filtered_inv[filtered_inv["Needs Reorder"] == True]

    if severity_filter != "All":
        filtered_inv = filtered_inv[filtered_inv["Alert Severity"] == severity_filter]

    if search_term:
        search_cols = ["RM ID", "Product Name"]
        mask = pd.DataFrame([filtered_inv[col].astype(str).str.contains(search_term, case=False, na=False)
                           for col in search_cols if col in filtered_inv.columns]).any()
        filtered_inv = filtered_inv[mask]

    # Display inventory table with conditional formatting
    if len(filtered_inv) > 0:
        display_cols = ["RM ID", "Product Name", "Unit", "Current Stock", "Reorder Level",
                       "Unit Cost", "Inventory Value", "Alert Severity"]
        display_cols = [col for col in display_cols if col in filtered_inv.columns]

        styled_df = filtered_inv[display_cols].style.apply(highlight_stock, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400)

        # Summary stats
        col_sum1, col_sum2, col_sum3 = st.columns(3)
        with col_sum1:
            st.metric("Items Displayed", len(filtered_inv))
        with col_sum2:
            st.metric("Total Value", f"₹{filtered_inv['Inventory Value'].sum():,.0f}")
        with col_sum3:
            st.metric("Avg Stock Level", f"{filtered_inv['Current Stock'].mean():.1f}")
    else:
        st.info("No items match the current filters.")

with tab2:
    st.markdown("### Inventory Trends")

    # Stock In vs Stock Out over time
    if len(data["in_trend"]) > 0 or len(data["out_trend"]) > 0:
        fig = make_subplots(rows=2, cols=2,
                           subplot_titles=("Stock In vs Stock Out", "Top 10 Products by Stock",
                                         "Inventory Value Distribution", "Alert Severity Breakdown"),
                           specs=[[{"type": "xy"}, {"type": "xy"}],
                                   [{"type": "xy"}, {"type": "domain"}]])

        # Stock In vs Stock Out trend
        if len(data["in_trend"]) > 0:
            fig.add_trace(go.Scatter(x=data["in_trend"]["Date"], y=data["in_trend"]["Stock In"],
                                   name="Stock In", line=dict(color="green")), row=1, col=1)
        if len(data["out_trend"]) > 0:
            fig.add_trace(go.Scatter(x=data["out_trend"]["Date"], y=data["out_trend"]["Stock Out"],
                                   name="Stock Out", line=dict(color="red")), row=1, col=1)

        # Top 10 products by current stock
        top_products = inv.nlargest(10, "Current Stock")
        fig.add_trace(go.Bar(x=top_products["Product Name"], y=top_products["Current Stock"],
                           name="Current Stock"), row=1, col=2)

        # Inventory value distribution
        fig.add_trace(go.Histogram(x=inv["Inventory Value"], name="Value Distribution"), row=2, col=1)

        # Alert severity breakdown
        severity_counts = inv["Alert Severity"].value_counts()
        fig.add_trace(go.Pie(labels=severity_counts.index, values=severity_counts.values,
                           name="Alert Severity"), row=2, col=2)

        fig.update_layout(height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available yet.")

with tab3:
    st.markdown("### Add Stock Entry")

    # Stock In Form
    st.markdown("#### 📥 Add Stock In")
    with st.form("stock_in_form"):
        col1, col2 = st.columns(2)

        with col1:
            # Get available products
            products = inv[["RM ID", "Product Name"]].dropna()
            product_options = [f"{row['RM ID']} - {row['Product Name']}" for _, row in products.iterrows()]

            selected_product = st.selectbox("Product", product_options)
            quantity = st.number_input("Quantity", min_value=0.0, value=1.0, step=0.1)
            cost_per_unit = st.number_input("Cost per Unit", min_value=0.0, value=0.0, step=0.01)

        with col2:
            supplier = st.text_input("Supplier")
            date_in = st.date_input("Date", value=date.today())
            notes = st.text_area("Notes")

        submitted_in = st.form_submit_button("Add Stock In")

        if submitted_in:
            # Extract RM ID from selection
            rm_id = selected_product.split(" - ")[0]

            stock_in_data = {
                "RM ID": rm_id,
                "Quantity": quantity,
                "Cost per Unit": cost_per_unit,
                "Supplier": supplier,
                "Date": date_in.strftime("%d/%m/%Y"),
                "Notes": notes
            }

            try:
                append_stock_in(stock_in_data)
                st.success("Stock In entry added successfully!")
                load_all_data.clear()  # Clear cache to refresh data
            except Exception as e:
                st.error(f"Error adding stock in: {str(e)}")

    st.markdown("---")

    # Stock Out Form
    st.markdown("#### 📤 Add Stock Out")
    with st.form("stock_out_form"):
        col1, col2 = st.columns(2)

        with col1:
            selected_product_out = st.selectbox("Product (Out)", product_options)
            quantity_out = st.number_input("Quantity Out", min_value=0.0, value=1.0, step=0.1)

        with col2:
            purpose = st.text_input("Purpose/Department")
            date_out = st.date_input("Date (Out)", value=date.today())
            notes_out = st.text_area("Notes (Out)")

        submitted_out = st.form_submit_button("Add Stock Out")

        if submitted_out:
            rm_id_out = selected_product_out.split(" - ")[0]

            stock_out_data = {
                "RM ID": rm_id_out,
                "Quantity Out": quantity_out,
                "Purpose": purpose,
                "Date": date_out.strftime("%d/%m/%Y"),
                "Notes": notes_out
            }

            try:
                append_stock_out(stock_out_data)
                st.success("Stock Out entry added successfully!")
                load_all_data.clear()  # Clear cache to refresh data
            except Exception as e:
                st.error(f"Error adding stock out: {str(e)}")

with tab4:
    st.markdown("### Alert History & Analysis")

    if len(st.session_state["alerts_history"]) > 0:
        # Alert timeline
        st.markdown("#### Alert Timeline")
        timeline_data = []
        for snapshot in st.session_state["alerts_history"]:
            timeline_data.append({
                "Time": snapshot["timestamp"].strftime("%H:%M:%S"),
                "Date": snapshot["timestamp"].strftime("%Y-%m-%d"),
                "Alert Count": snapshot["alert_count"],
                "Critical": len(snapshot["alerts"][snapshot["alerts"]["Alert Severity"] == "Critical"]),
                "High": len(snapshot["alerts"][snapshot["alerts"]["Alert Severity"] == "High"]),
                "Medium": len(snapshot["alerts"][snapshot["alerts"]["Alert Severity"] == "Medium"])
            })

        timeline_df = pd.DataFrame(timeline_data)
        st.dataframe(timeline_df, use_container_width=True)

        # Alert trend chart
        if len(timeline_data) > 1:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=timeline_df["Time"], y=timeline_df["Alert Count"],
                                         mode="lines+markers", name="Total Alerts"))
            fig_trend.add_trace(go.Scatter(x=timeline_df["Time"], y=timeline_df["Critical"],
                                         mode="lines+markers", name="Critical", line=dict(color="red")))
            fig_trend.add_trace(go.Scatter(x=timeline_df["Time"], y=timeline_df["High"],
                                         mode="lines+markers", name="High", line=dict(color="orange")))
            fig_trend.update_layout(title="Alert Trend Over Time", xaxis_title="Time", yaxis_title="Alert Count")
            st.plotly_chart(fig_trend, use_container_width=True)

        # Current alert details
        st.markdown("#### Current Alert Details")
        if len(current_alerts) > 0:
            alert_summary = current_alerts.groupby("Alert Severity").agg({
                "RM ID": "count",
                "Inventory Value": "sum"
            }).rename(columns={"RM ID": "Count", "Inventory Value": "Total Value"})

            col_sum1, col_sum2 = st.columns(2)
            with col_sum1:
                st.dataframe(alert_summary)
            with col_sum2:
                st.metric("Total Alert Value", f"₹{current_alerts['Inventory Value'].sum():,.0f}")
        else:
            st.success("No current alerts!")
    else:
        st.info("No alert history available yet.")

    # Clear history button
    if st.button("Clear Alert History"):
        st.session_state["alerts_history"] = []
        st.session_state["last_alert_snapshot"] = None
        st.success("Alert history cleared!")
        st.rerun()

# Footer
st.markdown("---")
st.markdown("*Dashboard automatically refreshes every 5 minutes. Click 'Refresh' for immediate updates.*")
