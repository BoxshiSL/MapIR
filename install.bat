@echo off
setlocal
pushd "%~dp0"

echo === MapIR Studio installer ===
echo.

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
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    popd
    exit /b 1
)

echo Installing development requirements ...
pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [ERROR] pip install -r requirements-dev.txt failed.
    popd
    exit /b 1
)

echo Installing MapIR in editable mode ...
pip install -e .
if errorlevel 1 (
    echo [ERROR] pip install -e . failed.
    popd
    exit /b 1
)

echo.
echo === MapIR is ready. Available commands ===
echo.
echo   run_desktop.bat                 - launch MapIR Studio (PySide6)
echo   validate_examples.bat           - validate bundled examples
echo   render_examples.bat             - render SVG previews
echo   export_blockout_examples.bat    - export OBJ + Blender scripts
echo   preflight.bat                   - run repository preflight scan
echo   test.bat                        - run pytest
echo   lint.bat                        - run black + ruff (check only)
echo   format.bat                      - run black + ruff (auto-fix)
echo   build_exe.bat                   - build MapIR Studio.exe via PyInstaller
echo.
echo Or directly:
echo   python -m mapir.cli desktop
echo   python -m mapir.cli inspect examples\worlds\world_jisso_city.json
echo.

popd
endlocal
exit /b 0
