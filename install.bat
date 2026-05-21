@echo off
setlocal
pushd "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv. Make sure Python 3.11+ is on PATH.
        popd
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Upgrading pip ...
python -m pip install --upgrade pip

echo Installing requirements ...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    popd
    exit /b 1
)

echo Installing MapIR in editable mode ...
pip install -e .

echo.
echo MapIR is ready. Try:
echo   validate_examples.bat
echo   render_examples.bat
echo   export_blockout_examples.bat
echo.
echo Or run directly:
echo   python -m mapir.cli inspect examples\worlds\world_jisso_city.json
echo.

popd
endlocal
