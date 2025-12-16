@echo off
setlocal
set "REMOTE_SERVER_PATH=\\hcwda30449e\Validation-Tool"
echo.
echo Starting deployment...
set "SOURCE_PATH=%~dp0"
if "%SOURCE_PATH:~-1%"=="\" set "SOURCE_PATH=%SOURCE_PATH:~0,-1%"
echo.
echo Source: %SOURCE_PATH%
echo Destination: %REMOTE_SERVER_PATH%
echo.
robocopy "%SOURCE_PATH%" "%REMOTE_SERVER_PATH%" /E /PURGE /R:3 /W:5 /XJ ^
/XF "*.tmp" "*.bat" "*~" "~*" ".gitignore" "Readme.md" "launcher.spec" "launcher.py" "validation-ui.spec" "ValidationLauncherSetup.exe" ^
/XD ".venv" "__pycache__" ".vscode" "logs" ".git" ".github" "build" "installer" "packaging" "venv"
if %errorlevel% leq 8 (
    echo.
    echo Deployment completed successfully!
) else (
    echo.
    echo [WARNING]: Deployment finished with errors. Please check the log above.
)
echo.
pause
