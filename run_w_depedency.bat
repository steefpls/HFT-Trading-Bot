@echo off
setlocal

:: Check for each dependency in requirements.txt and install if missing
for /F %%i in (requirements.txt) do (
    pip show %%i >nul 2>&1
    if errorlevel 1 (
        echo Installing missing dependency: %%i
        pip install %%i
    )
    echo checking dependency...
)

:run_main_py
echo Starting main.py...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo main.py crashed with exit code %ERRORLEVEL%. Respawning..
    goto run_main_py
)

endlocal
