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

echo Switching to main branch...
git rev-parse --verify main >nul 2>&1
if errorlevel 1 (
    git checkout -b main origin/main
) else (
    git checkout main
    git reset --hard origin/main
)
if not %errorlevel%==0 goto checkouterror

echo.
echo Sync complete (main branch, verified stable). Please reload the plugin in QGIS.
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
echo ERROR: Failed to switch to main branch.
pause
exit /b 1
