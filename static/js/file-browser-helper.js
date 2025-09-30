/**
 * File Browser Helper
 *
 * Este script adiciona suporte melhorado para ações de navegação de arquivos,
 * especialmente para botões de Smart Suggestions que precisam abrir diálogos de seleção de arquivos.
 */

class FileBrowserHelper {
  constructor() {
    this.init();
  }

  init() {
    console.log("[FileBrowserHelper] Initializing...");
    this.setupEventListeners();

    // Observar mudanças no DOM para capturar novos botões
    this.setupMutationObserver();

    // Também executar periodicamente
    setInterval(() => this.enhanceBrowseButtons(), 2000);

    // Executar imediatamente
    setTimeout(() => this.enhanceBrowseButtons(), 500);

    // Tornar global
    window.fileBrowserHelper = this;
  }

  setupEventListeners() {
    // Capturar todos os cliques no documento
    document.addEventListener("click", (e) => {
      // Verificar se o clique foi em um botão de sugestão ou com atributo data-action
      const target = e.target;
      const actionButton = target.closest(
        '[data-action="browse_folder"], [data-action="setup"], button.suggestion-action'
      );

      if (actionButton) {
        console.log(
          "[FileBrowserHelper] Detected click on action button:",
          actionButton
        );

        // Verificar o tipo de ação
        const actionType =
          actionButton.getAttribute("data-action") ||
          actionButton.getAttribute("data-type") ||
          "browse_folder";

        if (actionType === "browse_folder" || actionType === "setup") {
          console.log("[FileBrowserHelper] Triggering browse folder action");
          this.triggerBrowseFolder();
          // Evitar que o evento se propague se já estamos lidando com ele
          e.stopPropagation();
        }
      }
    });
  }

  setupMutationObserver() {
    // Observar mudanças no DOM para capturar novos botões
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.addedNodes.length) {
          // Verificar se novos botões foram adicionados
          setTimeout(() => this.enhanceBrowseButtons(), 100);
        }
      });
    });

    // Iniciar observação
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  enhanceBrowseButtons() {
    const browseSelectors = [
      "#browseFolderBtn",
      "button.browse-btn",
      "button.browse-folder-btn",
      "button.file-select-btn",
      ".browse-container .btn",
      "button:has(i.fa-folder)",
      "button:has(i.fa-folder-open)",
      "button:has(i.fa-file-upload)",
    ];

    const browseButtons = document.querySelectorAll(browseSelectors.join(", "));

    browseButtons.forEach((button) => {
      // Marcar para evitar duplicação
      if (!button.dataset.fileBrowserHelperEnhanced) {
        button.dataset.fileBrowserHelperEnhanced = "true";

        // Aumentar a visibilidade do botão
        button.style.position = "relative";
        button.style.zIndex = "10001";

        // Adicionar evento de clique diretamente
        button.addEventListener("click", (e) => {
          console.log("[FileBrowserHelper] Browse button clicked directly");
        });

        console.log("[FileBrowserHelper] Enhanced browse button:", button);
      }
    });
  }

  triggerBrowseFolder() {
    console.log("[FileBrowserHelper] Trying to trigger browse folder");

    // Primeira tentativa: botão com ID específico
    const browseBtn = document.getElementById("browseFolderBtn");
    if (browseBtn) {
      console.log("[FileBrowserHelper] Found browseFolderBtn, clicking it");
      browseBtn.click();
      return true;
    }

    // Segunda tentativa: botões com classes específicas
    const alternativeSelectors = [
      "button.browse-btn",
      "button.browse-folder-btn",
      "button.file-select-btn",
      ".browse-container .btn",
      "button:has(i.fa-folder)",
      "button:has(i.fa-folder-open)",
      "button:has(i.fa-file-upload)",
    ];

    for (const selector of alternativeSelectors) {
      try {
        const buttons = document.querySelectorAll(selector);
        if (buttons.length > 0) {
          console.log(
            `[FileBrowserHelper] Found button with selector "${selector}", clicking it`
          );
          buttons[0].click();
          return true;
        }
      } catch (e) {
        console.error(
          `[FileBrowserHelper] Error with selector "${selector}":`,
          e
        );
      }
    }

    // Terceira tentativa: procurar inputs de arquivo diretamente
    const fileInputs = document.querySelectorAll('input[type="file"]');
    if (fileInputs.length > 0) {
      console.log("[FileBrowserHelper] Found file input, clicking it");
      try {
        fileInputs[0].click();
        return true;
      } catch (e) {
        console.error("[FileBrowserHelper] Error clicking file input:", e);
      }
    }

    // Quarta tentativa: criar um input de arquivo temporário
    if (this._createAndClickTemporaryFileInput()) {
      return true;
    }

    // Quarta tentativa: procurar botões genéricos que possam servir
    const genericButtons = document.querySelectorAll("button, .btn");
    for (const btn of genericButtons) {
      const text = btn.textContent.toLowerCase();
      if (
        text.includes("browse") ||
        text.includes("upload") ||
        text.includes("select file") ||
        text.includes("folder")
      ) {
        console.log(
          "[FileBrowserHelper] Found generic button with relevant text, clicking it"
        );
        btn.click();
        return true;
      }
    }

    console.warn(
      "[FileBrowserHelper] Could not find any browse button or file input"
    );
    return false;
  }

  /**
   * Cria e clica em um input de arquivo temporário
   * Esta é uma solução de último recurso quando nenhum outro método funciona
   */
  _createAndClickTemporaryFileInput() {
    console.log("[FileBrowserHelper] Creating temporary file input");

    try {
      // Criar um input de arquivo temporário
      const tempInput = document.createElement("input");
      tempInput.type = "file";
      // Permitir vídeos comuns incluindo .mov; se não for necessário para outros fluxos não causa problema
      tempInput.accept = ".mp4,.mov,.mkv,.webm,.avi,.m4v,video/*";
      tempInput.style.position = "fixed";
      tempInput.style.top = "0";
      tempInput.style.left = "0";
      tempInput.style.opacity = "0.01";
      tempInput.style.zIndex = "10000";

      // Adicionar suporte para diretórios, se o navegador suportar
      tempInput.webkitdirectory = true;
      tempInput.directory = true;
      tempInput.multiple = true;

      // Adicionar ao DOM
      document.body.appendChild(tempInput);

      // Adicionar evento para remover após uso
      tempInput.addEventListener("change", () => {
        console.log("[FileBrowserHelper] Temporary file input used");

        // Processar os arquivos selecionados
        if (tempInput.files && tempInput.files.length > 0) {
          console.log(
            `[FileBrowserHelper] Selected ${tempInput.files.length} files/folders`
          );

          // Aqui você pode processar os arquivos ou disparar um evento personalizado
          // com os arquivos selecionados
          const event = new CustomEvent("folderSelected", {
            detail: {
              files: tempInput.files,
            },
          });
          document.dispatchEvent(event);
        }

        // Remover o input depois de usado
        setTimeout(() => {
          document.body.removeChild(tempInput);
        }, 1000);
      });

      // Clicar no input
      tempInput.click();
      return true;
    } catch (e) {
      console.error(
        "[FileBrowserHelper] Error creating temporary file input:",
        e
      );
      return false;
    }
  }
}

// Inicializar quando o documento estiver pronto
document.addEventListener("DOMContentLoaded", () => {
  window.fileBrowserHelper = new FileBrowserHelper();
});

// Tentar inicializar imediatamente se o DOM já estiver carregado
if (
  document.readyState === "complete" ||
  document.readyState === "interactive"
) {
  setTimeout(() => {
    if (!window.fileBrowserHelper) {
      window.fileBrowserHelper = new FileBrowserHelper();
    }
  }, 1);
}
