@echo off
setlocal
pushd "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run install.bat first.
    popd
    exit /b 1
)
call ".venv\Scripts\activate.bat"

if not exist "output\obj"     mkdir "output\obj"
if not exist "output\blender" mkdir "output\blender"

echo === Rebuilding demo fixtures from templates ===
python scripts\build_demo_fixtures.py
if errorlevel 1 (
    echo [FAIL] demo fixture build
    popd
    exit /b 1
)

echo.
echo === Exporting OBJ + Blender for demos ===
for %%F in (examples\demos\*.json) do (
    python -m mapir.cli export-obj     "%%F" --out "output\obj\%%~nF.obj"
    if errorlevel 1 ( echo [FAIL OBJ] %%F & popd & exit /b 1 )
    python -m mapir.cli export-blender "%%F" --out "output\blender\%%~nF.py"
    if errorlevel 1 ( echo [FAIL BLENDER] %%F & popd & exit /b 1 )
)

echo.
echo [OK] Blockouts written to output\obj\ and output\blender\

popd
endlocal
