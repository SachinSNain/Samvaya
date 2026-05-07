@echo off
title UBID Platform - Shutdown
color 0C

cd /d "%~dp0"

echo.
echo  ================================================
echo   UBID SAMVAYA PLATFORM  --  SHUTDOWN
echo  ================================================
echo.
echo  Stopping Docker containers...

docker compose down

echo.
echo  [OK] Postgres and Backend containers stopped.
echo.
echo  Note: The React frontend window (npm start) must be
echo  closed manually with Ctrl+C in its terminal.
echo.
echo  To wipe the database and start completely fresh, run:
echo    docker compose down -v
echo  WARNING: that deletes all data.
echo.
pause
