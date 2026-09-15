@echo off
cd /d "C:\claude\project\pointer_geocoding"
echo === GitHubから最新化します ===
git fetch origin
git status --porcelain > "%TEMP%\git_status_check.txt"
for %%A in ("%TEMP%\git_status_check.txt") do set size=%%~zA
if not "%size%"=="0" (
    echo.
    echo [警告] ローカルに未コミットの変更があります。先にコミットまたは破棄してください。
    git status
    del "%TEMP%\git_status_check.txt"
    pause
    exit /b 1
)
del "%TEMP%\git_status_check.txt"
git pull origin main
echo.
echo === 同期完了。QGISでプラグインをリロードしてください。 ===
pause
