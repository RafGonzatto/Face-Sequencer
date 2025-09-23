// export_validation.js - MP4 export validation utilities
(function () {
  // Utility to verify if a file is a valid MP4
  function isValidMP4(blob) {
    return new Promise((resolve) => {
      // Basic size check
      if (!blob || blob.size < 1024) {
        console.error("MP4 file is too small to be valid");
        resolve(false);
        return;
      }

      try {
        // For a more thorough check, we'd need to analyze the file format
        // but for basic validation, we'll check the first few bytes
        const reader = new FileReader();
        reader.onload = function (e) {
          const arr = new Uint8Array(e.target.result);

          // Check for MP4 signature (ftyp...)
          // MP4 files start with a 4-byte size followed by 'ftyp' or sometimes 'mdat'
          if (arr.length >= 8) {
            const signature = String.fromCharCode(
              arr[4],
              arr[5],
              arr[6],
              arr[7]
            );
            const isValid = signature === "ftyp" || signature === "mdat";

            if (!isValid) {
              console.error("MP4 signature check failed:", signature);
            }

            resolve(isValid);
          } else {
            console.error("MP4 file too short to verify signature");
            resolve(false);
          }
        };

        reader.onerror = function () {
          console.error("Error reading MP4 file");
          resolve(false);
        };

        // Read just the first 12 bytes for signature check
        reader.readAsArrayBuffer(blob.slice(0, 12));
      } catch (error) {
        console.error("MP4 validation error:", error);
        resolve(false);
      }
    });
  }

  // Function to check if an export task exists and is completed
  async function verifyExportTask(taskId) {
    try {
      const response = await fetch(`/api/export/status/${taskId}`);

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.task) {
          return {
            valid: true,
            status: data.task.status,
            message: data.task.message,
            error: data.task.error,
          };
        }
      }

      return {
        valid: false,
        status: "unknown",
        message: "Task not found or invalid response",
      };
    } catch (error) {
      console.error("Error verifying export task:", error);
      return {
        valid: false,
        status: "error",
        message: `Error checking task: ${error.message}`,
      };
    }
  }

  // Add these functions to the global FaceSequencerApp
  if (window.FaceSequencerApp) {
    window.FaceSequencerApp.prototype.isValidMP4 = isValidMP4;
    window.FaceSequencerApp.prototype.verifyExportTask = verifyExportTask;

    // Add a retry export method
    window.FaceSequencerApp.prototype.retryFailedExport = async function () {
      // First check if there's a failed task
      if (!this.state.exportTask) {
        this.showError("No export task to retry");
        return;
      }

      const taskStatus = await this.verifyExportTask(this.state.exportTask);

      if (!taskStatus.valid || taskStatus.status !== "error") {
        this.showError(
          "No failed export to retry or task is still in progress"
        );
        return;
      }

      // Re-export with the same parameters
      this.showStatus("Retrying failed export...");
      await this.exportVideo();
    };
  }
})();
