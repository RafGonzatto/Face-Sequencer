@echo off
echo =======================================================
echo Instalação de Dependências para Face Sequencer Pro
echo =======================================================
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
    pause
    exit /b 1
)

echo Python encontrado! Verificando versão:
py --version
echo.

echo Instalando dependências básicas...
py -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao instalar dependências básicas!
    pause
    exit /b 1
)

echo.
echo Instalando dependências de áudio...
py -m pip install -r requirements_audio.txt
if %ERRORLEVEL% NEQ 0 (
    echo AVISO: Algumas dependências de áudio podem não ter sido instaladas.
    echo O upload de áudio pode não funcionar corretamente.
)

echo.
echo Aplicando patch de compatibilidade do PyTorch...
py fix_pytorch_whisperx.py
if %ERRORLEVEL% NEQ 0 (
    echo AVISO: Não foi possível aplicar o patch do PyTorch.
    echo O alinhamento de áudio pode não funcionar corretamente.
)

echo.
echo =======================================================
echo Instalação concluída!
echo =======================================================
echo.
echo Para iniciar a aplicação, execute:
echo start.bat
echo.

pause