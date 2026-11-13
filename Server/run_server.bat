@echo off
title Smart Agriculture IoT Backend Server
color 0A
echo ========================================================
echo    KHOI DONG BACKEND SERVER FASTAPI (SMART FARM)
echo ========================================================
echo.
echo Dang kiem tra dia chi IP may tinh...
ipconfig | findstr /i "IPv4"
echo.
python -c "import fastapi, uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo [CANH BAO] Chua cai dat day du thu vien Python!
    echo Dang tien hanh cai dat cac goi tu requirements.txt...
    python -m pip install -r requirements.txt
    echo.
)
echo Dang khoi chay Uvicorn tai port 8000 (Host: 0.0.0.0)...
echo Nhan Ctrl + C de dung server bat cu luc nao.
echo ========================================================
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
