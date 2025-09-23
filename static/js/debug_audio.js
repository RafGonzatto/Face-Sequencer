// debug_audio.js - Script para depuração da funcionalidade de áudio

// Esta função é executada quando o botão "Verificar AudioManager" é clicado
function checkAudioManager() {
  const results = document.getElementById("debug-results");

  results.innerHTML = "<h3>Verificando o estado do AudioManager...</h3>";

  if (!window.faceSequencerApp) {
    results.innerHTML +=
      '<p class="error">❌ window.faceSequencerApp não está definido!</p>';
    return;
  }

  results.innerHTML +=
    '<p class="success">✅ window.faceSequencerApp encontrado</p>';

  if (!window.faceSequencerApp.audioManager) {
    results.innerHTML +=
      '<p class="error">❌ audioManager não está inicializado!</p>';
    return;
  }

  results.innerHTML +=
    '<p class="success">✅ audioManager está inicializado</p>';

  // Verificar elementos do DOM
  const manager = window.faceSequencerApp.audioManager;
  results.innerHTML += "<h3>Elementos do DOM:</h3>";

  checkElement(results, "audioFileInput", manager.audioFileInput);
  checkElement(results, "selectedAudioFile", manager.selectedAudioFile);
  checkElement(results, "uploadAudioBtn", manager.uploadAudioBtn);
  checkElement(results, "timingModeToggle", manager.timingModeToggle);
  checkElement(
    results,
    "audioVisualizationContainer",
    manager.audioVisualizationContainer
  );
  checkElement(results, "waveformContainer", manager.waveformContainer);

  // Verificar estado do wavesurfer
  results.innerHTML += "<h3>WaveSurfer:</h3>";
  if (manager.wavesurfer) {
    results.innerHTML +=
      '<p class="success">✅ WaveSurfer está inicializado</p>';
  } else {
    results.innerHTML +=
      '<p class="error">❌ WaveSurfer não está inicializado!</p>';
  }

  // Verificar event listeners
  results.innerHTML += "<h3>Testando eventos:</h3>";

  if (manager.uploadAudioBtn) {
    results.innerHTML +=
      '<p>Clique no botão "Teste Upload" abaixo para verificar se o evento click está funcionando no botão de upload</p>';
    results.innerHTML += '<button id="test-upload-btn">Teste Upload</button>';

    document
      .getElementById("test-upload-btn")
      .addEventListener("click", function () {
        // Criar uma instância temporária do método original
        const originalUpload = manager.uploadAudio;

        // Substituir o método por uma versão de teste
        manager.uploadAudio = function () {
          results.innerHTML +=
            '<p class="success">✅ O método uploadAudio foi chamado corretamente!</p>';

          // Restaurar o método original
          manager.uploadAudio = originalUpload;
        };

        // Tentar disparar o evento click
        manager.uploadAudioBtn.click();
      });
  }
}

// Função auxiliar para verificar elementos do DOM
function checkElement(results, name, element) {
  if (element) {
    results.innerHTML += `<p class="success">✅ ${name} encontrado</p>`;
  } else {
    results.innerHTML += `<p class="error">❌ ${name} não encontrado!</p>`;
  }
}

// Adicionar estilos para o depurador
function addDebugStyles() {
  const style = document.createElement("style");
  style.textContent = `
        #audio-debugger {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: rgba(255, 255, 255, 0.95);
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 15px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            z-index: 9999;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }
        
        #audio-debugger h2 {
            margin-top: 0;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        
        #debug-results {
            margin-top: 15px;
        }
        
        .success {
            color: green;
            font-weight: bold;
        }
        
        .error {
            color: red;
            font-weight: bold;
        }
        
        #check-audio-btn {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
        }
        
        #check-audio-btn:hover {
            background-color: #45a049;
        }
    `;
  document.head.appendChild(style);
}

// Criar e adicionar o depurador à página
function createDebugger() {
  addDebugStyles();

  const debuggerDiv = document.createElement("div");
  debuggerDiv.id = "audio-debugger";
  debuggerDiv.innerHTML = `
        <h2>Depurador de Áudio</h2>
        <button id="check-audio-btn">Verificar AudioManager</button>
        <div id="debug-results"></div>
    `;

  document.body.appendChild(debuggerDiv);

  document
    .getElementById("check-audio-btn")
    .addEventListener("click", checkAudioManager);
}

// Iniciar o depurador quando a página estiver carregada
document.addEventListener("DOMContentLoaded", function () {
  // Esperamos um pouco para garantir que tudo foi carregado
  setTimeout(createDebugger, 1000);
});
