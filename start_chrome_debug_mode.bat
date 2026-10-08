@echo off
title Google Maps Scraper - Live Chrome Connector
cls
echo =====================================================================
echo       Google Maps Lead Scraper - Live Chrome Debug Mode
echo =====================================================================
echo.
echo This script launches your Google Chrome browser with Remote Debugging
echo enabled on port 9222.
echo.
echo The scraper will automatically detect and attach directly to this Chrome
echo browser, using your existing Google accounts and logins!
echo.
echo NOTE: Google Chrome must be closed first so it can open port 9222.
echo.
echo Press any key to close existing Chrome and start debug mode...
pause >nul
echo.
echo Closing Chrome...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 >nul

echo Starting Google Chrome on port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --profile-directory="Profile 1"

echo.
echo =====================================================================
echo [SUCCESS] Chrome is now running in Remote Debugging Mode!
echo.
echo You can now return to the LeadGenPro Web UI (http://localhost:5000)
echo and click 'Refresh Status' or start scraping immediately.
echo =====================================================================
echo.
pause
