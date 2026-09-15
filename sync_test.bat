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
if not %errorlevel%==0 goto fetcherror

echo Switching to test branch...
git rev-parse --verify test >nul 2>&1
if errorlevel 1 (
    git checkout -b test origin/test
) else (
    git checkout test
    git reset --hard origin/test
)
if not %errorlevel%==0 goto checkouterror

echo.
echo Sync complete (test branch). Please reload the plugin in QGIS.
pause
goto :eof

:dirty
echo.
echo WARNING: You have uncommitted local changes. Commit or discard them before syncing.
git status
pause
exit /b 1

:fetcherror
echo.
echo ERROR: git fetch failed. Check your network connection.
pause
exit /b 1

:checkouterror
echo.
echo ERROR: Failed to switch to test branch.
pause
exit /b 1
