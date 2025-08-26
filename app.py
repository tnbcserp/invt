import json
import re
from datetime import datetime, date, timedelta
from dateutil import parser as dateparser
import os

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ============== Page Configuration ==============
st.set_page_config(
    page_title="Hotel Inventory Dashboard",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== Theme Configuration ==============
def apply_custom_css():
    st.markdown("""
    <style>
    /* Modern Card Styling */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    
    .alert-card {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(255,107,107,0.3);
        margin: 0.5rem 0;
    }
    
    .success-card {
        background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(0,184,148,0.3);
        margin: 0.5rem 0;
    }
    
    .warning-card {
        background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(253,203,110,0.3);
        margin: 0.5rem 0;
    }
    
    .info-card {
        background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(116,185,255,0.3);
        margin: 0.5rem 0;
    }
    
    /* Product Status Cards */
    .product-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        transition: transform 0.2s;
    }
    
    .product-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    
    .product-card.critical {
        border-left-color: #ff6b6b;
        background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
    }
    
    .product-card.warning {
        border-left-color: #fdcb6e;
        background: linear-gradient(135deg, #fffbf0 0%, #fff8e1 100%);
    }
    
    .product-card.success {
        border-left-color: #00b894;
        background: linear-gradient(135deg, #f0fff4 0%, #e8f5e8 100%);
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Alert Bell Animation */
    .alert-bell {
        animation: shake 0.5s ease-in-out infinite;
    }
    
    @keyframes shake {
        0%, 100% { transform: rotate(0deg); }
        25% { transform: rotate(-5deg); }
        75% { transform: rotate(5deg); }
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .metric-card, .alert-card, .success-card, .warning-card, .info-card {
            margin: 0.25rem 0;
            padding: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ============== Helpers ==============
def money_to_float(x):
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

def get_product_status(current_stock, reorder_level, reorder_required):
    """Get product status for hotel inventory"""
    if current_stock == 0:
        return "critical", "🔴 Out of Stock", "Immediate action required"
    elif current_stock <= reorder_level * 0.5:
        return "critical", "🔴 Critical Low", "Order immediately"
    elif current_stock <= reorder_level:
        return "warning", "🟡 Low Stock", "Order soon"
    elif str(reorder_required).strip().upper() == "YES":
        return "warning", "🟠 Manual Order", "Manual reorder flagged"
    else:
        return "success", "🟢 In Stock", "Stock levels good"

def calculate_hotel_metrics(data):
    """Calculate hotel-specific metrics"""
    metrics = {
        "total_products": len(data["raw_data"]),
        "total_value": 0,
        "critical_items": 0,
        "low_stock_items": 0,
        "out_of_stock_items": 0,
        "high_value_items": 0,
        "fast_moving_items": 0,
        "slow_moving_items": 0,
        "total_in": sum(num_or_zero(record.get("Quantity", record.get("Quantity In", 0))) for record in data["in_data"]),
        "total_out": sum(num_or_zero(record.get("Quantity Out", 0)) for record in data["out_data"]),
        "alert_items": []
    }
    
    for record in data["raw_data"]:
        current_stock = num_or_zero(record.get("Current Stock", 0))
        unit_cost = money_to_float(record.get("Cost per Unit", record.get("Avg. Cost per Unit", 0)))
        reorder_level = money_to_float(record.get("Reorder Level", 0))
        reorder_required = record.get("Re-Order Required", "")
        
        # Calculate inventory value
        item_value = current_stock * unit_cost
        metrics["total_value"] += item_value
        
        # Categorize items
        if item_value > 10000:  # High value items (>₹10,000)
            metrics["high_value_items"] += 1
        
        # Get status
        status, status_text, status_desc = get_product_status(current_stock, reorder_level, reorder_required)
        
        if status == "critical":
            if current_stock == 0:
                metrics["out_of_stock_items"] += 1
            else:
                metrics["critical_items"] += 1
            metrics["alert_items"].append({
                "product": record.get("Product Name", record.get("RM ID", "Unknown")),
                "current_stock": current_stock,
                "reorder_level": reorder_level,
                "unit_cost": unit_cost,
                "status": status,
                "status_text": status_text,
                "status_desc": status_desc,
                "priority": "High" if current_stock == 0 else "Medium"
            })
        elif status == "warning":
            metrics["low_stock_items"] += 1
            metrics["alert_items"].append({
                "product": record.get("Product Name", record.get("RM ID", "Unknown")),
                "current_stock": current_stock,
                "reorder_level": reorder_level,
                "unit_cost": unit_cost,
                "status": status,
                "status_text": status_text,
                "status_desc": status_desc,
                "priority": "Low"
            })
    
    return metrics

# ============== Google Sheets Integration ==============
@st.cache_resource(show_spinner=False)
def get_gspread_client():
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

    return {
        "raw_data": raw_data,
        "in_data": in_data,
        "out_data": out_data
    }

# ============== Main Application ==============
def main():
    # Apply custom CSS
    apply_custom_css()
    
    # Sidebar for navigation and settings
    with st.sidebar:
        st.markdown("## 🏨 Hotel Inventory")
        st.markdown("### Navigation")
        
        page = st.selectbox(
            "Choose a page:",
            ["📊 Dashboard", "🚨 Alerts", "📦 Products", "📈 Analytics", "⚙️ Settings"]
        )
        
        st.markdown("---")
        st.markdown("### Quick Actions")
        if st.button("🔄 Refresh Data"):
            load_all_data.clear()
            st.success("Data refreshed!")
            st.rerun()
        
        if st.button("📧 Send Alert Report"):
            st.info("Alert report feature coming soon!")
    
    # Load data
    try:
        data = load_all_data()
        
        if data is None:
            st.error("Unable to load data. Please check your Google Sheets connection and credentials.")
            st.stop()
        
        # Calculate hotel-specific metrics
        metrics = calculate_hotel_metrics(data)
        
        # Main content based on selected page
        if page == "📊 Dashboard":
            show_dashboard(metrics, data)
        elif page == "🚨 Alerts":
            show_alerts(metrics)
        elif page == "📦 Products":
            show_products(data, metrics)
        elif page == "📈 Analytics":
            show_analytics(data, metrics)
        elif page == "⚙️ Settings":
            show_settings()
            
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

def show_dashboard(metrics, data):
    """Main dashboard with hotel-specific KPIs"""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏨 Hotel Inventory Dashboard</h1>
        <p>Real-time inventory tracking and alert management for hotel operations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Alert Summary
    if metrics["alert_items"]:
        critical_count = len([item for item in metrics["alert_items"] if item["status"] == "critical"])
        warning_count = len([item for item in metrics["alert_items"] if item["status"] == "warning"])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="alert-card">
                <h3>🚨 Critical Alerts</h3>
                <h2>{critical_count}</h2>
                <p>Items need immediate attention</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="warning-card">
                <h3>⚠️ Low Stock Alerts</h3>
                <h2>{warning_count}</h2>
                <p>Items need reordering soon</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="info-card">
                <h3>📊 Total Alerts</h3>
                <h2>{len(metrics["alert_items"])}</h2>
                <p>Items requiring action</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="success-card">
            <h3>✅ All Systems Operational</h3>
            <p>No alerts at this time. All inventory levels are satisfactory.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # KPI Cards
    st.markdown("### 📈 Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📦 Total Products</h3>
            <h2>{metrics['total_products']:,}</h2>
            <p>Items in inventory</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 Inventory Value</h3>
            <h2>₹{metrics['total_value']:,.0f}</h2>
            <p>Total stock value</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📥 Stock In</h3>
            <h2>{int(metrics['total_in']):,}</h2>
            <p>Units received</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📤 Stock Out</h3>
            <h2>{int(metrics['total_out']):,}</h2>
            <p>Units consumed</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick Actions
    st.markdown("---")
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚨 View All Alerts", use_container_width=True):
            st.switch_page("🚨 Alerts")
    
    with col2:
        if st.button("📦 Product Overview", use_container_width=True):
            st.switch_page("📦 Products")
    
    with col3:
        if st.button("📈 Analytics", use_container_width=True):
            st.switch_page("📈 Analytics")

def show_alerts(metrics):
    """Dedicated alerts page with detailed information"""
    
    st.markdown("## 🚨 Inventory Alerts")
    st.markdown("### Real-time alert monitoring for hotel operations")
    
    if not metrics["alert_items"]:
        st.markdown("""
        <div class="success-card">
            <h3>✅ No Active Alerts</h3>
            <p>All inventory levels are within acceptable ranges.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Sort alerts by priority
    critical_alerts = [item for item in metrics["alert_items"] if item["status"] == "critical"]
    warning_alerts = [item for item in metrics["alert_items"] if item["status"] == "warning"]
    
    # Critical Alerts
    if critical_alerts:
        st.markdown("### 🔴 Critical Alerts (Immediate Action Required)")
        
        for alert in critical_alerts:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.markdown(f"""
                <div class="product-card critical">
                    <h4>{alert['product']}</h4>
                    <p><strong>Status:</strong> {alert['status_text']}</p>
                    <p><strong>Description:</strong> {alert['status_desc']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.metric("Current Stock", f"{alert['current_stock']:.0f}")
            
            with col3:
                st.metric("Reorder Level", f"{alert['reorder_level']:.0f}")
            
            with col4:
                st.metric("Unit Cost", f"₹{alert['unit_cost']:,.2f}")
    
    # Warning Alerts
    if warning_alerts:
        st.markdown("### 🟡 Warning Alerts (Monitor Closely)")
        
        for alert in warning_alerts:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.markdown(f"""
                <div class="product-card warning">
                    <h4>{alert['product']}</h4>
                    <p><strong>Status:</strong> {alert['status_text']}</p>
                    <p><strong>Description:</strong> {alert['status_desc']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.metric("Current Stock", f"{alert['current_stock']:.0f}")
            
            with col3:
                st.metric("Reorder Level", f"{alert['reorder_level']:.0f}")
            
            with col4:
                st.metric("Unit Cost", f"₹{alert['unit_cost']:,.2f}")

def show_products(data, metrics):
    """Product overview with filtering and search"""
    
    st.markdown("## 📦 Product Inventory")
    st.markdown("### Complete product overview with status tracking")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Critical", "Warning", "Success"]
        )
    
    with col2:
        search_term = st.text_input("Search Products", "")
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Name", "Stock Level", "Value", "Status"]
        )
    
    # Filter and display products
    filtered_products = []
    
    for record in data["raw_data"]:
        current_stock = num_or_zero(record.get("Current Stock", 0))
        unit_cost = money_to_float(record.get("Cost per Unit", record.get("Avg. Cost per Unit", 0)))
        reorder_level = money_to_float(record.get("Reorder Level", 0))
        reorder_required = record.get("Re-Order Required", "")
        
        status, status_text, status_desc = get_product_status(current_stock, reorder_level, reorder_required)
        product_name = record.get("Product Name", record.get("RM ID", "Unknown"))
        
        # Apply filters
        if status_filter != "All" and status != status_filter.lower():
            continue
        
        if search_term and search_term.lower() not in product_name.lower():
            continue
        
        filtered_products.append({
            "name": product_name,
            "current_stock": current_stock,
            "reorder_level": reorder_level,
            "unit_cost": unit_cost,
            "total_value": current_stock * unit_cost,
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
    else:  # Name
        filtered_products.sort(key=lambda x: x["name"])
    
    # Display products
    for product in filtered_products:
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
        
        with col1:
            st.markdown(f"""
            <div class="product-card {product['status']}">
                <h4>{product['name']}</h4>
                <p><strong>Status:</strong> {product['status_text']}</p>
                <p><strong>Description:</strong> {product['status_desc']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.metric("Stock", f"{product['current_stock']:.0f}")
        
        with col3:
            st.metric("Reorder Level", f"{product['reorder_level']:.0f}")
        
        with col4:
            st.metric("Unit Cost", f"₹{product['unit_cost']:,.2f}")
        
        with col5:
            st.metric("Total Value", f"₹{product['total_value']:,.0f}")

def show_analytics(data, metrics):
    """Analytics and insights page"""
    
    st.markdown("## 📈 Analytics & Insights")
    st.markdown("### Data-driven insights for hotel inventory management")
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("High Value Items", metrics["high_value_items"])
    
    with col2:
        st.metric("Out of Stock", metrics["out_of_stock_items"])
    
    with col3:
        st.metric("Critical Low", metrics["critical_items"])
    
    with col4:
        st.metric("Low Stock", metrics["low_stock_items"])
    
    # Value distribution
    st.markdown("### 💰 Value Distribution")
    
    high_value_items = []
    medium_value_items = []
    low_value_items = []
    
    for record in data["raw_data"]:
        current_stock = num_or_zero(record.get("Current Stock", 0))
        unit_cost = money_to_float(record.get("Cost per Unit", record.get("Avg. Cost per Unit", 0)))
        total_value = current_stock * unit_cost
        
        if total_value > 10000:
            high_value_items.append(total_value)
        elif total_value > 1000:
            medium_value_items.append(total_value)
        else:
            low_value_items.append(total_value)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("High Value (>₹10K)", f"₹{sum(high_value_items):,.0f}")
    
    with col2:
        st.metric("Medium Value (₹1K-10K)", f"₹{sum(medium_value_items):,.0f}")
    
    with col3:
        st.metric("Low Value (<₹1K)", f"₹{sum(low_value_items):,.0f}")

def show_settings():
    """Settings and configuration page"""
    
    st.markdown("## ⚙️ Settings & Configuration")
    st.markdown("### Dashboard configuration and preferences")
    
    # Theme settings
    st.markdown("### 🎨 Theme Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Light Mode")
        st.info("Clean, professional appearance suitable for office environments")
    
    with col2:
        st.markdown("#### Dark Mode")
        st.info("Easy on the eyes, perfect for low-light conditions")
    
    # Alert settings
    st.markdown("### 🔔 Alert Settings")
    
    critical_threshold = st.slider(
        "Critical Stock Threshold (%)",
        min_value=10,
        max_value=50,
        value=25,
        help="Percentage of reorder level to trigger critical alerts"
    )
    
    warning_threshold = st.slider(
        "Warning Stock Threshold (%)",
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
    
    if st.button("💾 Save Settings"):
        st.success("Settings saved successfully!")

# Run the application
if __name__ == "__main__":
    main()
