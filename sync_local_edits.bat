@echo off
setlocal
cd /d "C:\claude\project\pointer_geocoding"

set BRANCH_NAME=local-edits

echo This will move uncommitted changes on the current branch (expected: test)
echo to the "%BRANCH_NAME%" branch and force-push it to origin.
echo.
choice /c YN /m "Continue"
if errorlevel 2 goto cancelled
if errorlevel 1 goto proceed

:proceed
echo.
echo Checking for local changes...
git diff --quiet
if not %errorlevel%==0 goto haschanges
git diff --cached --quiet
if not %errorlevel%==0 goto haschanges
git status --porcelain | findstr "^??" >nul
if %errorlevel%==0 goto haschanges

echo.
echo No changes to sync.
pause
goto :eof

:haschanges
echo.
echo Local changes detected. Stashing (including untracked files)...
git stash push -u -m "sync_local_edits temp stash"
if not %errorlevel%==0 goto stasherror

echo.
echo Removing any existing local "%BRANCH_NAME%" branch...
git branch -D %BRANCH_NAME% >nul 2>&1

echo.
echo Creating new "%BRANCH_NAME%" branch from current branch...
git checkout -b %BRANCH_NAME%
if not %errorlevel%==0 goto checkouterror

echo.
echo Restoring stashed changes onto "%BRANCH_NAME%"...
git stash pop
if not %errorlevel%==0 goto stashpoperror

echo.
echo Staging and committing changes...
git add -A
git commit -m "Local edits synced via sync_local_edits.bat (%date% %time%)"
if not %errorlevel%==0 goto commiterror

echo.
echo Pushing "%BRANCH_NAME%" to origin (force)...
git push -u origin %BRANCH_NAME% --force
if not %errorlevel%==0 goto pusherror

echo.
echo Returning to test branch...
git checkout test
if not %errorlevel%==0 goto returnerror

echo.
echo Sync complete. Local edits are now on branch "%BRANCH_NAME%" and pushed to origin.
echo Please tell your Claude Code session that branch "%BRANCH_NAME%" has been pushed.
pause
goto :eof

:cancelled
echo.
echo Cancelled. No changes were made.
pause
exit /b 1

:stasherror
echo.
echo ERROR: git stash push failed.
pause
exit /b 1

:checkouterror
echo.
echo ERROR: Failed to create/checkout "%BRANCH_NAME%" branch.
echo Your changes are still safely stashed. Run "git stash list" to check.
pause
exit /b 1

:stashpoperror
echo.
echo ERROR: git stash pop failed (possible conflict).
echo Resolve manually, then commit and push branch "%BRANCH_NAME%" yourself.
pause
exit /b 1

:commiterror
echo.
echo ERROR: git commit failed.
pause
exit /b 1

:pusherror
echo.
echo ERROR: git push failed. Check your network connection and permissions.
pause
exit /b 1

:returnerror
echo.
echo ERROR: Failed to switch back to test branch.
echo Your changes were committed and pushed to "%BRANCH_NAME%" successfully.
echo Please switch back to test manually (e.g. run sync_test.bat).
pause
exit /b 1
