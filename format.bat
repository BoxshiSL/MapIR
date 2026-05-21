@echo off
setlocal
pushd "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run install.bat first.
    popd
    exit /b 1
)
call ".venv\Scripts\activate.bat"

echo === black ===
black mapir tests scripts
if errorlevel 1 (
    popd
    exit /b 1
)

echo.
echo === ruff --fix ===
ruff check mapir tests scripts --fix
set RC=%ERRORLEVEL%

popd
endlocal & exit /b %RC%
