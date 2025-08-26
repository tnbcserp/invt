# Inventory Dashboard

A comprehensive Streamlit-based inventory management dashboard that connects to Google Sheets for real-time inventory tracking and alert management.

## Features

- 🔔 **Real-time Alert System**: Detects items out of stock, below reorder level, or flagged for reorder
- 📊 **KPI Dashboard**: Total products, stock in/out, inventory value, and alert counts
- 📈 **Interactive Charts**: Stock trends, value distribution, and alert severity breakdown
- 📋 **Alert History**: Track alert changes over time with session-based history
- ➕ **Stock Management**: Add stock in/out entries directly to Google Sheets
- 🎨 **Conditional Formatting**: Visual indicators for different alert levels
- 🔍 **Search & Filter**: Find products quickly with advanced filtering options

## Deployment on Render

### Prerequisites

1. **Google Sheets API Setup**:
   - Create a Google Cloud Project
   - Enable Google Sheets API
   - Create a service account and download credentials JSON
   - Share your Google Sheet with the service account email

2. **Google Sheet Structure**:
   - **Raw Material Master**: Product details, reorder levels, costs
   - **Stock In**: Stock in transactions
   - **Stock Out**: Stock out transactions

### Deployment Steps

1. **Fork/Clone this repository** to your GitHub account

2. **Set up Render**:
   - Go to [render.com](https://render.com)
   - Sign up/Login with your GitHub account
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

3. **Configure Environment Variables**:
   - In Render dashboard, go to your service settings
   - Add environment variable:
     - **Key**: `GOOGLE_CREDENTIALS_JSON`
     - **Value**: Paste your entire Google service account JSON credentials

4. **Deploy**:
   - Render will automatically detect the `render.yaml` configuration
   - Click "Create Web Service"
   - Wait for build and deployment to complete

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CREDENTIALS_JSON` | Google service account credentials JSON | Yes |

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up credentials**:
   - Create `.streamlit/secrets.toml` file
   - Add your Google credentials:
   ```toml
   GOOGLE_CREDENTIALS_JSON = '''
   {
     "type": "service_account",
     "project_id": "your-project-id",
     ...
   }
   '''
   ```

3. **Run locally**:
   ```bash
   streamlit run app.py
   ```

## Alert System

The dashboard detects three types of alerts:

1. **Critical**: Items with zero stock (Out of Stock)
2. **High**: Items manually flagged for reorder
3. **Medium**: Items below reorder level

## Data Flow

1. **Google Sheets** → **Streamlit App** → **Real-time Dashboard**
2. **User Input** → **Google Sheets** → **Automatic Refresh**
3. **Alert Detection** → **Session History** → **Trend Analysis**

## Support

For issues or questions:
- Check the Google Sheets API setup
- Verify service account permissions
- Ensure Google Sheet structure matches expected format

## License

MIT License - feel free to use and modify as needed.
