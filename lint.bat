@echo off
setlocal
pushd "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run install.bat first.
    popd
    exit /b 1
)
call ".venv\Scripts\activate.bat"

echo === black --check ===
black --check mapir tests scripts
if errorlevel 1 set BLACK_FAILED=1

echo.
echo === ruff check ===
ruff check mapir tests scripts
if errorlevel 1 set RUFF_FAILED=1

if defined BLACK_FAILED (
    echo [FAIL] black reported issues.
    popd
    exit /b 1
)
if defined RUFF_FAILED (
    echo [FAIL] ruff reported issues.
    popd
    exit /b 1
)
echo [OK] lint passed.

popd
endlocal & exit /b 0
