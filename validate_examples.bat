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

echo === Validating worlds ===
for %%F in (examples\worlds\*.json) do (
    echo.
    echo --- %%F ---
    python -m mapir.cli validate "%%F"
    if errorlevel 1 set FAILED=1
)

echo.
echo === Validating scenes ===
for %%F in (examples\scenes\*.json) do (
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
echo [OK] All examples validated successfully.

popd
endlocal
