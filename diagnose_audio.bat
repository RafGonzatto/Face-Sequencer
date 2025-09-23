@echo off
echo =============================================
echo Diagnóstico de Áudio - Face Sequencer Pro
echo =============================================
echo.

REM Verifica se o Python está instalado
where py >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Python não encontrado!
    echo.
    echo Para resolver este problema:
    echo 1. Baixe e instale Python 3.8 ou superior de python.org
    echo 2. IMPORTANTE: Selecione a opção "Add Python to PATH" durante a instalação
    echo 3. Reinicie o computador após a instalação
    echo.
    echo Após instalar o Python, execute este diagnóstico novamente.
    pause
    exit /b 1
)

echo Python encontrado! Verificando versão:
py --version
echo.

echo Executando diagnóstico completo...
py diagnose_audio.py

echo.
echo =============================================
echo INSTRUÇÕES PARA RESOLVER PROBLEMAS:
echo =============================================
echo.
echo Se faltarem dependências, execute:
echo py -m pip install -r requirements.txt
echo py -m pip install -r requirements_audio.txt
echo.
echo Para instalar o sistema de alinhamento de áudio:
echo py -m pip install whisperx
echo.
echo Se houver problemas com o PyTorch, execute:
echo py fix_pytorch_whisperx.py
echo.

pause