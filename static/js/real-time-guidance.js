// Real-time User Guidance System
class RealTimeGuidance {
  constructor(app) {
    this.app = app;
    this.guidancePanel = null;
    this.currentSuggestions = [];
    this.isActive = true;
    this.init();
  }

  init() {
    this.createGuidancePanel();
    this.bindEvents();
    this.startAnalyzing();

    // Make instance globally available for direct calls from HTML
    window.realTimeGuidance = this;
  }

  createGuidancePanel() {
    this.guidancePanel = document.createElement("div");
    this.guidancePanel.className = "guidance-panel";
    this.guidancePanel.innerHTML = `
      <div class="guidance-header">
        <div class="guidance-title">
          <i class="fas fa-lightbulb"></i>
          Smart Suggestions
        </div>
        <button class="guidance-toggle" title="Toggle suggestions">
          <i class="fas fa-chevron-up"></i>
        </button>
      </div>
      <div class="guidance-content">
        <div class="guidance-suggestions"></div>
        <div class="guidance-progress">
          <div class="progress-item" data-step="setup">
            <i class="fas fa-circle-check"></i>
            <span>Setup character images</span>
          </div>
          <div class="progress-item" data-step="content">
            <i class="fas fa-circle"></i>
            <span>Add text or audio content</span>
          </div>
          <div class="progress-item" data-step="generate">
            <i class="fas fa-circle"></i>
            <span>Generate animation</span>
          </div>
          <div class="progress-item" data-step="export">
            <i class="fas fa-circle"></i>
            <span>Export final video</span>
          </div>
        </div>
      </div>
    `;

    // Position panel with higher z-index to garantir clicabilidade
    this.guidancePanel.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 320px;
      max-height: 400px;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      z-index: 10000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      overflow: hidden;
      transition: all 0.3s ease;
      pointer-events: auto !important;
    `;

    // Criar um container especial para garantir que o painel fique acima de outros elementos
    let guidancePanelContainer = document.getElementById(
      "guidance-panel-container"
    );

    if (!guidancePanelContainer) {
      guidancePanelContainer = document.createElement("div");
      guidancePanelContainer.id = "guidance-panel-container";
      guidancePanelContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        pointer-events: none;
        z-index: 9999;
      `;
      document.body.appendChild(guidancePanelContainer);
    }

    // O container não recebe eventos de clique, mas o painel sim
    guidancePanelContainer.appendChild(this.guidancePanel);

    // Bind toggle
    this.guidancePanel
      .querySelector(".guidance-toggle")
      .addEventListener("click", () => {
        this.togglePanel();
      });
  }

  bindEvents() {
    // Monitor form changes
    document.addEventListener("input", (e) => this.onInputChange(e));
    document.addEventListener("change", (e) => this.onInputChange(e));

    // Monitor button clicks
    document.addEventListener("click", (e) => this.onButtonClick(e));

    // Adicionar manipuladores para todos os botões de navegação de arquivos
    this._addFileNavigationHandlers();

    // Monitor file operations
    if (this.app) {
      // Hook into app state changes
      const originalSetState = this.app.setState?.bind(this.app);
      if (originalSetState) {
        this.app.setState = (...args) => {
          const result = originalSetState(...args);
          this.analyzeCurrentState();
          return result;
        };
      }
    }
  }

  startAnalyzing() {
    // Initial analysis
    this.analyzeCurrentState();

    // Periodic analysis
    setInterval(() => {
      if (this.isActive) {
        this.analyzeCurrentState();
      }
    }, 2000);
  }

  // Handle input changes from form fields
  onInputChange(e) {
    // When input fields change, analyze the current state
    setTimeout(() => this.analyzeCurrentState(), 100);
  }

  analyzeCurrentState() {
    const suggestions = [];
    const progress = this.assessProgress();

    // Analyze based on current state
    if (!this.hasImages()) {
      suggestions.push({
        type: "setup",
        priority: "high",
        icon: "fas fa-images",
        title: "Add Character Images",
        message: "Start by adding mouth position images for your character.",
        action: () => this.focusElement("#folderPath"),
        actionText: "Browse Images",
      });
    } else if (!this.hasValidMappings()) {
      suggestions.push({
        type: "setup",
        priority: "high",
        icon: "fas fa-link",
        title: "Map Characters to Images",
        message:
          "Drag images onto letters or use auto-mapping to connect characters with mouth positions.",
        action: () => this.switchToTab("setup"),
        actionText: "Setup Mappings",
      });
    }

    if (this.hasValidMappings() && !this.hasContent()) {
      suggestions.push({
        type: "content",
        priority: "high",
        icon: "fas fa-font",
        title: "Add Text Content",
        message:
          "Enter the text you want to animate, or upload an audio file for automatic sync.",
        action: () => this.focusElement("#textInput"),
        actionText: "Add Text",
      });
    }

    if (this.hasContent() && this.hasValidMappings() && !this.hasSequence()) {
      suggestions.push({
        type: "generate",
        priority: "high",
        icon: "fas fa-play",
        title: "Generate Animation",
        message:
          "Everything is ready! Click to generate your lip-sync animation.",
        action: () => this.clickElement("#buildSequenceBtn"),
        actionText: "Generate Now",
      });
    }

    if (this.hasSequence() && !this.hasExported()) {
      suggestions.push({
        type: "export",
        priority: "medium",
        icon: "fas fa-download",
        title: "Export Video",
        message: "Your animation looks great! Export it as an MP4 video file.",
        action: () => this.clickElement("#exportVideo"),
        actionText: "Export Video",
      });
    }

    // Performance suggestions
    if (this.isLongSequence()) {
      suggestions.push({
        type: "performance",
        priority: "low",
        icon: "fas fa-tachometer-alt",
        title: "Optimize Performance",
        message:
          "For long sequences, consider reducing frame rate or using smaller images.",
        action: () => this.showPerformanceTips(),
        actionText: "Learn More",
      });
    }

    // Quality suggestions
    if (this.hasLowQualityImages()) {
      suggestions.push({
        type: "quality",
        priority: "medium",
        icon: "fas fa-exclamation-triangle",
        title: "Image Quality Notice",
        message:
          "Some images are low resolution. Consider using higher quality images for better results.",
        action: () => this.showQualityTips(),
        actionText: "Tips",
      });
    }

    this.updateSuggestions(suggestions);
    this.updateProgress(progress);
  }

  assessProgress() {
    const progress = {
      setup: this.hasImages() && this.hasValidMappings(),
      content: this.hasContent(),
      generate: this.hasSequence(),
      export: this.hasExported(),
    };

    return progress;
  }

  // State detection methods
  hasImages() {
    const folderPath = document.getElementById("folderPath")?.value;
    return folderPath && folderPath.trim().length > 0;
  }

  hasValidMappings() {
    const mappings = this.app?.state?.mappings || {};
    return Object.keys(mappings).length > 0;
  }

  hasContent() {
    const text = document.getElementById("textInput")?.value;
    const hasAudio = this.app?.state?.audioData;
    return (text && text.trim().length > 0) || hasAudio;
  }

  hasSequence() {
    return this.app?.state?.sequence?.length > 0;
  }

  hasExported() {
    // Check if export was recently performed
    return (
      localStorage.getItem("lastExportTime") &&
      Date.now() - parseInt(localStorage.getItem("lastExportTime")) < 300000
    ); // 5 minutes
  }

  isLongSequence() {
    return (this.app?.state?.sequence?.length || 0) > 300; // More than 10 seconds at 30fps
  }

  hasLowQualityImages() {
    // This would need to be implemented based on image analysis
    return false;
  }

  // UI update methods
  updateSuggestions(suggestions) {
    this.currentSuggestions = suggestions;
    const container = this.guidancePanel.querySelector(".guidance-suggestions");

    if (suggestions.length === 0) {
      container.innerHTML = `
        <div class="no-suggestions">
          <i class="fas fa-check-circle"></i>
          <p>You're all set! Everything looks good.</p>
        </div>
      `;
      return;
    }

    // Show top 2 most important suggestions
    const topSuggestions = suggestions
      .sort((a, b) => {
        const priorities = { high: 3, medium: 2, low: 1 };
        return priorities[b.priority] - priorities[a.priority];
      })
      .slice(0, 2);

    container.innerHTML = topSuggestions
      .map(
        (suggestion, index) => `
      <div class="suggestion-item priority-${suggestion.priority}" data-type="${
          suggestion.type
        }" data-index="${index}" data-action="${
          suggestion.action ? suggestion.type : "browse_folder"
        }" tabindex="0" role="button">
        <div class="suggestion-icon">
          <i class="${suggestion.icon}"></i>
        </div>
        <div class="suggestion-content">
          <div class="suggestion-title">${suggestion.title}</div>
          <div class="suggestion-message">${suggestion.message}</div>
          <button class="suggestion-action btn btn-sm btn-primary" data-type="${
            suggestion.type
          }" data-index="${index}" data-action="${
          suggestion.action ? suggestion.type : "browse_folder"
        }">
            ${suggestion.actionText}
          </button>
        </div>
      </div>
    `
      )
      .join("");

    // Add click event listeners to suggestions and buttons
    setTimeout(() => {
      // Add click handlers for all suggestion items
      const items = container.querySelectorAll(".suggestion-item");
      items.forEach((item, idx) => {
        const suggestionIndex = parseInt(item.dataset.index);
        const suggestion = topSuggestions[suggestionIndex];

        // Make the whole suggestion clickable
        item.addEventListener("click", (e) => {
          if (!e.target.closest(".suggestion-action")) {
            this.executeSuggestionByIndex(suggestionIndex);
          }
        });

        // Make it keyboard accessible
        item.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            this.executeSuggestionByIndex(suggestionIndex);
            e.preventDefault();
          }
        });

        // Handle button clicks
        const button = item.querySelector(".suggestion-action");
        if (button) {
          button.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("Button clicked:", suggestion.type);

            if (suggestion.type === "setup") {
              // Forçar o clique no botão browse folder
              const browseBtn = document.getElementById("browseFolderBtn");
              if (browseBtn) {
                console.log("Auto-clicking browse folder button");
                browseBtn.click();
              } else {
                console.warn("Browse folder button not found");
                // Tenta encontrar alternativas
                this._executeFallbackAction("setup");
              }
            } else {
              this.executeSuggestionByIndex(suggestionIndex);
            }
          });
        }
      });
    }, 0);
  }

  // Execute a suggestion by its index in the current suggestions array
  executeSuggestionByIndex(index) {
    const suggestion = this.currentSuggestions[index];
    if (suggestion && suggestion.action) {
      suggestion.action();
    } else {
      this.executeSuggestion(suggestion?.type || "setup");
    }
  }

  /**
   * Adiciona manipuladores de eventos para todos os botões de navegação de arquivos
   * que possam existir na aplicação
   */
  _addFileNavigationHandlers() {
    // Esta função é chamada quando a classe é inicializada
    console.log("[RealTimeGuidance] Setting up file navigation handlers");

    // Usar um MutationObserver para detectar quando novos botões são adicionados ao DOM
    const observer = new MutationObserver((mutations) => {
      this._detectAndBindFileBrowserButtons();
    });

    // Observar todo o documento para mudanças na estrutura do DOM
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    // Também fazer uma verificação inicial
    setTimeout(() => this._detectAndBindFileBrowserButtons(), 500);

    // E verificar novamente em intervalos regulares
    setInterval(() => this._detectAndBindFileBrowserButtons(), 2000);
  }

  /**
   * Detecta e vincula manipuladores de eventos a todos os botões de navegação de arquivos
   */
  _detectAndBindFileBrowserButtons() {
    // Seletores para possíveis botões de navegação de arquivos
    const selectors = [
      "#browseFolderBtn",
      "button.browse-btn",
      "button.browse-folder-btn",
      "button.file-select-btn",
      ".browse-container .btn",
      "button.btn-outline-primary:has(i.fa-folder)",
      "button:has(i.fa-folder-open)",
      "button:has(i.fa-file-upload)",
    ];

    // Combinar seletores
    const combinedSelector = selectors.join(", ");
    const buttons = document.querySelectorAll(combinedSelector);

    buttons.forEach((button) => {
      // Verificar se já adicionamos um handler
      if (!button.dataset.guidanceHandlerAdded) {
        console.log("[RealTimeGuidance] Found file browser button:", button);

        // Marcar como processado
        button.dataset.guidanceHandlerAdded = "true";

        // Adicionar evento de clique
        button.addEventListener("click", (e) => {
          console.log(
            "[RealTimeGuidance] File browser button clicked:",
            button
          );
        });

        // Tornar mais visível
        button.style.position = "relative";
        button.style.zIndex = "10001";
      }
    });
  }

  updateProgress(progress) {
    const progressItems = this.guidancePanel.querySelectorAll(".progress-item");

    progressItems.forEach((item) => {
      const step = item.dataset.step;
      const icon = item.querySelector("i");

      if (progress[step]) {
        icon.className = "fas fa-circle-check";
        item.classList.add("completed");
      } else {
        icon.className = "fas fa-circle";
        item.classList.remove("completed");
      }
    });
  }

  // Action methods
  executeSuggestion(type) {
    console.log("[RealTimeGuidance] Executing suggestion:", type);

    const suggestion = this.currentSuggestions.find((s) => s.type === type);
    if (suggestion && suggestion.action) {
      try {
        suggestion.action();
        console.log("[RealTimeGuidance] Suggestion action executed");
      } catch (e) {
        console.error(
          "[RealTimeGuidance] Error executing suggestion action:",
          e
        );
      }
    } else {
      // Fallback para ações comuns se a ação específica não for encontrada
      this._executeFallbackAction(type);
    }
  }

  _executeFallbackAction(type) {
    console.log("[RealTimeGuidance] Using fallback action for:", type);

    switch (type) {
      case "setup":
        // Tentar abrir o diálogo de seleção de pasta
        const browseBtn = document.getElementById("browseFolderBtn");
        if (browseBtn) {
          console.log("[RealTimeGuidance] Clicking browse folder button");
          browseBtn.click();
          return true;
        } else {
          // Tente encontrar por seletor CSS
          const altBtn = document
            .querySelector(
              'button[id="browseFolderBtn"], button.btn-outline-primary i.fa-folder, button.browse-btn, button.browse-folder-btn, button.file-select-btn, .browse-container .btn'
            )
            ?.closest("button");
          if (altBtn) {
            console.log(
              "[RealTimeGuidance] Clicking alternative browse button"
            );
            altBtn.click();
            return true;
          }
          // Tentar acionar o input de arquivo diretamente
          const folderInput = document.querySelector(
            "input[type=file]#folderInput"
          );
          if (folderInput) {
            console.log("[RealTimeGuidance] Clicking folder input directly");
            folderInput.click();
          }
        }
        break;

      case "content":
        const textInput = document.getElementById("textInput");
        if (textInput) {
          textInput.focus();
          textInput.scrollIntoView({ behavior: "smooth" });
        }
        break;

      default:
        console.log("[RealTimeGuidance] No fallback action for type:", type);
    }
  }

  focusElement(selector) {
    console.log("[RealTimeGuidance] Focusing element:", selector);
    const element = document.querySelector(selector);
    if (element) {
      element.focus();
      element.scrollIntoView({ behavior: "smooth", block: "center" });

      // Add temporary highlight
      element.classList.add("guidance-highlight");
      setTimeout(() => element.classList.remove("guidance-highlight"), 2000);

      // Se o elemento for folderPath, também acionar o browseFolderBtn
      if (selector === "#folderPath") {
        const browseBtn = document.getElementById("browseFolderBtn");
        if (browseBtn) {
          console.log("[RealTimeGuidance] Auto-clicking browse folder button");
          setTimeout(() => browseBtn.click(), 300);
        }
      }

      return true;
    } else {
      console.warn("[RealTimeGuidance] Element not found:", selector);
      return false;
    }
  }

  clickElement(selector) {
    const element = document.querySelector(selector);
    if (element) {
      element.click();
    }
  }

  switchToTab(tabName) {
    const tab = document.querySelector(`[data-tab="${tabName}"]`);
    if (tab) {
      tab.click();
    }
  }

  togglePanel() {
    const content = this.guidancePanel.querySelector(".guidance-content");
    const toggle = this.guidancePanel.querySelector(".guidance-toggle i");

    const isCollapsed = content.style.display === "none";

    content.style.display = isCollapsed ? "block" : "none";
    toggle.className = isCollapsed
      ? "fas fa-chevron-up"
      : "fas fa-chevron-down";

    this.isActive = isCollapsed;
  }

  /**
   * Exibe uma mensagem de orientação contextual.
   * Evita quebrar se chamada por outros módulos que esperam este método.
   * @param {string} key - Chave única da dica (para evitar spam repetido)
   * @param {{title?: string, message: string, type?: 'info'|'warning'|'tip'}} data
   */
  showGuidance(key, data) {
    try {
      if (!this.guidancePanel) return;
      if (!this._shownGuidanceKeys) this._shownGuidanceKeys = new Set();

      // Ignorar mensagens vazias
      if (!data || !data.message) return;

      // Evitar repetir a mesma dica em sequência curta
      if (this._shownGuidanceKeys.has(key)) return;
      this._shownGuidanceKeys.add(key);
      setTimeout(() => this._shownGuidanceKeys.delete(key), 15000); // expira após 15s

      // Container onde vamos inserir as mensagens
      let msgHost = this.guidancePanel.querySelector(".guidance-suggestions");
      if (!msgHost) return;

      // Criar elemento visual da dica
      const wrapper = document.createElement("div");
      wrapper.className = `guidance-inline-msg guidance-${data.type || "info"}`;
      wrapper.style.cssText = `
        border: 1px solid #e5e7eb;
        background: #f8fafc;
        padding: 8px 10px; border-radius: 6px; font-size: 12px; line-height: 1.4; margin-bottom: 8px;
        position: relative; animation: fadeIn 0.25s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.04);
      `;
      const titleHtml = data.title
        ? `<div style="font-weight:600; margin-bottom:4px;">${data.title}</div>`
        : "";
      const icon =
        data.type === "warning"
          ? "fa-triangle-exclamation"
          : data.type === "tip"
          ? "fa-lightbulb"
          : "fa-info-circle";
      wrapper.innerHTML = `
        <div style="display:flex; gap:8px; align-items:flex-start;">
          <i class="fas ${icon}" style="color:#2563eb; font-size:14px; margin-top:2px;"></i>
          <div style="flex:1;">
            ${titleHtml}
            <div>${data.message}</div>
          </div>
          <button aria-label="Fechar" style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:14px;padding:0 4px;line-height:1;">×</button>
        </div>`;

      const closeBtn = wrapper.querySelector("button");
      closeBtn.addEventListener("click", () => wrapper.remove());

      msgHost.prepend(wrapper);

      // Auto-remover após 12s
      setTimeout(() => {
        if (wrapper.isConnected) wrapper.remove();
      }, 12000);
    } catch (err) {
      console.warn("[RealTimeGuidance] showGuidance fallback log:", key, data);
    }
  }

  showPerformanceTips() {
    alert(`Performance Tips:
• Use smaller image files (under 500KB each)
• Reduce frame rate for longer sequences
• Consider shorter text segments for complex animations
• Use compressed image formats like WebP`);
  }

  showQualityTips() {
    alert(`Quality Tips:
• Use high-resolution images (at least 512x512px)
• Ensure consistent lighting across mouth positions
• Use clear, sharp images without blur
• Keep consistent character positioning`);
  }

  // Public methods
  hide() {
    this.guidancePanel.style.display = "none";
  }

  show() {
    this.guidancePanel.style.display = "block";
  }

  destroy() {
    if (this.guidancePanel) {
      this.guidancePanel.remove();
    }
  }

  onButtonClick(event) {
    const target = event.target;
    const button = target.closest("button");

    if (!button) return;

    // Provide guidance based on button type
    const buttonId = button.id || "";
    const buttonClasses = button.className || "";
    const buttonText = button.textContent?.toLowerCase() || "";

    console.log("[RealTimeGuidance] Button clicked:", {
      id: buttonId,
      text: buttonText,
      classes: buttonClasses,
      element: button,
    });

    // Detectar se é um botão de navegação de arquivos
    if (
      buttonId === "browseFolderBtn" ||
      buttonText.includes("browse") ||
      buttonText.includes("folder") ||
      buttonText.includes("select file") ||
      buttonText.includes("upload") ||
      buttonClasses.includes("browse-btn") ||
      buttonClasses.includes("file-select") ||
      button.querySelector("i.fa-folder, i.fa-folder-open, i.fa-file-upload")
    ) {
      console.log("[RealTimeGuidance] File browser button detected");

      // Verificar se o botão está funcionando corretamente
      setTimeout(() => {
        // Se nenhum diálogo de arquivo foi aberto, tentar encontrar inputs de arquivo e acioná-los
        const fileInputs = document.querySelectorAll('input[type="file"]');
        if (fileInputs.length > 0) {
          console.log("[RealTimeGuidance] Found file inputs:", fileInputs);
          // Tentar clicar no primeiro input de arquivo
          try {
            fileInputs[0].click();
            console.log("[RealTimeGuidance] Clicked file input");
          } catch (e) {
            console.error("[RealTimeGuidance] Error clicking file input:", e);
          }
        }
      }, 100);
    }

    // Upload button guidance
    if (buttonText.includes("upload") || buttonId.includes("upload")) {
      this.showGuidance("upload_guidance", {
        title: "Upload Video",
        message:
          "Select a video file to start creating your lip-sync animation.",
        type: "info",
      });
    }

    // Export button guidance
    else if (buttonText.includes("export") || buttonId.includes("export")) {
      this.showGuidance("export_guidance", {
        title: "Export Options",
        message: "Choose your export format and quality settings.",
        type: "info",
      });
    }

    // Play/pause button guidance
    else if (buttonText.includes("play") || buttonText.includes("pause")) {
      this.showGuidance("playback_guidance", {
        title: "Playback Controls",
        message: "Use playback controls to review your animation.",
        type: "tip",
      });
    }
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    if (window.faceSequencerApp) {
      window.realTimeGuidance = new RealTimeGuidance(window.faceSequencerApp);
    }
  }, 1000);
});
