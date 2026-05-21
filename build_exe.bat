@echo off
setlocal
pushd "%~dp0"

echo === MapIR Studio exe build ===
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run install.bat first.
    popd
    exit /b 1
)
call ".venv\Scripts\activate.bat"

REM Make sure PyInstaller is installed (it is in requirements-dev.txt).
python -c "import PyInstaller" 1>nul 2>nul
if errorlevel 1 (
    echo [INFO] PyInstaller missing — installing from requirements-dev.txt ...
    pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo [ERROR] failed to install PyInstaller.
        popd
        exit /b 1
    )
)

echo --- preflight ---
python -m mapir.cli preflight
if errorlevel 1 (
    echo [ERROR] preflight failed — fix issues before building.
    popd
    exit /b 1
)

if exist "build" (
    echo Cleaning build\ ...
    rmdir /S /Q build
)
if exist "dist\MapIR-Studio" (
    echo Cleaning dist\MapIR-Studio ...
    rmdir /S /Q "dist\MapIR-Studio"
)

echo.
echo --- pyinstaller ---
pyinstaller --noconfirm --clean MapIR-Studio.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    popd
    exit /b 1
)

echo.
if exist "dist\MapIR-Studio\MapIR Studio.exe" (
    echo [OK] Built: dist\MapIR-Studio\MapIR Studio.exe
) else (
    echo [WARN] Build finished but expected exe path not found.
    echo        Inspect dist\MapIR-Studio\ for the produced binary.
)

popd
endlocal & exit /b 0
