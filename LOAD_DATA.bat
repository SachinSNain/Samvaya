@echo off
title UBID Platform - Load Demo Data
color 0B

cd /d "%~dp0"

echo.
echo  ================================================
echo   UBID SAMVAYA  --  LOAD DEMO DATA
echo  ================================================
echo  Run this ONCE after START.bat to populate the
echo  database with synthetic business entities.
echo.
echo  This takes about 5-15 minutes.
echo  Do NOT run it again unless you want to reset.
echo  ================================================
echo.

:: Make sure backend container is running
docker compose ps backend | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Backend container is not running.
    echo  Run START.bat first, then come back here.
    echo.
    pause
    exit /b 1
)

echo  [1/5] Initialising database tables...
docker compose exec -e PYTHONPATH=/app -T backend python scripts/init_db.py
if errorlevel 1 (
    echo.
    echo  ERROR: Database init failed.
    echo  Check: docker compose logs backend
    pause
    exit /b 1
)
echo  [OK] Tables ready.

echo.
echo  [2/5] Generating synthetic data (5,000 entities)...
docker compose exec -e PYTHONPATH=/app -T backend python scripts/generate_synthetic_data.py
if errorlevel 1 (
    echo.
    echo  ERROR: Data generation failed.
    echo  Check: docker compose logs backend
    pause
    exit /b 1
)
echo  [OK] CSV files generated.

echo.
echo  [3/5] Loading CSV files into the database...
docker compose exec -e PYTHONPATH=/app -T backend python scripts/load_dept_records.py
if errorlevel 1 (
    echo.
    echo  ERROR: Database load failed.
    echo  Check: docker compose logs backend
    pause
    exit /b 1
)
echo  [OK] Records loaded into database.

echo.
echo  [4/5] Training LightGBM model on ground-truth pairs...
docker compose exec -e PYTHONPATH=/app -T backend python scripts/train_model.py
if errorlevel 1 (
    echo.
    echo  ERROR: Model training failed.
    echo  Check: docker compose logs backend
    pause
    exit /b 1
)
echo  [OK] Model trained.

echo.
echo  [5/5] Running entity resolution + activity pipeline...
echo  This may take several minutes...
docker compose exec -e PYTHONPATH=/app -e FORCE_LOCAL_ONLY=false -T backend python scripts/run_pipeline.py
if errorlevel 1 (
    echo.
    echo  ERROR: Pipeline failed.
    echo  Check: docker compose logs backend
    pause
    exit /b 1
)
echo  [OK] Pipeline complete.

echo.
echo  ================================================
echo   ALL DONE  --  App is ready at localhost:3000
echo  ================================================
echo.
pause
