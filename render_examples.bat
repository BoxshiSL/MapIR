@echo off
setlocal
pushd "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run install.bat first.
    popd
    exit /b 1
)
call ".venv\Scripts\activate.bat"

if not exist "output\svg" mkdir "output\svg"

echo === Rebuilding demo fixtures from templates ===
python scripts\build_demo_fixtures.py
if errorlevel 1 (
    echo [FAIL] demo fixture build
    popd
    exit /b 1
)

echo.
echo === Rendering demo SVGs ===
for %%F in (examples\demos\*.json) do (
    python -m mapir.cli render-svg "%%F" --out "output\svg\%%~nF.svg"
    if errorlevel 1 (
        echo [FAIL] %%F
        popd
        exit /b 1
    )
)

echo.
echo [OK] SVGs written to output\svg\

popd
endlocal
