@echo off
cd /d %~dp0
where python >nul 2>nul
if errorlevel 1 (
  echo Python install nahi hai.
  echo python.org se Python install karein. Add Python to PATH ka box tick karein.
  echo Phir SETUP.bat dobara chalayein.
  pause
  exit /b
)
python -m pip install -r requirements.txt
python make_shortcut.py
echo.
echo Taiyar! Desktop par "Shifa Medical Centre" ka icon ban gaya hai.
echo Ab sirf us icon par double click karein.
pause
