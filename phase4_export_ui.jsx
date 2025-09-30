/**
 * Phase 4 Export UI Components - Enhanced Social Media Export Interface
 * React components for advanced video export with subtitle burn-in and platform optimization.
 */

import React, { useState, useEffect, useCallback } from "react";

// =============================================================================
// Social Media Presets Selector Component
// =============================================================================

const SocialMediaPresetsSelector = ({
  onPresetSelect,
  selectedPreset,
  duration = null,
  contentType = "general",
}) => {
  const [presets, setPresets] = useState({});
  const [recommendations, setRecommendations] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch available presets on component mount
  useEffect(() => {
    fetchPresets();
    if (duration && contentType) {
      fetchRecommendations();
    }
  }, [duration, contentType]);

  const fetchPresets = async () => {
    try {
      const response = await fetch("/api/v4/export/presets");
      const data = await response.json();

      if (data.success) {
        setPresets(data.data.presets);
      } else {
        setError("Failed to load presets");
      }
    } catch (err) {
      setError("Network error loading presets");
    } finally {
      setLoading(false);
    }
  };

  const fetchRecommendations = async () => {
    try {
      const response = await fetch("/api/v4/export/presets/recommendations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content_type: contentType,
          duration: duration,
          target_audience: "general",
        }),
      });

      const data = await response.json();
      if (data.success) {
        setRecommendations(data.data.recommendations);
      }
    } catch (err) {
      console.error("Failed to fetch recommendations:", err);
    }
  };

  const handlePresetSelect = (presetName) => {
    onPresetSelect(presetName, presets[presetName]);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="ml-2">Loading presets...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">{error}</p>
        <button
          onClick={fetchPresets}
          className="mt-2 text-sm bg-red-100 hover:bg-red-200 px-3 py-1 rounded"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Recommendations Section */}
      {Object.keys(recommendations).length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-semibold text-blue-800 mb-2">
            🎯 Recommended for your content
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {Object.entries(recommendations).map(([presetName, preset]) => (
              <button
                key={presetName}
                onClick={() => handlePresetSelect(presetName)}
                className={`text-left p-3 rounded border-2 transition-all ${
                  selectedPreset === presetName
                    ? "border-blue-500 bg-blue-100"
                    : "border-blue-300 hover:border-blue-400 bg-white"
                }`}
              >
                <div className="font-medium text-sm">{preset.name}</div>
                <div className="text-xs text-gray-600">
                  {preset.width}×{preset.height} • {preset.fps}fps
                </div>
                <div className="text-xs text-blue-600 mt-1">Recommended</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* All Presets Grid */}
      <div>
        <h4 className="font-semibold mb-3">All Social Media Presets</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(presets).map(([presetName, preset]) => {
            const isRecommended = presetName in recommendations;
            const isSelected = selectedPreset === presetName;

            return (
              <button
                key={presetName}
                onClick={() => handlePresetSelect(presetName)}
                className={`text-left p-4 rounded-lg border-2 transition-all ${
                  isSelected
                    ? "border-blue-500 bg-blue-50"
                    : isRecommended
                    ? "border-blue-300 bg-blue-25 hover:border-blue-400"
                    : "border-gray-300 bg-white hover:border-gray-400"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h5 className="font-medium">{preset.name}</h5>
                  {isRecommended && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      Recommended
                    </span>
                  )}
                </div>

                <div className="space-y-1 text-sm text-gray-600">
                  <div>
                    📱 {preset.width} × {preset.height}
                  </div>
                  <div>🎬 {preset.fps} fps</div>
                  <div>⏱️ Max {preset.max_duration}s</div>
                  <div>📝 {preset.max_chars_per_line} chars/line</div>
                </div>

                {preset.description && (
                  <p className="text-xs text-gray-500 mt-2">
                    {preset.description}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// Export Progress Tracking Component
// =============================================================================

const ExportProgressTracker = ({ jobId, onComplete, onError }) => {
  const [jobStatus, setJobStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchJobStatus = useCallback(async () => {
    try {
      const response = await fetch(`/api/v4/export/job-status/${jobId}`);
      const data = await response.json();

      if (data.success) {
        const status = data.data.job_status;
        setJobStatus(status);

        if (status.status === "completed") {
          onComplete && onComplete(status);
        } else if (status.status === "failed") {
          onError && onError(status.error);
        }
      }
    } catch (err) {
      onError && onError("Failed to fetch job status");
    } finally {
      setLoading(false);
    }
  }, [jobId, onComplete, onError]);

  useEffect(() => {
    if (!jobId) return;

    fetchJobStatus();

    // Poll for status updates
    const interval = setInterval(fetchJobStatus, 2000);

    return () => clearInterval(interval);
  }, [jobId, fetchJobStatus]);

  if (loading) {
    return (
      <div className="flex items-center p-4">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        <span className="ml-2">Initializing export...</span>
      </div>
    );
  }

  if (!jobStatus) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">Unable to track export progress</p>
      </div>
    );
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case "queued":
        return "⏳";
      case "processing":
        return "⚙️";
      case "completed":
        return "✅";
      case "failed":
        return "❌";
      default:
        return "❓";
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "queued":
        return "text-yellow-600 bg-yellow-50 border-yellow-200";
      case "processing":
        return "text-blue-600 bg-blue-50 border-blue-200";
      case "completed":
        return "text-green-600 bg-green-50 border-green-200";
      case "failed":
        return "text-red-600 bg-red-50 border-red-200";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  return (
    <div
      className={`border rounded-lg p-4 ${getStatusColor(jobStatus.status)}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          <span className="text-2xl mr-2">
            {getStatusIcon(jobStatus.status)}
          </span>
          <div>
            <h4 className="font-medium">Export Progress</h4>
            <p className="text-sm opacity-75">Job ID: {jobId}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="font-medium capitalize">{jobStatus.status}</div>
          {jobStatus.progress !== undefined && (
            <div className="text-sm">
              {Math.round(jobStatus.progress * 100)}%
            </div>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {jobStatus.progress !== undefined &&
        jobStatus.status === "processing" && (
          <div className="mb-3">
            <div className="bg-white bg-opacity-50 rounded-full h-2">
              <div
                className="bg-current h-2 rounded-full transition-all duration-300"
                style={{ width: `${jobStatus.progress * 100}%` }}
              ></div>
            </div>
          </div>
        )}

      {/* Status Details */}
      <div className="space-y-2 text-sm">
        {jobStatus.current_step && (
          <div>Current step: {jobStatus.current_step}</div>
        )}

        {jobStatus.estimated_time_remaining && (
          <div>
            Estimated time remaining:{" "}
            {Math.round(jobStatus.estimated_time_remaining)}s
          </div>
        )}

        {jobStatus.processing_time && (
          <div>Processing time: {jobStatus.processing_time.toFixed(1)}s</div>
        )}

        {jobStatus.output_file_size && (
          <div>
            Output file size:{" "}
            {(jobStatus.output_file_size / 1024 / 1024).toFixed(1)} MB
          </div>
        )}

        {jobStatus.error && (
          <div className="text-red-600 font-medium">
            Error: {jobStatus.error}
          </div>
        )}
      </div>

      {/* Download Button */}
      {jobStatus.status === "completed" && (
        <div className="mt-4">
          <button
            onClick={() =>
              window.open(`/api/v4/export/download/${jobId}`, "_blank")
            }
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            📥 Download Video
          </button>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Main Export Interface Component
// =============================================================================

const Phase4ExportInterface = ({
  videoPath,
  subtitleSegments,
  duration,
  onExportStart,
  onExportComplete,
}) => {
  const [selectedPreset, setSelectedPreset] = useState("instagram_reel");
  const [presetDetails, setPresetDetails] = useState(null);
  const [customSettings, setCustomSettings] = useState({});
  const [outputFilename, setOutputFilename] = useState("");
  const [isExporting, setIsExporting] = useState(false);
  const [currentJobId, setCurrentJobId] = useState(null);
  const [validationResults, setValidationResults] = useState(null);

  useEffect(() => {
    if (duration) {
      validateDuration();
    }
  }, [selectedPreset, duration]);

  const validateDuration = async () => {
    try {
      const response = await fetch("/api/v4/export/validate-duration", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          duration: duration,
          platforms: [selectedPreset],
        }),
      });

      const data = await response.json();
      if (data.success) {
        setValidationResults(data.data);
      }
    } catch (err) {
      console.error("Duration validation failed:", err);
    }
  };

  const handlePresetSelect = (presetName, preset) => {
    setSelectedPreset(presetName);
    setPresetDetails(preset);

    // Auto-generate filename based on preset
    if (preset) {
      const timestamp = new Date()
        .toISOString()
        .slice(0, 19)
        .replace(/:/g, "-");
      setOutputFilename(
        `${preset.name.toLowerCase().replace(/\s+/g, "_")}_${timestamp}`
      );
    }
  };

  const startExport = async () => {
    if (!videoPath || !subtitleSegments || !outputFilename) {
      alert("Please ensure video, subtitles, and filename are provided");
      return;
    }

    setIsExporting(true);
    onExportStart && onExportStart();

    try {
      const response = await fetch("/api/v4/export/video-with-subtitles", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          input_video_path: videoPath,
          subtitle_segments: subtitleSegments,
          output_filename: outputFilename,
          preset_name: selectedPreset,
          custom_settings: customSettings,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setCurrentJobId(data.data.job_id);
      } else {
        throw new Error(data.message || "Export failed");
      }
    } catch (err) {
      alert(`Export failed: ${err.message}`);
      setIsExporting(false);
    }
  };

  const handleExportComplete = (jobStatus) => {
    setIsExporting(false);
    setCurrentJobId(null);
    onExportComplete && onExportComplete(jobStatus);
  };

  const handleExportError = (error) => {
    setIsExporting(false);
    setCurrentJobId(null);
    alert(`Export failed: ${error}`);
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold mb-4">🎬 Phase 4 Enhanced Export</h2>
        <p className="text-gray-600 mb-6">
          Export your video with optimized subtitles for social media platforms
        </p>

        {/* Duration Validation */}
        {validationResults && (
          <div className="mb-6">
            {validationResults.overall_valid ? (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-700">
                  ✅ Video duration ({duration}s) is compatible with selected
                  platform
                </p>
              </div>
            ) : (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-yellow-700">
                  ⚠️ Video duration ({duration}s) exceeds platform limit
                </p>
                {validationResults.recommendations.map((rec, index) => (
                  <p key={index} className="text-sm mt-1">
                    💡 {rec}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Preset Selection */}
        <div className="mb-6">
          <SocialMediaPresetsSelector
            onPresetSelect={handlePresetSelect}
            selectedPreset={selectedPreset}
            duration={duration}
            contentType="general"
          />
        </div>

        {/* Export Configuration */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Output Filename
            </label>
            <input
              type="text"
              value={outputFilename}
              onChange={(e) => setOutputFilename(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="my_social_video"
            />
            <p className="text-xs text-gray-500 mt-1">
              File extension (.mp4) will be added automatically
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Video Info
            </label>
            <div className="bg-gray-50 p-3 rounded-lg text-sm">
              <div>📁 {videoPath?.split("/").pop() || "No video selected"}</div>
              <div>📝 {subtitleSegments?.length || 0} subtitle segments</div>
              {duration && <div>⏱️ {duration}s duration</div>}
            </div>
          </div>
        </div>

        {/* Selected Preset Details */}
        {presetDetails && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h4 className="font-semibold text-blue-800 mb-2">
              Selected: {presetDetails.name}
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                📱 {presetDetails.width}×{presetDetails.height}
              </div>
              <div>🎬 {presetDetails.fps} fps</div>
              <div>⏱️ Max {presetDetails.max_duration}s</div>
              <div>📝 {presetDetails.max_chars_per_line} chars/line</div>
            </div>
          </div>
        )}

        {/* Export Actions */}
        {!isExporting ? (
          <div className="flex gap-3">
            <button
              onClick={startExport}
              disabled={!videoPath || !subtitleSegments || !outputFilename}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors"
            >
              🚀 Start Enhanced Export
            </button>
          </div>
        ) : (
          <ExportProgressTracker
            jobId={currentJobId}
            onComplete={handleExportComplete}
            onError={handleExportError}
          />
        )}
      </div>
    </div>
  );
};

export {
  SocialMediaPresetsSelector,
  ExportProgressTracker,
  Phase4ExportInterface,
};
