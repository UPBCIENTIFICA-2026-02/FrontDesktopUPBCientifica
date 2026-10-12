@echo off
rem ==========================================================================
rem  UPB-CIENTIFICA - Cliente de Escritorio
rem  Doble clic para abrir. La primera vez instala lo necesario.
rem ==========================================================================
setlocal
cd /d "%~dp0"
title UPB-CIENTIFICA

rem --- 1. Buscar Python -----------------------------------------------------
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo.
    echo  No se encontro Python en este equipo.
    echo  Instalalo desde https://www.python.org/downloads/
    echo  y marca la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

rem --- 2. Instalar dependencias solo si faltan ------------------------------
%PY% -c "import customtkinter, PIL, av, sounddevice" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias por primera vez, espera un momento...
    %PY% -m pip install --user -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  No se pudieron instalar las dependencias. Revisa tu conexion a internet.
        pause
        exit /b 1
    )
)

rem --- 3. Los servicios NO se arrancan aqui ----------------------------------
rem  La app usa los servicios reales (Auth 8081, Storage 8084, Shared File 8085,
rem  node-media 8083, job-api 8082). En el PC de desarrollo los arranca
rem  UPB-CIENTIFICA\despliegue\cluster-virtualbox\7-iniciar-servicios-windows.ps1.
rem  El mock antiguo (mock-auth-server, puerto 8080) ya no se lanza: ese puerto
rem  es ahora el de node-web.

rem --- 4. Abrir la aplicacion sin dejar la consola abierta ------------------
set "PYW=pythonw"
where pyw >nul 2>&1 && set "PYW=pyw -3"
start "" %PYW% main.py
exit /b 0
