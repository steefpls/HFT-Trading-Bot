@echo off

setlocal

:run_main_py
echo Starting main.py...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo main.py crashed with exit code %ERRORLEVEL%. Respawning..
    goto run_main_py
)
echo main.py has been stopped due to either a crash, error, or an unknown manual reason. Restarting in 1 second(s)...
timeout /t 1
echo Restarting now...
goto run_main_py
endlocal

