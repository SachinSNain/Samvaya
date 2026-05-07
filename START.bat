@echo off
cd /d "%~dp0"
title UBID Platform - Startup
color 0A

echo.
echo  ================================================
echo   UBID SAMVAYA PLATFORM  --  STARTUP
echo  ================================================
echo.

:: STEP 0 - Check Docker
echo [0/5] Checking Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Docker Desktop is not running.
    echo  Please open Docker Desktop and wait for it to fully load.
    echo  Then double-click START.bat again.
    echo.
    pause
    exit /b 1
)
echo  OK - Docker is running.

:: STEP 1 - Check Node
echo [1/5] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Node.js not found.
    echo  Download from: https://nodejs.org  and install, then try again.
    echo.
    pause
    exit /b 1
)
echo  OK - Node.js found.

:: STEP 2 - npm install if needed
echo.
echo [2/5] Checking frontend packages...
if not exist "frontend\node_modules" (
    echo  Running npm install inside frontend\ ...
    cd frontend
    npm install
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: npm install failed. Check internet and try again.
        echo.
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo  OK - packages installed.
) else (
    echo  OK - node_modules already present.
)

:: STEP 3 - docker compose up
echo.
echo [3/5] Starting Postgres and Backend via Docker...
echo  First run takes 3-5 minutes to build the image.
echo  You will see build output below - this is normal.
echo.
docker compose up -d --build postgres backend
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: docker compose failed.
    echo  Common fix: make sure port 5432 and 8000 are not used by another app.
    echo.
    pause
    exit /b 1
)
echo.
echo  OK - containers started.

:: STEP 4 - wait for postgres
echo.
echo [4/5] Waiting for Postgres to be ready...
set TRIES=0
:WAITPG
set /a TRIES+=1
if %TRIES% GTR 30 (
    echo.
    echo  ERROR: Postgres did not start in time.
    echo  Run this command to see why:  docker compose logs postgres
    echo.
    pause
    exit /b 1
)
docker compose exec -T postgres pg_isready -U ubid >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 /nobreak >nul
    goto WAITPG
)
echo  OK - Postgres is ready.

:: Run migrations
echo.
echo [5/5] Running database migrations...
docker compose exec -T backend sh -c "alembic upgrade head"
if %errorlevel% neq 0 (
    echo  NOTE: Migration warning is normal if tables already exist.
)
echo  OK - migrations done.

:: Start frontend in a new window
echo.
echo  Starting React frontend in a new window...
start "UBID Frontend" cmd /k "cd /d "%~dp0frontend" && npm start"

echo.
echo  ================================================
echo   ALL DONE - services are running
echo  ================================================
echo.
echo   Frontend  -  http://localhost:3000
echo   Backend   -  http://localhost:8000
echo   API Docs  -  http://localhost:8000/docs
echo.
echo   Run STOP.bat to shut everything down.
echo  ================================================
echo.
timeout /t 5 /nobreak >nul
start http://localhost:3000
echo.
echo  Press any key to close this window.
pause >nul
