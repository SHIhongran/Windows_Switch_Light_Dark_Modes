@echo off

REM 检查 PyInstaller 是否已安装
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Failed to install PyInstaller. Please install it manually.
        exit /b 1
    )
)

REM 使用 PyInstaller 打包
pyinstaller --noconfirm --onefile --windowed --name "ThemeSwitcher" ^
    --icon="icon.ico" ^
    --add-data "toggle_theme.bat;." ^
    --add-data "toggle_and_restart.bat;." ^
    --add-data "restart_explorer_only.bat;." ^
    theme_switcher.py

echo.
echo Build complete. You can find the executable in the 'dist' folder.
pause