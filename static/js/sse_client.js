// sse_client.js - Server-Sent Events client for real-time updates
(function () {
  "use strict";

  /**
   * SSE client for real-time updates from the server.
   */
  class SSEClient {
    /**
     * Initialize a new SSE client
     */
    constructor() {
      this.eventSources = {};
      this.callbacks = {};
      this.reconnectTimeouts = {};
    }

    /**
     * Subscribe to an event stream for a specific task
     *
     * @param {string} taskId - Task ID to subscribe to
     * @param {string} eventType - Event type (e.g., 'export_progress')
     * @param {Function} callback - Callback function to handle events
     * @returns {boolean} - Success status
     */
    subscribe(taskId, eventType, callback) {
      if (!taskId || !callback || typeof callback !== "function") {
        console.error("Invalid parameters for SSE subscription");
        return false;
      }

      const sourceId = `${eventType}-${taskId}`;

      // Clean up any existing connection
      this.unsubscribe(taskId, eventType);

      try {
        // Create a new EventSource connection to the server
        const url = `/api/sse/${eventType}/${taskId}`;
        const eventSource = new EventSource(url);

        // Set up event handlers
        eventSource.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data);
            // Server may wrap payloads as { event, data, timestamp }
            const payload =
              parsed && typeof parsed === "object" && "data" in parsed
                ? parsed.data
                : parsed;
            callback(payload);
          } catch (error) {
            console.error("Error parsing SSE data:", error);
          }
        };

        eventSource.onerror = (error) => {
          console.error("SSE connection error:", error);
          this.unsubscribe(taskId, eventType);

          // Try to reconnect after a delay
          this.reconnectTimeouts[sourceId] = setTimeout(() => {
            console.log("Attempting to reconnect SSE...");
            this.subscribe(taskId, eventType, callback);
          }, 3000);
        };

        // Store the connection and callback
        this.eventSources[sourceId] = eventSource;
        this.callbacks[sourceId] = callback;

        return true;
      } catch (error) {
        console.error("Failed to create SSE connection:", error);
        return false;
      }
    }

    /**
     * Unsubscribe from an event stream
     *
     * @param {string} taskId - Task ID to unsubscribe from
     * @param {string} eventType - Event type (e.g., 'export_progress')
     * @returns {boolean} - Success status
     */
    unsubscribe(taskId, eventType) {
      const sourceId = `${eventType}-${taskId}`;

      // Clear any pending reconnect timeout
      if (this.reconnectTimeouts[sourceId]) {
        clearTimeout(this.reconnectTimeouts[sourceId]);
        delete this.reconnectTimeouts[sourceId];
      }

      // Close the EventSource connection if it exists
      if (this.eventSources[sourceId]) {
        try {
          this.eventSources[sourceId].close();
          delete this.eventSources[sourceId];
          delete this.callbacks[sourceId];
          return true;
        } catch (error) {
          console.error("Error closing SSE connection:", error);
        }
      }

      return false;
    }

    /**
     * Check if there is an active subscription for a task
     *
     * @param {string} taskId - Task ID to check
     * @param {string} eventType - Event type (e.g., 'export_progress')
     * @returns {boolean} - Whether there is an active subscription
     */
    isSubscribed(taskId, eventType) {
      const sourceId = `${eventType}-${taskId}`;
      return !!this.eventSources[sourceId];
    }
  }

  // Create a global SSE client instance
  window.sseClient = new SSEClient();
})();
