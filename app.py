import json
import re
from datetime import datetime
from dateutil import parser as dateparser

import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============== Helpers ==============

def money_to_float(x):
    """Convert strings like '₹1,650' to 1650.0; pass through numbers; None->0."""
    if pd.isna(x):
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x)
    s = re.sub(r"[^\d.\-]", "", s)  # remove currency/commas
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

@st.cache_data(ttl=300, show_spinner=False)  # 5 minutes
def load_all_data():
    gc = get_gspread_client()
    sh = gc.open_by_key(st.secrets["SHEET_ID"])

    ws_raw = sh.worksheet("Raw Material Master")
    ws_in  = sh.worksheet("Stock In")
    ws_out = sh.worksheet("Stock Out")

    df_raw = pd.DataFrame(ws_raw.get_all_records())
    df_in  = pd.DataFrame(ws_in.get_all_records())
    df_out = pd.DataFrame(ws_out.get_all_records())

    # Normalize column names (strip spaces)
    df_raw.columns = [c.strip() for c in df_raw.columns]
    df_in.columns  = [c.strip() for c in df_in.columns]
    df_out.columns = [c.strip() for c in df_out.columns]

    # Standardize numeric money fields
    for col in ["Avg. Cost per Unit", "Cost per Unit", "Reorder Level"]:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(money_to_float)

    # Attempt to ensure Quantity columns exist for in/out
    if "Quantity" not in df_in.columns:
        # Some users store Quantity in "Quantity In"
        if "Quantity In" in df_in.columns:
            df_in["Quantity"] = df_in["Quantity In"]
        else:
            df_in["Quantity"] = 0

    if "Quantity Out" not in df_out.columns:
        df_out["Quantity Out"] = 0

    # Parse dates
    if "Date" in df_in.columns:
        df_in["Date"] = df_in["Date"].apply(to_date)
    if "Date" in df_out.columns:
        df_out["Date"] = df_out["Date"].apply(to_date)

    # Derive keys to match Stock In/Out to Raw Master
    # Prefer RM ID if available, else fallback to Product Name
    key_col = "RM ID" if "RM ID" in df_raw.columns else "Product Name"

    # Build in/out totals by key
    def key_series(df, possible_cols):
        for c in possible_cols:
            if c in df.columns:
                return df[c].astype(str).str.strip()
        return pd.Series([""] * len(df))

    df_in["_key"]  = key_series(df_in,  ["RM ID", "Product ID", "Product Name"])
    df_out["_key"] = key_series(df_out, ["RM ID", "Product ID", "Product Name"])
    df_raw["_key"] = key_series(df_raw, [key_col])

    in_totals  = df_in.groupby("_key", dropna=False)["Quantity"].sum().reset_index().rename(columns={"Quantity":"InQty"})
    out_totals = df_out.groupby("_key", dropna=False)["Quantity Out"].sum().reset_index().rename(columns={"Quantity Out":"OutQty"})

    # Merge into master
    inv = df_raw.merge(in_totals, on="_key", how="left").merge(out_totals, on="_key", how="left")
    inv["InQty"]  = inv["InQty"].fillna(0).apply(num_or_zero)
    inv["OutQty"] = inv["OutQty"].fillna(0).apply(num_or_zero)
    inv["Current Stock"] = inv["InQty"] - inv["OutQty"]

    # Pick cost column (Cost per Unit fallback to Avg)
    inv["Unit Cost"] = inv.apply(
        lambda r: r["Cost per Unit"] if r.get("Cost per Unit", 0) else r.get("Avg. Cost per Unit", 0),
        axis=1
    )
    inv["Inventory Value"] = inv["Current Stock"] * inv["Unit Cost"]

    # Alerts
    if "Reorder Level" in inv.columns:
        inv["Below Reorder"] = inv["Current Stock"] <= inv["Reorder Level"]
    else:
        inv["Below Reorder"] = False

    # Trend frames
    in_trend = df_in.copy()
    if "Date" in in_trend.columns:
        in_trend = in_trend.dropna(subset=["Date"])
        in_trend = in_trend.groupby("Date")["Quantity"].sum().reset_index(name="Stock In")
    out_trend = df_out.copy()
    if "Date" in out_trend.columns:
        out_trend = out_trend.dropna(subset=["Date"])
        out_trend = out_trend.groupby("Date")["Quantity Out"].sum().reset_index(name="Stock Out")

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
    sh = gc.open_by_key(st.secrets["SHEET_ID"])
    ws = sh.worksheet("Stock In")
    # Append maintaining column order if exists, else append values list
    headers = ws.row_values(1)
    values = [row_dict.get(h, "") for h in headers]
    ws.append_row(values, value_input_option="USER_ENTERED")

def append_stock_out(row_dict):
    gc = get_gspread_client()
    sh = gc.open_by_key(st.secrets["SHEET_ID"])
    ws = sh.worksheet("Stock Out")
    headers = ws.row_values(1)
    values = [row_dict.get(h, "") for h in headers]
    ws.append_row(values, value_input_option="USER_ENTERED")

# ============== UI ==============

st.set_page_config(page_title="Inventory Dashboard", page_icon="📦", layout="wide")

# Header with Notification Bell
data = load_all_data()
inv = data["inventory"]

alerts_df = inv[inv["Below Reorder"] == True]
alerts_count = int(alerts_df.shape[0])

col_logo, col_title, col_alerts, col_refresh = st.columns([0.5, 5, 1.2, 1.2])
with col_logo:
    st.markdown("### 📦")
with col_title:
    st.markdown("## Inventory Dashboard")
with col_alerts:
    # Notification bell with count
    bell = "🔔" if alerts_count > 0 else "🔕"
    st.markdown(f"### {bell} {alerts_count}")
    with st.expander("View Alerts"):
        if alerts_count == 0:
            st.success("All good — no low stock items.")
        else:
            st.warning("Items at/below reorder level:")
            show_cols = [c for c in ["RM ID","Product Name","Unit","Current Stock","Reorder Level"] if c in alerts_df.columns]
            st.dataframe(alerts_df[show_cols], use_container_width=True)
with col_refresh:
    if st.button("Refresh Data"):
        load_all_data.clear()
        st.toast("Data cache cleared. Reloading…")
        st.rerun()

st.markdown("---")

# KPI cards
total_items = inv.shape[0]
total_value = inv["Inventory Value"].sum()
total_in = inv["InQty"].sum()
total_out = inv["OutQty"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Products", f"{total_items:,}")
k2.metric("Total Stock In (units)", f"{int(total_in):,}")
k3.metric("Total Stock Out (units)", f"{int(total_out):,}")
k4.metric("Inventory Value", f"₹{total_value:,.0f}")

st.markdown("")

# Tabs
tab_dash, tab_stock, tab_mov, tab_forms = st.tabs(["📈 Dashboard", "📋 Stock Table", "🔄 Movements", "✍️ Forms"])

with tab_dash:
    c1, c2 = st.columns(2)

    # In vs Out Trend
    in_trend = data["in_trend"]
    out_trend = data["out_trend"]

    if not in_trend.empty or not out_trend.empty:
        # Combine for plotting
        trend = pd.DataFrame()
        if not in_trend.empty:
            trend = in_trend
        if not out_trend.empty:
            trend = trend.merge(out_trend, on="Date", how="outer")
        trend = trend.sort_values("Date")
        trend = trend.fillna(0)
        with c1:
            fig = px.line(trend, x="Date", y=["Stock In", "Stock Out"], title="Stock In vs Stock Out")
            st.plotly_chart(fig, use_container_width=True)
    else:
        with c1:
            st.info("No dated stock movements to chart yet.")

    # Current Stock by Product (Top 15)
    show_cols = [c for c in ["RM ID", "Product Name", "Current Stock"] if c in inv.columns]
    top_stock = inv.sort_values("Current Stock", ascending=False).head(15)
    with c2:
        fig2 = px.bar(top_stock, x=show_cols[1] if "Product Name" in show_cols else "RM ID", y="Current Stock",
                      title="Top 15 Current Stock by Product")
        st.plotly_chart(fig2, use_container_width=True)

with tab_stock:
    st.subheader("Current Stock Snapshot")
    search = st.text_input("Search by RM ID or Product Name").strip().lower()
    view_df = inv.copy()
    if search:
        view_df = view_df[
            view_df["_key"].str.lower().str.contains(search) |
            (view_df["Product Name"].astype(str).str.lower().str.contains(search) if "Product Name" in view_df.columns else False)
        ]
    cols = [c for c in ["RM ID","Product Name","Unit","InQty","OutQty","Current Stock","Unit Cost","Inventory Value","Reorder Level"] if c in view_df.columns]
    st.dataframe(view_df[cols], use_container_width=True)

with tab_mov:
    st.subheader("Stock Movements")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Stock In (raw)**")
        df_in = data["df_in"].copy()
        st.dataframe(df_in, use_container_width=True)
    with c2:
        st.markdown("**Stock Out (raw)**")
        df_out = data["df_out"].copy()
        st.dataframe(df_out, use_container_width=True)

with tab_forms:
    st.subheader("Append Records")

    st.markdown("### ➕ Stock In")
    with st.form("form_in"):
        rm_id = st.text_input("RM ID (preferred)", "")
        product = st.text_input("Product Name", "")
        unit = st.text_input("Unit", "")
        qty_in = st.number_input("Quantity", min_value=0.0, step=1.0)
        cost = st.text_input("Cost per Unit (optional)", "")
        date_in = st.date_input("Date (optional)", value=datetime.today())
        submitted_in = st.form_submit_button("Add Stock In")
        if submitted_in:
            row = {
                "RM ID": rm_id,
                "Product Name": product,
                "Unit": unit,
                "Quantity": qty_in,
                "Cost per Unit": cost,
                "Date": date_in.strftime("%d %b %Y"),
            }
            try:
                append_stock_in(row)
                st.success("Stock In appended!")
                load_all_data.clear()
            except Exception as e:
                st.error(f"Failed to append Stock In: {e}")

    st.markdown("---")

    st.markdown("### ➖ Stock Out")
    with st.form("form_out"):
        rm_id_o = st.text_input("RM ID / Product ID", "")
        product_o = st.text_input("Product Name", "")
        qty_out = st.number_input("Quantity Out", min_value=0.0, step=1.0)
        remarks = st.text_input("Remarks", "")
        to_whom = st.text_input("Distributed To", "")
        date_out = st.date_input("Date", value=datetime.today())
        submitted_out = st.form_submit_button("Add Stock Out")
        if submitted_out:
            row = {
                "Product ID": rm_id_o,
                "Product Name": product_o,
                "Quantity Out": qty_out,
                "Remarks": remarks,
                "Distributed To": to_whom,
                "Date": date_out.strftime("%d %b %Y"),
            }
            try:
                append_stock_out(row)
                st.success("Stock Out appended!")
                load_all_data.clear()
            except Exception as e:
                st.error(f"Failed to append Stock Out: {e}")
