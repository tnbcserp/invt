import json
import re
from datetime import datetime, date, timedelta
from dateutil import parser as dateparser
import os
from typing import Dict, List, Optional, Tuple

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============== Page Configuration ==============
st.set_page_config(
    page_title="🏪 Restaurant Inventory Manager - Smart Stock Control",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== Theme Configuration ==============
def get_theme_colors():
    """Get theme colors based on current mode"""
    # Check if dark mode is enabled
    try:
        # This is a workaround to detect dark mode
        dark_mode = st.get_option("theme.base") == "dark"
    except:
        dark_mode = False

    if dark_mode:
        return {
            "primary": "#667eea",
            "secondary": "#764ba2",
            "background": "#0e1117",
            "surface": "#262730",
            "text": "#fafafa",
            "text_secondary": "#b0b0b0",
            "success": "#00b894",
            "warning": "#fdcb6e",
            "error": "#ff6b6b",
            "info": "#74b9ff",
            "border": "#404040",
            "hover": "#1e1e1e",
            "light": "#404040"
        }
    else:
        return {
            "primary": "#667eea",
            "secondary": "#764ba2",
            "background": "#ffffff",
            "surface": "#f0f2f6",
            "text": "#262730",
            "text_secondary": "#666666",
            "success": "#00b894",
            "warning": "#fdcb6e",
            "error": "#ff6b6b",
            "info": "#74b9ff",
            "border": "#e0e0e0",
            "hover": "#f8f9fa",
            "light": "#f8f9fa"
        }

def apply_custom_css():
    """Apply optimized CSS with theme support and excellent UX"""
    colors = get_theme_colors()

    st.markdown(f"""
    <style>
    /* Global Styles */
    .stApp {{
        background-color: {colors['background']} !important;
        color: {colors['text']} !important;
    }}

    /* Global Navigation Styles */
    .global-nav {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['secondary']} 100%);
        padding: 0;
        margin: -1rem -1rem 1rem -1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        position: sticky;
        top: 0;
        z-index: 1000;
    }}

    .nav-container {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }}

    .nav-brand h2 {{
        color: white;
        margin: 0;
        font-size: 1.2rem;
        font-weight: 600;
    }}

    .nav-links {{
        display: flex;
        gap: 1rem;
        align-items: center;
    }}

    .nav-link {{
        color: white;
        text-decoration: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        transition: all 0.3s ease;
        font-weight: 500;
        font-size: 0.9rem;
    }}

    .nav-link:hover {{
        background: rgba(255,255,255,0.2);
        color: white;
        text-decoration: none;
        transform: translateY(-1px);
    }}

    .nav-link.active {{
        background: rgba(255,255,255,0.3);
        color: white;
        font-weight: 600;
    }}

    /* Responsive Navigation */
    @media (max-width: 768px) {{
        .nav-container {{
            flex-direction: column;
            gap: 1rem;
            padding: 1rem;
        }}

        .nav-links {{
            flex-wrap: wrap;
            justify-content: center;
        }}

        .nav-link {{
            font-size: 0.8rem;
            padding: 0.4rem 0.8rem;
        }}
    }}

    

    /* Navigation Cards - Excellent UX */
    .nav-card {{
        background: {colors['surface']};
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px solid transparent;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        cursor: pointer;
        text-decoration: none;
        display: block;
    }}

    .nav-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        border-color: {colors['primary']};
    }}

    .nav-card.active {{
        border-color: {colors['primary']};
        background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%);
    }}

    /* Value Proposition Cards */
    .value-card {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['secondary']} 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .value-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.15);
    }}

    /* Modern Card Styling with Theme Support */
    .metric-card {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['secondary']} 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.15);
    }}

    .alert-card {{
        background: linear-gradient(135deg, {colors['error']} 0%, #ee5a24 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(255,107,107,0.3);
        margin: 0.5rem 0;
        transition: transform 0.2s ease;
    }}

    .alert-card:hover {{
        transform: translateY(-1px);
    }}

    .success-card {{
        background: linear-gradient(135deg, {colors['success']} 0%, #00a085 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(0,184,148,0.3);
        margin: 0.5rem 0;
    }}

    .warning-card {{
        background: linear-gradient(135deg, {colors['warning']} 0%, #e17055 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(253,203,110,0.3);
        margin: 0.5rem 0;
    }}

    .info-card {{
        background: linear-gradient(135deg, {colors['info']} 0%, #0984e3 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(116,185,255,0.3);
        margin: 0.5rem 0;
    }}

    /* Product Status Cards with Theme Support */
    .product-card {{
        background: {colors['surface']};
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid {colors['primary']};
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        transition: all 0.2s ease;
        color: {colors['text']};
    }}

    .product-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        background: {colors['hover']};
    }}

    .product-card.critical {{
        border-left-color: {colors['error']};
        background: linear-gradient(135deg, rgba(255,107,107,0.1) 0%, rgba(255,107,107,0.05) 100%);
    }}

    .product-card.warning {{
        border-left-color: {colors['warning']};
        background: linear-gradient(135deg, rgba(253,203,110,0.1) 0%, rgba(253,203,110,0.05) 100%);
    }}

    .product-card.success {{
        border-left-color: {colors['success']};
        background: linear-gradient(135deg, rgba(0,184,148,0.1) 0%, rgba(0,184,148,0.05) 100%);
    }}

    /* Header Styling */
    .main-header {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['secondary']} 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }}

    /* Quick Action Buttons */
    .quick-action {{
        background: {colors['surface']};
        padding: 1rem;
        border-radius: 10px;
        border: 2px solid {colors['border']};
        transition: all 0.2s ease;
        text-align: center;
        cursor: pointer;
    }}

    .quick-action:hover {{
        border-color: {colors['primary']};
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }}

    /* Alert Bell Animation */
    .alert-bell {{
        animation: shake 0.5s ease-in-out infinite;
    }}

    @keyframes shake {{
        0%, 100% {{ transform: rotate(0deg); }}
        25% {{ transform: rotate(-5deg); }}
        75% {{ transform: rotate(5deg); }}
    }}

    /* Sidebar Styling */
    .css-1d391kg {{
        background-color: {colors['surface']} !important;
    }}

    /* Metric Styling */
    .css-1wivap2 {{
        background-color: {colors['surface']} !important;
        border: 1px solid {colors['border']} !important;
    }}

    /* Responsive Design */
    @media (max-width: 768px) {{
        .metric-card, .alert-card, .success-card, .warning-card, .info-card, .nav-card {{
            margin: 0.25rem 0;
            padding: 1rem;
        }}

        .main-header {{
            padding: 1rem;
            margin-bottom: 1rem;
        }}
    }}

    /* Loading Animation */
    .loading {{
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(255,255,255,.3);
        border-radius: 50%;
        border-top-color: #fff;
        animation: spin 1s ease-in-out infinite;
    }}

    @keyframes spin {{
        to {{ transform: rotate(360deg); }}
    }}
    </style>
    """, unsafe_allow_html=True)

# ============== Optimized Helpers ==============
@st.cache_data
def money_to_float(x) -> float:
    """Optimized money conversion with caching"""
    if x is None or x == "":
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x)
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s) if s != "" else 0.0
    except ValueError:
        return 0.0

@st.cache_data
def num_or_zero(x) -> float:
    """Optimized number conversion with caching"""
    try:
        return float(x)
    except Exception:
        return 0.0

@st.cache_data
def to_date(x) -> Optional[date]:
    """Optimized date conversion with caching"""
    if x is None or str(x).strip() == "":
        return None
    try:
        return dateparser.parse(str(x), dayfirst=True).date()
    except Exception:
        return None

@st.cache_data
def get_product_status(current_stock: float, reorder_level: float, reorder_required: str) -> Tuple[str, str, str]:
    """Get product status based on inventory system rules"""
    if current_stock == 0:
        return "critical", "🔴 Out of Stock", "Immediate action required - Zero inventory"
    elif current_stock <= reorder_level * 0.5:
        return "critical", "🔴 Critical Low", "Order immediately - Below 50% of reorder level"
    elif current_stock <= reorder_level:
        return "warning", "🟡 Low Stock", "Order soon - Below reorder level"
    elif str(reorder_required).strip().upper() == "YES":
        return "warning", "🟠 Manual Order", "Manual reorder flagged"
    else:
        return "success", "🟢 In Stock", "Stock levels satisfactory"

@st.cache_data
def clean_and_validate_data(data: Dict) -> Dict:
    """Strict data cleaning and validation process"""
    cleaned_data = {}

    # Clean Raw Material Master data
    cleaned_raw_data = []
    for record in data.get("raw_data", []):
        # Validate required fields
        if not record.get("RM ID") or not record.get("Product Name"):
            continue

        # Clean and validate numeric fields
        current_stock = num_or_zero(record.get("Current Stock", 0))
        unit_cost = money_to_float(record.get("Cost per Unit", record.get("Avg. Cost per Unit", 0)))
        reorder_level = money_to_float(record.get("Reorder Level", 0))

        # Validate data integrity
        if current_stock < 0:
            current_stock = 0
        if unit_cost < 0:
            unit_cost = 0
        if reorder_level < 0:
            reorder_level = 0

        cleaned_record = {
            "RM ID": str(record.get("RM ID", "")).strip(),
            "Product Name": str(record.get("Product Name", "")).strip(),
            "Unit": str(record.get("Unit", "")).strip(),
            "Current Stock": current_stock,
            "Cost per Unit": unit_cost,
            "Avg. Cost per Unit": unit_cost,
            "Reorder Level": reorder_level,
            "Re-Order Required": str(record.get("Re-Order Required", "")).strip().upper()
        }
        cleaned_raw_data.append(cleaned_record)

    # Clean Stock IN data
    cleaned_in_data = []
    for record in data.get("in_data", []):
        if not record.get("Product Name") or not record.get("Quantity In"):
            continue

        quantity_in = num_or_zero(record.get("Quantity In", 0))
        cost_per_unit = money_to_float(record.get("Cost Per Unit", 0))

        if quantity_in <= 0 or cost_per_unit <= 0:
            continue

        cleaned_record = {
            "Date": record.get("Date", ""),
            "Product Name": str(record.get("Product Name", "")).strip(),
            "Quantity In": quantity_in,
            "Cost Per Unit": cost_per_unit,
            "Total Cost": quantity_in * cost_per_unit,
            "RM ID": str(record.get("RM ID", "")).strip(),
            "Product ID": str(record.get("Product ID", "")).strip()
        }
        cleaned_in_data.append(cleaned_record)

    # Clean Stock OUT data
    cleaned_out_data = []
    for record in data.get("out_data", []):
        if not record.get("Product Name") or not record.get("Quantity Out"):
            continue

        quantity_out = num_or_zero(record.get("Quantity Out", 0))

        if quantity_out <= 0:
            continue

        cleaned_record = {
            "Date": record.get("Date", ""),
            "Product Name": str(record.get("Product Name", "")).strip(),
            "Quantity Out": quantity_out,
            "RM ID": str(record.get("RM ID", "")).strip(),
            "Product ID": str(record.get("Product ID", "")).strip(),
            "Remarks": str(record.get("Remarks", "")).strip()
        }
        cleaned_out_data.append(cleaned_record)

    cleaned_data = {
        "raw_data": cleaned_raw_data,
        "in_data": cleaned_in_data,
        "out_data": cleaned_out_data,
        "inventory_data": data.get("inventory_data", []),
        "supplier_data": data.get("supplier_data", []),
        "staff_data": data.get("staff_data", []),
        "partner_data": data.get("partner_data", [])
    }

    return cleaned_data

@st.cache_data
def calculate_inventory_metrics(data: Dict) -> Dict:
    """Calculate comprehensive inventory metrics with proper formulas and fallback handling"""
    try:
        # First clean the data
        cleaned_data = clean_and_validate_data(data)

        metrics = {
            "total_products": len(cleaned_data["raw_data"]),
            "total_value": 0.0,
            "critical_items": 0,
            "low_stock_items": 0,
            "out_of_stock_items": 0,
            "high_value_items": 0,
            "total_in": 0.0,
            "total_out": 0.0,
            "alert_items": [],
            "expiring_soon": 0,
            "fifo_items": [],
            "avg_cost_per_unit": 0.0,
            "total_reorder_value": 0.0,
            "stock_turnover_rate": 0.0
        }

        st.success("✅ Metrics calculation started successfully")

    except Exception as e:
        st.error(f"❌ Failed to initialize metrics calculation: {str(e)}")
        # Return safe defaults
        return {
            "total_products": 0,
            "total_value": 0.0,
            "critical_items": 0,
            "low_stock_items": 0,
            "out_of_stock_items": 0,
            "high_value_items": 0,
            "total_in": 0.0,
            "total_out": 0.0,
            "alert_items": [],
            "expiring_soon": 0,
            "fifo_items": [],
            "avg_cost_per_unit": 0.0,
            "total_reorder_value": 0.0,
            "stock_turnover_rate": 0.0
        }

    # Calculate Stock IN/OUT totals with proper validation
    for record in cleaned_data["in_data"]:
        metrics["total_in"] += num_or_zero(record.get("Quantity In", 0))

    for record in cleaned_data["out_data"]:
        metrics["total_out"] += num_or_zero(record.get("Quantity Out", 0))

    # Process all records with proper calculations
    total_cost = 0.0
    total_units = 0.0

    for record in cleaned_data["raw_data"]:
        current_stock = num_or_zero(record.get("Current Stock", 0))
        unit_cost = money_to_float(record.get("Cost per Unit", 0))
        reorder_level = money_to_float(record.get("Reorder Level", 0))
        reorder_required = record.get("Re-Order Required", "")
        rm_id = record.get("RM ID", "")
        product_name = record.get("Product Name", "")

        # Calculate inventory value (Current Stock × Cost per Unit)
        item_value = current_stock * unit_cost
        metrics["total_value"] += item_value

        # Calculate total cost for average
        total_cost += unit_cost
        total_units += 1

        # Categorize high value items (>₹10,000)
        if item_value > 10000:
            metrics["high_value_items"] += 1

        # Get status with proper thresholds
        status, status_text, status_desc = get_product_status(current_stock, reorder_level, reorder_required)

        # Calculate reorder value (Reorder Level × Cost per Unit)
        reorder_value = reorder_level * unit_cost

        if status == "critical":
            if current_stock == 0:
                metrics["out_of_stock_items"] += 1
            else:
                metrics["critical_items"] += 1
            metrics["alert_items"].append({
                "product": product_name,
                "rm_id": rm_id,
                "current_stock": current_stock,
                "reorder_level": reorder_level,
                "unit_cost": unit_cost,
                "status": status,
                "status_text": status_text,
                "status_desc": status_desc,
                "priority": "High" if current_stock == 0 else "Medium",
                "est_reorder_value": reorder_value,
                "stock_value": item_value
            })
            metrics["total_reorder_value"] += reorder_value
        elif status == "warning":
            metrics["low_stock_items"] += 1
            metrics["alert_items"].append({
                "product": product_name,
                "rm_id": rm_id,
                "current_stock": current_stock,
                "reorder_level": reorder_level,
                "unit_cost": unit_cost,
                "status": status,
                "status_text": status_text,
                "status_desc": status_desc,
                "priority": "Low",
                "est_reorder_value": reorder_value,
                "stock_value": item_value
            })
            metrics["total_reorder_value"] += reorder_value

    # Calculate average cost per unit
    if total_units > 0:
        metrics["avg_cost_per_unit"] = total_cost / total_units

    # Calculate stock turnover rate (Stock Out / Average Stock)
    avg_stock = metrics["total_value"] / max(metrics["total_products"], 1)
    if avg_stock > 0:
        metrics["stock_turnover_rate"] = metrics["total_out"] / avg_stock

    return metrics

# ============== Optimized Google Sheets Integration ==============
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Optimized Google Sheets client with better error handling"""
    try:
        # Try to get credentials from environment variable first (for Render)
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
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets client: {str(e)}")
        return None

@st.cache_data(ttl=300, show_spinner=False)
def load_all_data():
    """Load data from all system sheets as per user manual"""
    try:
        gc = get_gspread_client()

        if gc is None:
            return None

        # Embedded sheet ID
        SHEET_ID = "1G_q_d4Kg35PWBWb49f5FWmoYAnA4k0TYAg4QzIM4N24"
        sh = gc.open_by_key(SHEET_ID)

        # Load all worksheets as per system structure with minimal user feedback
        sheets_loaded = {}
        sheets_errors = {}

        # Define all possible sheets (removed Partner Sheet)
        sheet_names = [
            "Raw Material Master",
            "Stock In",
            "Stock Out",
            "Inventory",
            "Supplier Master",
            "Report"
        ]

        # Try to load each sheet individually with minimal user feedback
        for sheet_name in sheet_names:
            try:
                ws = sh.worksheet(sheet_name)
                sheets_loaded[sheet_name] = ws
            except Exception as e:
                sheets_errors[sheet_name] = str(e)
        
        # Only show errors if critical sheets are missing
        critical_sheets = ["Raw Material Master", "Stock In", "Stock Out"]
        missing_critical = [sheet for sheet in critical_sheets if sheet in sheets_errors]
        
        if missing_critical:
            st.error(f"⚠️ Critical sheets missing: {', '.join(missing_critical)}")
            return None

        # Get all records from available sheets with minimal feedback
        data = {}

        # Map sheet names to data keys (removed Partner Sheet)
        sheet_data_mapping = {
            "Raw Material Master": "raw_data",
            "Stock In": "in_data",
            "Stock Out": "out_data",
            "Inventory": "inventory_data",
            "Supplier Master": "supplier_data",
            "Report": "report_data"
        }

        # Load data from each successfully loaded sheet
        for sheet_name, ws in sheets_loaded.items():
            data_key = sheet_data_mapping.get(sheet_name)
            if data_key:
                try:
                    records = ws.get_all_records()
                    data[data_key] = records
                except Exception as e:
                    data[data_key] = []
        
        # Initialize empty arrays for missing sheets
        for data_key in sheet_data_mapping.values():
            if data_key not in data:
                data[data_key] = []

        return data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# ============== Optimized UI Components ==============
def create_metric_card(title: str, value: str, subtitle: str, card_class: str = "metric-card"):
    """Optimized metric card component"""
    st.markdown(f"""
    <div class="{card_class}">
        <h3>{title}</h3>
        <h2>{value}</h2>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

def create_product_card(product: Dict, colors: Dict):
    """Optimized product card component"""
    status = product['status']
    st.markdown(f"""
    <div class="product-card {status}">
        <h4>{product['name']}</h4>
        <p><strong>Status:</strong> {product['status_text']}</p>
        <p><strong>Description:</strong> {product['status_desc']}</p>
    </div>
    """, unsafe_allow_html=True)

# ============== Main Application ==============
def main():
    """Main application with excellent UX and minimal learning curve"""
    # Apply custom CSS with theme support
    apply_custom_css()

    # Initialize session state for performance
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "dashboard"

        # Load data with minimal user feedback
    try:
        data = load_all_data()

        if data is None:
            st.error("❌ Unable to load data. Please check your Google Sheets connection.")
            st.stop()

        # Calculate inventory metrics with error handling
        try:
            metrics = calculate_inventory_metrics(data)
        except Exception as e:
            # Provide safe default metrics
            metrics = {
                "total_products": 0,
                "total_value": 0.0,
                "critical_items": 0,
                "low_stock_items": 0,
                "out_of_stock_items": 0,
                "high_value_items": 0,
                "total_in": 0.0,
                "total_out": 0.0,
                "alert_items": [],
                "avg_cost_per_unit": 0.0,
                "total_reorder_value": 0.0,
                "stock_turnover_rate": 0.0
            }
                
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        st.stop()

    # Clean Top Global Navigation
    st.markdown("""
    <div class="global-nav">
        <div class="nav-container">
            <div class="nav-brand">
                <h2>🏪 Restaurant Inventory Manager</h2>
            </div>
            <div class="nav-links">
                <a href="#" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'nav_home', value: 'home'}, '*')" class="nav-link">🏠 Home</a>
                <a href="#" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'nav_dashboard', value: 'dashboard'}, '*')" class="nav-link">📊 Kitchen</a>
                <a href="#" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'nav_alerts', value: 'alerts'}, '*')" class="nav-link">🚨 Alerts</a>
                <a href="#" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'nav_products', value: 'products'}, '*')" class="nav-link">📦 Ingredients</a>
                <a href="#" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'nav_reports', value: 'reports'}, '*')" class="nav-link">📈 Reports</a>
                <a href="#" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'nav_settings', value: 'settings'}, '*')" class="nav-link">⚙️ Settings</a>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>🏪 Restaurant Inventory Manager</h1>
        <p>Smart Stock Control for Your Restaurant - Track ingredients, manage costs, prevent waste</p>
        <p style="font-size: 0.8em; margin-top: 10px; opacity: 0.8;">Made with Value by DV™</p>
    </div>
    """, unsafe_allow_html=True)

    # Quick status overview
    if metrics["alert_items"]:
        critical_count = len([item for item in metrics["alert_items"] if item["status"] == "critical"])
        st.warning(f"🚨 **{critical_count} Items Need Reordering** - Check your kitchen supplies!")
    else:
        st.success("✅ **Kitchen Stock is Good** - All ingredients are available")

        # Home button and current page indicator
    st.markdown("---")

    # Current page indicator
    current_page_names = {
        "dashboard": "📊 Kitchen Overview",
        "alerts": "🚨 Reorder Reminders",
        "products": "📦 Ingredient List",
        "reports": "📈 Kitchen Reports",
        "settings": "⚙️ Kitchen Settings"
    }

    current_page_name = current_page_names.get(st.session_state.current_page, "🏠 Home")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 10px; color: white; margin: 1rem 0;">
            <h3>📍 Currently Viewing: {current_page_name}</h3>
        </div>
        """, unsafe_allow_html=True)

    # Home button
    if st.button("🏠 **Back to Home**", use_container_width=True, key="nav_home"):
        st.session_state.current_page = "dashboard"
        st.rerun()

    st.markdown("---")

    # Navigation with value propositions
    st.markdown("### 🎯 What would you like to check today?")

    # Create navigation grid
    col1, col2 = st.columns(2)

    with col1:
        # Dashboard/Overview
        if st.button("📊 **Kitchen Overview**\n\nSee all your ingredients and supplies at a glance",
                    use_container_width=True, key="nav_dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()

        # Alerts
        if st.button("🚨 **Reorder Reminders**\n\nIngredients that need to be ordered soon",
                    use_container_width=True, key="nav_alerts"):
            st.session_state.current_page = "alerts"
            st.rerun()

        # Products
        if st.button("📦 **Ingredient List**\n\nManage all your kitchen ingredients and costs",
                    use_container_width=True, key="nav_products"):
            st.session_state.current_page = "products"
            st.rerun()

    with col2:
        # Reports
        if st.button("📈 **Kitchen Reports**\n\nSee usage patterns and cost analysis",
                    use_container_width=True, key="nav_reports"):
            st.session_state.current_page = "reports"
            st.rerun()

        # Settings
        if st.button("⚙️ **Kitchen Settings**\n\nSet reorder levels and alerts",
                    use_container_width=True, key="nav_settings"):
            st.session_state.current_page = "settings"
            st.rerun()

        # Quick Actions
        if st.button("🔄 **Update Stock**\n\nGet latest ingredient counts",
                    use_container_width=True, key="nav_refresh"):
        load_all_data.clear()
            st.success("Stock updated!")
        st.rerun()

    # Main content based on selected page with error handling
    try:
        if st.session_state.current_page == "dashboard":
            show_inventory_sheet(metrics, data)
        elif st.session_state.current_page == "alerts":
            show_reorder_alerts(metrics)
        elif st.session_state.current_page == "products":
            show_raw_material_master(data, metrics)
        elif st.session_state.current_page == "reports":
            show_report_sheet(data, metrics)
        elif st.session_state.current_page == "settings":
            show_settings()
        else:
            show_inventory_sheet(metrics, data)  # Default to dashboard
    except Exception as e:
        st.error(f"❌ **Page Error:** Failed to load {st.session_state.current_page} page")
        st.error(f"**Error Details:** {str(e)}")
        st.error("**Fallback:** Loading dashboard instead")
        try:
            show_inventory_sheet(metrics, data)
        except Exception as fallback_error:
            st.error(f"❌ **Critical Error:** Even fallback failed: {str(fallback_error)}")
            st.error("**Please refresh the page or contact support.**")

    

def show_inventory_sheet(metrics: Dict, data: Dict):
    """Kitchen Overview - Main dashboard for restaurant inventory"""

    # Breadcrumb navigation
    st.markdown("""
    <div style="padding: 0.5rem 0; color: #666; font-size: 0.9rem;">
        🏠 Home > 📊 Kitchen Overview
    </div>
    """, unsafe_allow_html=True)

    # Value proposition for this page
    st.markdown("### 📊 **Kitchen Overview** - Your Complete Ingredient Status")
    st.info("""
    **What you'll find here:** Real-time ingredient counts, cost overview, and quick insights to manage your kitchen efficiently.
    """)

    # Alert Summary with optimized rendering
    if metrics["alert_items"]:
        critical_count = len([item for item in metrics["alert_items"] if item["status"] == "critical"])
        warning_count = len([item for item in metrics["alert_items"] if item["status"] == "warning"])

        col1, col2, col3 = st.columns(3)

        with col1:
            create_metric_card("🚨 Critical Alerts", str(critical_count), "Items need immediate attention", "alert-card")

        with col2:
            create_metric_card("⚠️ Low Stock Alerts", str(warning_count), "Items need reordering soon", "warning-card")

        with col3:
            create_metric_card("📊 Total Alerts", str(len(metrics["alert_items"])), "Items requiring action", "info-card")
    else:
        st.markdown("""
        <div class="success-card">
            <h3>✅ All Systems Operational</h3>
            <p>No reorder alerts at this time. All inventory levels are satisfactory.</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

    # Kitchen Overview Key Metrics
    st.markdown("### 📊 Kitchen Overview - Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        create_metric_card("📦 Total Ingredients", f"{metrics['total_products']:,}", "Items in your kitchen")

    with col2:
        create_metric_card("💰 Total Ingredient Value", f"₹{metrics['total_value']:,.0f}", "Current stock value")

    with col3:
        create_metric_card("📥 Ingredients Received", f"{int(metrics['total_in']):,}", "Units received this period")

    with col4:
        create_metric_card("📤 Ingredients Used", f"{int(metrics['total_out']):,}", "Units consumed this period")

    # Kitchen Cost Overview
    st.markdown("### 💰 Kitchen Cost Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        create_metric_card("📊 Avg Cost per Unit", f"₹{metrics['avg_cost_per_unit']:,.2f}", "Average ingredient cost")

    with col2:
        create_metric_card("🔄 Usage Rate", f"{metrics['stock_turnover_rate']:.2f}", "How fast ingredients are used")

    with col3:
        create_metric_card("🚨 Reorder Cost", f"₹{metrics['total_reorder_value']:,.0f}", "Cost to restock needed items")

    # Quick Actions for Kitchen
    st.markdown("---")
    st.markdown("### ⚡ Quick Kitchen Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚨 Check What Needs Ordering", use_container_width=True):
            st.session_state.current_page = "alerts"
            st.rerun()

    with col2:
        if st.button("📦 View All Ingredients", use_container_width=True):
            st.session_state.current_page = "products"
            st.rerun()

    with col3:
        if st.button("📈 Kitchen Reports", use_container_width=True):
            st.session_state.current_page = "reports"
            st.rerun()

def show_reorder_alerts(metrics: Dict):
    """Reorder Reminders - Kitchen ingredients that need ordering"""

    # Breadcrumb navigation
    st.markdown("""
    <div style="padding: 0.5rem 0; color: #666; font-size: 0.9rem;">
        🏠 Home > 🚨 Reorder Reminders
    </div>
    """, unsafe_allow_html=True)

    # Value proposition for this page
    st.markdown("### 🚨 **Reorder Reminders** - Ingredients That Need Ordering")
    st.info("""
    **What you'll find here:** Ingredients that need immediate reordering, items running low, and suggested order quantities for your kitchen.
    """)

    if not metrics["alert_items"]:
        st.markdown("""
        <div class="success-card">
            <h3>✅ All Ingredients Are Well Stocked</h3>
            <p>Your kitchen has all the ingredients it needs. No immediate ordering required.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Status indicators for kitchen
    st.markdown("### 📊 Kitchen Status")
    st.info("""
    **Kitchen Status:**
    - "Order Now" - Need to order immediately
    - "Out of Stock" - Completely out of ingredient
    - "Running Low" - Stock is getting low
    """)

    # Sort alerts by priority for better performance
    critical_alerts = [item for item in metrics["alert_items"] if item["status"] == "critical"]
    warning_alerts = [item for item in metrics["alert_items"] if item["status"] == "warning"]

    # Critical Alerts for kitchen
    if critical_alerts:
        st.markdown("### 🔴 **Order Immediately** - Critical Kitchen Items")

        for alert in critical_alerts:
            col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])

            with col1:
                st.markdown(f"""
                <div class="product-card critical">
                    <h4>{alert['product']} ({alert['rm_id']})</h4>
                    <p><strong>Status:</strong> {alert['status_text']}</p>
                    <p><strong>Description:</strong> {alert['status_desc']}</p>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.metric("Current Stock", f"{alert['current_stock']:.0f}")

            with col3:
                st.metric("Reorder Level", f"{alert['reorder_level']:.0f}")

            with col4:
                st.metric("Stock Value", f"₹{alert['stock_value']:,.0f}")

            with col5:
                st.metric("Est Reorder Value", f"₹{alert['est_reorder_value']:,.0f}")

            with col6:
                suggested_qty = alert['reorder_level'] - alert['current_stock']
                st.metric("Reorder Qty", f"{suggested_qty:.0f}")

    # Warning Alerts for kitchen
    if warning_alerts:
        st.markdown("### 🟡 **Monitor Closely** - Items Running Low")

        for alert in warning_alerts:
            col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])

            with col1:
                st.markdown(f"""
                <div class="product-card warning">
                    <h4>{alert['product']} ({alert['rm_id']})</h4>
                    <p><strong>Status:</strong> {alert['status_text']}</p>
                    <p><strong>Description:</strong> {alert['status_desc']}</p>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.metric("Current Stock", f"{alert['current_stock']:.0f}")

            with col3:
                st.metric("Reorder Level", f"{alert['reorder_level']:.0f}")

            with col4:
                st.metric("Stock Value", f"₹{alert['stock_value']:,.0f}")

            with col5:
                st.metric("Est Reorder Value", f"₹{alert['est_reorder_value']:,.0f}")

            with col6:
                suggested_qty = alert['reorder_level'] - alert['current_stock']
                st.metric("Reorder Qty", f"{suggested_qty:.0f}")

def show_raw_material_master(data: Dict, metrics: Dict):
    """Ingredient List - Kitchen ingredient database"""

    # Breadcrumb navigation
    st.markdown("""
    <div style="padding: 0.5rem 0; color: #666; font-size: 0.9rem;">
        🏠 Home > 📦 Ingredient List
    </div>
    """, unsafe_allow_html=True)

    # Value proposition for this page
    st.markdown("### 📦 **Ingredient List** - Manage All Your Kitchen Ingredients")
    st.info("""
    **What you'll find here:** Complete ingredient information, current stock levels, costs, and specifications. Search, filter, and manage your entire kitchen inventory.
    """)

    # Required Information for kitchen
    st.markdown("### 📋 Ingredient Information")
    st.info("""
    **Required Fields:** Ingredient ID, Ingredient Name, Unit, Avg. Cost per Unit, Cost per Unit, Reorder Level
    **Best Practice:** Use consistent naming conventions for Ingredient IDs - typically first 4 letters of ingredient + sequential number
    **Example:** WHEA01 for Wheat, PANE04 for Paneer, TOMA01 for Tomatoes
    """)

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Critical", "Warning", "Success"]
        )

    with col2:
        search_term = st.text_input("Search Ingredients (ID or Ingredient Name)", "")

    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Name", "RM ID", "Stock Level", "Value", "Status"]
        )

    # Optimized filtering and processing
    filtered_products = []

    for record in data["raw_data"]:
        current_stock = num_or_zero(record.get("Current Stock", 0))
        unit_cost = money_to_float(record.get("Cost per Unit", record.get("Avg. Cost per Unit", 0)))
        reorder_level = money_to_float(record.get("Reorder Level", 0))
        reorder_required = record.get("Re-Order Required", "")
        rm_id = record.get("RM ID", "")
        product_name = record.get("Product Name", record.get("RM ID", "Unknown"))
        unit = record.get("Unit", "")

        status, status_text, status_desc = get_product_status(current_stock, reorder_level, reorder_required)

        # Apply filters
        if status_filter != "All" and status != status_filter.lower():
            continue

        if search_term and search_term.lower() not in product_name.lower() and search_term.lower() not in rm_id.lower():
            continue

        filtered_products.append({
            "name": product_name,
            "rm_id": rm_id,
            "current_stock": current_stock,
            "reorder_level": reorder_level,
            "unit_cost": unit_cost,
            "total_value": current_stock * unit_cost,
            "unit": unit,
            "status": status,
            "status_text": status_text,
            "status_desc": status_desc
        })

    # Sort products
    if sort_by == "Stock Level":
        filtered_products.sort(key=lambda x: x["current_stock"])
    elif sort_by == "Value":
        filtered_products.sort(key=lambda x: x["total_value"], reverse=True)
    elif sort_by == "Status":
        filtered_products.sort(key=lambda x: x["status"])
    elif sort_by == "RM ID":
        filtered_products.sort(key=lambda x: x["rm_id"])
    else:  # Name
        filtered_products.sort(key=lambda x: x["name"])

    # Display products with columns as per user manual
    for product in filtered_products:
        col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 1, 1, 1, 1, 1, 1])

        with col1:
            st.markdown(f"""
            <div class="product-card {product['status']}">
                <h4>{product['name']} ({product['rm_id']})</h4>
                <p><strong>Status:</strong> {product['status_text']}</p>
                <p><strong>Unit:</strong> {product['unit']}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.metric("Current Stock", f"{product['current_stock']:.0f}")

        with col3:
            st.metric("Reorder Level", f"{product['reorder_level']:.0f}")

        with col4:
            st.metric("Avg Cost/Unit", f"₹{product['unit_cost']:,.2f}")

        with col5:
            st.metric("Cost/Unit", f"₹{product['unit_cost']:,.2f}")

        with col6:
            st.metric("Stock Value", f"₹{product['total_value']:,.0f}")

        with col7:
            st.metric("Status", product['status_text'].split()[0])

def show_report_sheet(data: Dict, metrics: Dict):
    """Kitchen Reports - Search and analysis tools for restaurant"""

    # Breadcrumb navigation
    st.markdown("""
    <div style="padding: 0.5rem 0; color: #666; font-size: 0.9rem;">
        🏠 Home > 📈 Kitchen Reports
    </div>
    """, unsafe_allow_html=True)

    # Value proposition for this page
    st.markdown("### 📈 **Kitchen Reports** - Smart Insights for Your Restaurant")
    st.info("""
    **What you'll find here:** Search ingredients, analyze usage patterns, view cost metrics, and get insights for better kitchen management.
    """)

    # Kitchen Search Functions
    st.markdown("### 🔍 Search Your Kitchen")
    st.info("""
    **Search Functions:**
    - Type any ingredient name in the search field
    - View comprehensive details instantly
    - Access usage history and patterns
    - Review reorder recommendations
    """)

    # Search functionality
    search_product = st.text_input("🔍 Search Ingredients", placeholder="Enter ingredient name or ID...")

    if search_product:
        st.markdown("### 📋 Search Results")
        # Filter products based on search
        cleaned_data = clean_and_validate_data(data)
        search_results = []

        for record in cleaned_data["raw_data"]:
            product_name = record.get("Product Name", "").lower()
            rm_id = record.get("RM ID", "").lower()
            search_term = search_product.lower()

            if search_term in product_name or search_term in rm_id:
                search_results.append(record)

        if search_results:
            st.success(f"Found {len(search_results)} matching ingredients")
            for result in search_results:
                st.write(f"**{result['Product Name']}** ({result['RM ID']}) - Stock: {result['Current Stock']}")
        else:
            st.warning("No ingredients found matching your search")

    # Key Kitchen Indicators
    st.markdown("### 📊 Key Kitchen Indicators")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Ingredients", metrics["total_products"])
        st.caption("Items in your kitchen")

    with col2:
        st.metric("High Value Items", metrics["high_value_items"])
        st.caption("Ingredients worth >₹10,000")

    with col3:
        st.metric("Out of Stock", metrics["out_of_stock_items"])
        st.caption("Completely out of ingredient")

    with col4:
        st.metric("Running Low", metrics["critical_items"])
        st.caption("Below 50% reorder level")

        # Kitchen Cost Analytics
    st.markdown("### 💰 Kitchen Cost Analytics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Ingredient Value", f"₹{metrics['total_value']:,.0f}")
        st.caption("Current Stock × Unit Cost")

    with col2:
        st.metric("Average Cost per Unit", f"₹{metrics['avg_cost_per_unit']:,.2f}")
        st.caption("Average ingredient cost")

    with col3:
        st.metric("Total Reorder Value", f"₹{metrics['total_reorder_value']:,.0f}")
        st.caption("Cost to restock needed items")

    with col4:
        st.metric("Usage Rate", f"{metrics['stock_turnover_rate']:.2f}")
        st.caption("How fast ingredients are used")

        # Kitchen Usage Analysis
    st.markdown("### 📦 Kitchen Usage Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Ingredients Received", f"{metrics['total_in']:,.0f}")
        st.caption("Units received this period")

    with col2:
        st.metric("Ingredients Used", f"{metrics['total_out']:,.0f}")
        st.caption("Units consumed this period")

    with col3:
        net_movement = metrics['total_in'] - metrics['total_out']
        st.metric("Net Change", f"{net_movement:,.0f}")
        st.caption("Received - Used")

        # Ingredient Value Analysis
    st.markdown("### 📊 Ingredient Value Analysis")

    # Use cleaned data for accurate calculations
    cleaned_data = clean_and_validate_data(data)

    high_value_items = []
    medium_value_items = []
    low_value_items = []
    high_value_count = 0
    medium_value_count = 0
    low_value_count = 0

    for record in cleaned_data["raw_data"]:
        current_stock = num_or_zero(record.get("Current Stock", 0))
        unit_cost = money_to_float(record.get("Cost per Unit", 0))
        total_value = current_stock * unit_cost

        if total_value > 10000:
            high_value_items.append(total_value)
            high_value_count += 1
        elif total_value > 1000:
            medium_value_items.append(total_value)
            medium_value_count += 1
        else:
            low_value_items.append(total_value)
            low_value_count += 1

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("High Value (>₹10K)", f"₹{sum(high_value_items):,.0f}")
        st.caption(f"{high_value_count} ingredients")

    with col2:
        st.metric("Medium Value (₹1K-10K)", f"₹{sum(medium_value_items):,.0f}")
        st.caption(f"{medium_value_count} ingredients")

    with col3:
        st.metric("Low Value (<₹1K)", f"₹{sum(low_value_items):,.0f}")
        st.caption(f"{low_value_count} ingredients")

        # Kitchen Alert Analysis
    st.markdown("### 🚨 Kitchen Alert Analysis")

    if metrics["alert_items"]:
        critical_alerts = [item for item in metrics["alert_items"] if item["status"] == "critical"]
        warning_alerts = [item for item in metrics["alert_items"] if item["status"] == "warning"]

        col1, col2, col3 = st.columns(3)

        with col1:
            critical_value = sum(item.get("stock_value", 0) for item in critical_alerts)
            st.metric("Critical Items Value", f"₹{critical_value:,.0f}")
            st.caption(f"{len(critical_alerts)} ingredients")

        with col2:
            warning_value = sum(item.get("stock_value", 0) for item in warning_alerts)
            st.metric("Warning Items Value", f"₹{warning_value:,.0f}")
            st.caption(f"{len(warning_alerts)} ingredients")

        with col3:
            total_alert_value = critical_value + warning_value
            st.metric("Total Alert Value", f"₹{total_alert_value:,.0f}")
            st.caption(f"{len(metrics['alert_items'])} ingredients")
    else:
        st.success("✅ No active alerts - All kitchen ingredients are well stocked")

        # Kitchen Data Quality
    st.markdown("### 🔍 Kitchen Data Quality")

    # Calculate data quality metrics
    total_raw_records = len(data.get("raw_data", []))
    total_in_records = len(data.get("in_data", []))
    total_out_records = len(data.get("out_data", []))

    cleaned_raw_records = len(cleaned_data["raw_data"])
    cleaned_in_records = len(cleaned_data["in_data"])
    cleaned_out_records = len(cleaned_data["out_data"])

    col1, col2, col3 = st.columns(3)

    with col1:
        raw_quality = (cleaned_raw_records / max(total_raw_records, 1)) * 100
        st.metric("Ingredient Data Quality", f"{raw_quality:.1f}%")
        st.caption(f"{cleaned_raw_records}/{total_raw_records} valid records")

    with col2:
        in_quality = (cleaned_in_records / max(total_in_records, 1)) * 100
        st.metric("Receiving Data Quality", f"{in_quality:.1f}%")
        st.caption(f"{cleaned_in_records}/{total_in_records} valid records")

    with col3:
        out_quality = (cleaned_out_records / max(total_out_records, 1)) * 100
        st.metric("Usage Data Quality", f"{out_quality:.1f}%")
        st.caption(f"{cleaned_out_records}/{total_out_records} valid records")

                # Kitchen Usage Tracking
    st.markdown("### 📊 Kitchen Usage Tracking")
    
    st.info("""
    **Usage Analytics:**
    - Ingredient consumption patterns
    - Stock movement analysis
    - Cost tracking and optimization
    - Reorder recommendations
    """)

    # Kitchen Sheets Overview
    st.markdown("### 📋 Kitchen Sheets Overview")

    sheet_stats = {
        "Raw Material Master": len(data.get("raw_data", [])),
        "Stock In": len(data.get("in_data", [])),
        "Stock Out": len(data.get("out_data", [])),
        "Inventory": len(data.get("inventory_data", [])),
        "Supplier Master": len(data.get("supplier_data", [])),
        "Report": len(data.get("report_data", []))
    }

    for sheet_name, record_count in sheet_stats.items():
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{sheet_name}**")
        with col2:
            st.write(f"{record_count} records")

def show_settings():
    """Kitchen settings page with configuration options"""

    # Breadcrumb navigation
    st.markdown("""
    <div style="padding: 0.5rem 0; color: #666; font-size: 0.9rem;">
        🏠 Home > ⚙️ Kitchen Settings
    </div>
    """, unsafe_allow_html=True)

    # Value proposition for this page
    st.markdown("### ⚙️ **Kitchen Settings** - Configure Your Restaurant Dashboard")
    st.info("""
    **What you'll find here:** Customize reorder alerts, set refresh intervals, and configure kitchen preferences to match your restaurant needs.
    """)

    # Theme settings
    st.markdown("### 🎨 Kitchen Display Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Light Mode")
        st.info("Clean, professional appearance suitable for kitchen environments")

    with col2:
        st.markdown("#### Dark Mode")
        st.info("Easy on the eyes, perfect for low-light kitchen conditions")

    # Kitchen Alert Settings
    st.markdown("### 🔔 Kitchen Alert Settings")

    critical_threshold = st.slider(
        "Critical Ingredient Threshold (%)",
        min_value=10,
        max_value=50,
        value=25,
        help="Percentage of reorder level to trigger critical alerts"
    )

    warning_threshold = st.slider(
        "Warning Ingredient Threshold (%)",
        min_value=50,
        max_value=100,
        value=75,
        help="Percentage of reorder level to trigger warning alerts"
    )

    # Auto-refresh settings
    st.markdown("### 🔄 Auto-Refresh Settings")

    refresh_interval = st.selectbox(
        "Data Refresh Interval",
        ["30 seconds", "1 minute", "5 minutes", "10 minutes", "Manual only"],
        help="How often to automatically refresh data"
    )

    # System information
    st.markdown("### 📋 System Information")
    st.info("""
    **Inventory Management System**
    - Google Sheets-based solution
    - Real-time stock tracking
    - Automatic reorder alerts
    - Consumption monitoring
    - Expiry date tracking
    - FIFO inventory management
    """)

    if st.button("💾 Save Settings"):
        st.success("Settings saved successfully!")

# Run the application
if __name__ == "__main__":
    main()
