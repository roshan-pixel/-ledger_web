# C&F Portal Synchronization Documentation

## Overview
The Portal Sync module is a newly integrated feature of the Ledger God Mode Web App. It provides an automated, one-click synchronization mechanism between the Asclepius Wellness C&F online portal and the local `Asclepius_Wellness_PROFESSIONAL.xlsm` inventory master. 

By automating the web navigation and data extraction process, it eliminates manual entry errors and ensures that the local Excel inventory perfectly mirrors the online purchase records.

## How It Works

1. **Web Interface (UI)**: 
   A sleek, glassmorphism-styled dashboard (`portal_sync.html`) allows users to define the `From Date` and `To Date` for the sync operation. Predefined presets (Today, Last 7 Days, This Month) provide quick, seamless access.

2. **Backend Bridge (`app.py` & `portal_sync.py`)**: 
   When the user triggers "Sync Now", an API request is dispatched to `/api/portal_sync`. 
   The backend:
   - Uses **Playwright** (headless browser automation) to navigate to the Asclepius Wellness login page.
   - Automatically fills in the secure franchise credentials.
   - Navigates through the portal to the `PurchaseListn.aspx` (or relevant order lists).
   - Injects the specified date ranges and extracts the HTML/table data.

3. **Data Parsing & Aggregation**:
   The script parses the raw sales data using libraries such as `BeautifulSoup` and `pandas`. It extracts product names, HSN codes, and quantities sold within the selected date range.

4. **Excel Live Update**:
   Using `openpyxl`, the backend opens the `Asclepius_Wellness_PROFESSIONAL.xlsm` file, matches the extracted products against the `Inventory_Master` sheet, and updates the dynamically calculated columns (such as `Sold Qty (Jul 1-7)`). It also re-calculates all necessary bottom-row `TOTAL` formulas and ensures the `_KPI_Data` sheet remains completely accurate.

## Running the Sync

To trigger a sync:
1. Open the Ledger Web App dashboard.
2. Navigate to the **Portal Sync** sidebar menu.
3. Select the desired date range.
4. Click **Start Sync**. 

*Note: Ensure the `Asclepius_Wellness_PROFESSIONAL.xlsm` file is closed locally during the sync operation to prevent `PermissionError` file-locking issues.*
