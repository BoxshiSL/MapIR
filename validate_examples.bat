@echo off
setlocal
pushd "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run install.bat first.
    popd
    exit /b 1
)
call ".venv\Scripts\activate.bat"

set FAILED=0

REM Make sure demos are up-to-date before validating. The script is idempotent.
echo === Rebuilding demo fixtures from templates ===
python scripts\build_demo_fixtures.py
if errorlevel 1 set FAILED=1

echo.
echo === Validating demos ===
for %%F in (examples\demos\*.json) do (
    echo.
    echo --- %%F ---
    python -m mapir.cli validate "%%F"
    if errorlevel 1 set FAILED=1
)

echo.
if "%FAILED%"=="1" (
    echo [FAIL] One or more files failed validation.
    popd
    exit /b 1
)
echo [OK] All demos validated successfully.

popd
endlocal
