@echo off
setlocal
pushd "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run install.bat first.
    popd
    exit /b 1
)
call ".venv\Scripts\activate.bat"

python -m mapir.cli desktop %*
set RC=%ERRORLEVEL%

popd
endlocal & exit /b %RC%
