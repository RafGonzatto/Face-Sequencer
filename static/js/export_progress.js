// export_progress.js - Real-time export progress monitoring with SSE
(function () {
  "use strict";

  // Wait for DOM to be ready
  document.addEventListener("DOMContentLoaded", function () {
    // Check if we have access to the app
    const app = window.FaceSequencerApp;
    if (!app || !app.prototype) {
      console.error("Could not find FaceSequencerApp");
      return;
    }

    // Override the monitorExportProgress method
    const originalMonitorExportProgress = app.prototype.monitorExportProgress;

    app.prototype.monitorExportProgress = function () {
      // Create progress modal if it doesn't exist
      if (!this.exportProgressModal) {
        this.exportProgressModal = document.createElement("div");
        this.exportProgressModal.className = "modal progress-modal";
        this.exportProgressModal.innerHTML = `
          <div class="modal-content">
            <h2>Exporting Video</h2>
            <div class="progress-container">
              <div class="progress-bar">
                <div class="progress-fill"></div>
              </div>
              <div class="progress-text">0%</div>
            </div>
            <div class="progress-message">Starting export...</div>
            <div class="progress-actions">
              <button class="btn btn-secondary cancel-export-btn">Cancel</button>
            </div>
          </div>
        `;
        document.body.appendChild(this.exportProgressModal);

        // Add event listener for cancel button
        const cancelBtn =
          this.exportProgressModal.querySelector(".cancel-export-btn");
        if (cancelBtn) {
          cancelBtn.addEventListener("click", () => {
            // We can't actually cancel the export, but we can stop monitoring
            this.hideExportProgressModal();
            this.showStatus("Export continues in background");
          });
        }
      }

      // Show the modal
      this.exportProgressModal.style.display = "flex";

      // Check if SSE is available
      if (window.sseClient) {
        // Close any existing SSE connections for this task
        window.sseClient.unsubscribe(this.state.exportTask, "export_progress");

        // Subscribe to SSE updates for this task
        window.sseClient.subscribe(
          this.state.exportTask,
          "export_progress",
          (data) => this.handleExportProgressUpdate(data)
        );
      } else {
        console.warn("SSE client not available, falling back to polling");
        // Fall back to original polling implementation
        if (originalMonitorExportProgress) {
          originalMonitorExportProgress.call(this);
        }
      }
    };

    // Add a method to handle SSE progress updates
    app.prototype.handleExportProgressUpdate = function (data) {
      // Update progress bar and message
      const progressFill =
        this.exportProgressModal.querySelector(".progress-fill");
      const progressText =
        this.exportProgressModal.querySelector(".progress-text");
      const progressMessage =
        this.exportProgressModal.querySelector(".progress-message");

      if (progressFill && progressText) {
        const progress = data.progress || 0;
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;

        if (progressMessage && data.message) {
          progressMessage.textContent = data.message;
        }

        // Update visual state based on status
        if (data.status === "error") {
          progressFill.classList.add("error");
          progressMessage.classList.add("error");
        } else {
          progressFill.classList.remove("error");
          progressMessage.classList.remove("error");
        }
      }

      // Handle completed or error states
      if (data.status === "completed") {
        const progressMessage =
          this.exportProgressModal.querySelector(".progress-message");
        if (progressMessage) {
          progressMessage.textContent = "Export completed. Validating file...";
        }

        // Validate and download
        this.validateAndDownloadExport();
      } else if (data.status === "error") {
        // Show error message
        this.showError(`Export failed: ${data.error || "Unknown error"}`);

        // Change the cancel button to close
        const cancelBtn =
          this.exportProgressModal.querySelector(".cancel-export-btn");
        if (cancelBtn) {
          cancelBtn.textContent = "Close";
        }
      }
    };

    // Add method to validate and download export
    app.prototype.validateAndDownloadExport = function () {
      const progressMessage =
        this.exportProgressModal.querySelector(".progress-message");

      // First verify the export is valid
      this.apiCall(`/export/validate/${this.state.exportTask}`)
        .then((validateResponse) => {
          if (validateResponse.success && validateResponse.valid) {
            // Update message to show validation success
            if (progressMessage) {
              progressMessage.textContent =
                "Export validated successfully! Starting download...";
            }

            // Auto-download after short delay
            setTimeout(() => {
              this.hideExportProgressModal();
              this.downloadExport();
            }, 1000);
          } else {
            // Show validation error
            if (progressMessage) {
              progressMessage.textContent = `Export validation failed: ${
                validateResponse.error || "Unknown error"
              }`;
              progressMessage.style.color = "red";
            }

            // Change the cancel button to close
            const cancelBtn =
              this.exportProgressModal.querySelector(".cancel-export-btn");
            if (cancelBtn) {
              cancelBtn.textContent = "Close";
            }

            // Add a retry button if it doesn't exist
            this.addRetryButton();
          }
        })
        .catch((error) => {
          console.error("Export validation error:", error);
          // Continue with download anyway
          setTimeout(() => {
            this.hideExportProgressModal();
            this.downloadExport();
          }, 1000);
        });
    };

    // Add method to create retry button
    app.prototype.addRetryButton = function () {
      const actionsDiv =
        this.exportProgressModal.querySelector(".progress-actions");
      if (actionsDiv && !actionsDiv.querySelector(".retry-export-btn")) {
        const retryBtn = document.createElement("button");
        retryBtn.className = "btn btn-primary retry-export-btn";
        retryBtn.textContent = "Retry Export";
        retryBtn.addEventListener("click", () => {
          this.hideExportProgressModal();
          this.exportVideo();
        });
        actionsDiv.appendChild(retryBtn);
      }
    };

    // Override hideExportProgressModal to clean up SSE subscription
    const originalHideExportProgressModal =
      app.prototype.hideExportProgressModal;
    app.prototype.hideExportProgressModal = function () {
      if (window.sseClient && this.state.exportTask) {
        window.sseClient.unsubscribe(this.state.exportTask, "export_progress");
      }

      if (originalHideExportProgressModal) {
        originalHideExportProgressModal.call(this);
      } else if (this.exportProgressModal) {
        this.exportProgressModal.style.display = "none";
      }
    };

    console.log("Export progress streaming initialized");
  });
})();
