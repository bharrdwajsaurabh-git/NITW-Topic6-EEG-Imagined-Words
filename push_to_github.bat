@echo off
echo ========================================================
echo   Pushing NITW Topic 6 EEG Project to GitHub
echo   Account: bharrdwajsaurabh-git
echo ========================================================
echo.

cd /d "%~dp0"

echo Current remote:
git remote -v
echo.

echo Pushing main branch to GitHub...
git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================================
    echo [SUCCESS] Project successfully uploaded to GitHub!
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo [NOTE] If you got 'Repository not found', please first create
    echo the empty repository at: https://github.com/new
    echo with the name: NITW-Topic6-EEG-Imagined-Words
    echo (Do not initialize with README or license).
    echo ========================================================
)

pause
