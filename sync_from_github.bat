@echo off
setlocal
cd /d "C:\claude\project\pointer_geocoding"

echo Checking for local changes...
git diff --quiet
if not %errorlevel%==0 goto dirty
git diff --cached --quiet
if not %errorlevel%==0 goto dirty

echo Fetching from GitHub...
git fetch origin
git pull origin main
echo.
echo Sync complete. Please reload the plugin in QGIS.
pause
goto :eof

:dirty
echo.
echo WARNING: You have uncommitted local changes. Commit or discard them before syncing.
git status
pause
exit /b 1
