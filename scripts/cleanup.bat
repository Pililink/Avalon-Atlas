@echo off
echo Cleaning up residual processes...

REM Kill processes using port 1420 (Vite dev server)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :1420 ^| findstr LISTENING') do (
    echo Killing process %%a on port 1420
    taskkill /PID %%a /F
)

REM Kill any remaining node/vite processes
taskkill /IM node.exe /F 2>nul
taskkill /IM avalon-atlas.exe /F 2>nul

echo Cleanup complete!
pause
