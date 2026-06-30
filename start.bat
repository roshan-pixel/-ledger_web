@echo off
echo ===========================================
echo Starting Asclepius Ledger GOD MODE Server
echo ===========================================
echo.
echo Installing dependencies if missing...
pip install flask pywin32 --quiet

echo Starting Flask server...
start http://127.0.0.1:5000
python app.py
pause
