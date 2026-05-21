import { CheckCircle2, Maximize2, MonitorPlay, Pause, Play, Plus, RefreshCw, Save } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  addPreviewReviewMarker,
  addPreviewReviewNote,
  applyPreviewPauseEdit,
  comparePreviewVersions,
  previewExportReadiness,
  regeneratePreviewSection,
  restorePreviewVersion,
  savePreviewVersion,
  sceneAtTime,
  setSceneReviewStatus,
  type PauseEditPatch,
  type PreviewMarkerType,
  type PreviewRegenerateAction,
  type PreviewReviewMarker,
  type ProjectData
} from "../lib/project";

type PreviewInteractiveState = {
  previewVideo?: string;
  sceneThumbnails?: Array<{
    sceneId: string;
    start?: number;
    duration?: number;
    frame: string;
  }>;
  waveformPath?: string | null;
  qualityMode?: string;
  scope?: string;
  selectedSceneId?: string | null;
  duration?: number;
  estimatedFinalDuration?: number;
  fps?: number;
  cached?: boolean;
  reportPath?: string;
  supports?: string[];
};

export function PreviewWindow({
  project,
  previewPath,
  realtimePreview,
  interactivePreview,
  previewTimeSeconds,
  setPreviewTimeSeconds,
  previewQualityMode,
  setPreviewQualityMode,
  previewScope,
  setPreviewScope,
  previewSceneId,
  setPreviewSceneId,
  preset,
  exportFormat,
  qualityReport,
  duration,
  onRealtimePreview,
  onInteractivePreview,
  onProjectChange,
  onProjectPreviewChange
}: {
  project: ProjectData | null;
  previewPath: string | null;
  realtimePreview: Record<string, unknown> | null;
  interactivePreview: PreviewInteractiveState | null;
  previewTimeSeconds: number;
  setPreviewTimeSeconds: (value: number) => void;
  previewQualityMode: string;
  setPreviewQualityMode: (value: string) => void;
  previewScope: "full" | "scene";
  setPreviewScope: (value: "full" | "scene") => void;
  previewSceneId: string;
  setPreviewSceneId: (value: string) => void;
  preset: string;
  exportFormat: string;
  qualityReport: Record<string, unknown> | null;
  duration: number;
  onRealtimePreview: () => void;
  onInteractivePreview: () => void;
  onProjectChange: (project: ProjectData) => void;
  onProjectPreviewChange: (project: ProjectData) => Promise<void>;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const previewFrameRef = useRef<HTMLDivElement | null>(null);
  const [time, setTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.85);
  const [loop, setLoop] = useState(false);
  const [performanceNotice, setPerformanceNotice] = useState("");
  const [previewHover, setPreviewHover] = useState<{ x: number; y: number; sceneId: string; time: number; frame?: string } | null>(null);
  const [overlays, setOverlays] = useState({
    safeZones: true,
    captions: true,
    aspectGuides: true,
    sceneMarkers: true,
    aiSuggestions: true,
    crop: true
  });
  const [markerType, setMarkerType] = useState<PreviewMarkerType>("needs_cut");
  const [markerNote, setMarkerNote] = useState("");
  const [previewNote, setPreviewNote] = useState("");
  const [captionDraft, setCaptionDraft] = useState("");
  const [sceneStartDraft, setSceneStartDraft] = useState(0);
  const [sceneDurationDraft, setSceneDurationDraft] = useState(0);
  const [transitionDraft, setTransitionDraft] = useState("crossfade");
  const [transitionDurationDraft, setTransitionDurationDraft] = useState(0.35);
  const [zoomDraft, setZoomDraft] = useState(1);
  const [lightingDraft, setLightingDraft] = useState(0.35);
  const [assetDraft, setAssetDraft] = useState("");
  const [rangeEndDraft, setRangeEndDraft] = useState(0);
  const src = previewPath ? window.ave.toFileUrl(previewPath) : "";
  const framePath = typeof realtimePreview?.frame === "string" ? realtimePreview.frame : "";
  const timelineDuration = Math.max(videoDuration || interactivePreview?.duration || duration || 0, 0);
  const estimatedFinalDuration = Number(interactivePreview?.estimatedFinalDuration || duration || 0);
  const fps = Number(interactivePreview?.fps || project?.project?.fps || 30);
  const playheadPercent = timelineDuration ? Math.min(100, Math.max(0, (time / timelineDuration) * 100)) : 0;
  const thumbnails = interactivePreview?.sceneThumbnails || [];
  const waveformPath = interactivePreview?.waveformPath || "";
  const selectedScene = project?.timeline?.find((scene) => scene.id === previewSceneId) || null;
  const currentProjectTime = previewScope === "scene" && selectedScene ? Number(selectedScene.start || 0) + time : time;
  const currentScene = project ? (previewScope === "scene" && selectedScene ? selectedScene : sceneAtTime(project, currentProjectTime)) : null;
  const currentSceneId = currentScene?.id || previewSceneId || project?.timeline?.[0]?.id || "";
  const assetKeys = Object.keys(project?.assets || {});
  const review = project?.metadata?.previewReview as Record<string, unknown> | undefined;
  const markers = Array.isArray(review?.markers) ? review.markers as PreviewReviewMarker[] : [];
  const notes = Array.isArray(review?.notes) ? review.notes as Array<Record<string, unknown>> : [];
  const readiness = project ? previewExportReadiness(project) : { active: false, ready: true, warnings: [], approved: 0, total: 0 };
  const versionComparison = project ? comparePreviewVersions(project) : "";
  const qualityIssueCount = Number(qualityReport?.issueCount ?? (Array.isArray(qualityReport?.issues) ? qualityReport.issues.length : 0));

  useEffect(() => {
    if (!currentScene) return;
    setCaptionDraft(sceneCaption(currentScene));
    setSceneStartDraft(Number(currentScene.start || 0));
    setSceneDurationDraft(Number(currentScene.duration || 0));
    setTransitionDraft(String(currentScene.transitionOut?.type || "cut"));
    setTransitionDurationDraft(Number(currentScene.transitionOut?.duration || 0));
    const media = currentScene.layers?.find((layer) => layer.type === "video" || layer.type === "image");
    setZoomDraft(Number(media?.scale || 1));
    setAssetDraft(String(media?.asset || ""));
    const post = currentScene.postProcessing as Record<string, unknown> | undefined;
    setLightingDraft(Number(post?.glow || 0.35));
    setRangeEndDraft(Number(currentScene.start || 0) + Number(currentScene.duration || 0));
  }, [currentScene?.id]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      const video = videoRef.current as (HTMLVideoElement & { getVideoPlaybackQuality?: () => { totalVideoFrames: number; droppedVideoFrames: number } }) | null;
      const quality = video?.getVideoPlaybackQuality?.();
      if (!quality || quality.totalVideoFrames < 90) return;
      const dropRate = quality.droppedVideoFrames / Math.max(quality.totalVideoFrames, 1);
      if (dropRate > 0.08 && previewQualityMode !== "draft") {
        setPreviewQualityMode("draft");
        setPerformanceNotice("Preview quality lowered to Performance because playback was dropping frames.");
      }
    }, 2500);
    return () => window.clearInterval(interval);
  }, [previewQualityMode, setPreviewQualityMode]);

  function syncVideo(nextTime: number) {
    const clamped = Math.max(0, Math.min(nextTime, timelineDuration || nextTime));
    if (videoRef.current) videoRef.current.currentTime = clamped;
    setTime(clamped);
  }

  function setRate(nextRate: number) {
    setPlaybackRate(nextRate);
    if (videoRef.current) videoRef.current.playbackRate = nextRate;
  }

  function playPreview() {
    void videoRef.current?.play();
  }

  function pausePreview() {
    videoRef.current?.pause();
  }

  function stopPreview() {
    videoRef.current?.pause();
    syncVideo(0);
  }

  function restartPreview() {
    syncVideo(0);
    void videoRef.current?.play();
  }

  function toggleFullscreen() {
    const element = previewFrameRef.current;
    if (!element) return;
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void element.requestFullscreen();
    }
  }

  function scrubTimeline(nextTime: number) {
    setPreviewTimeSeconds(nextTime);
    syncVideo(nextTime);
  }

  function sceneThumbnail(sceneId: string) {
    return thumbnails.find((thumb) => thumb.sceneId === sceneId)?.frame;
  }

  function toggleOverlay(key: keyof typeof overlays) {
    setOverlays((value) => ({ ...value, [key]: !value[key] }));
  }

  function jumpToScene(sceneId: string) {
    setPreviewSceneId(sceneId);
    const scene = project?.timeline?.find((item) => item.id === sceneId);
    syncVideo(previewScope === "scene" ? 0 : Number(scene?.start || 0));
  }

  function timestamp(value: number) {
    const minutes = Math.floor(value / 60);
    const seconds = value - minutes * 60;
    return `${minutes}:${seconds.toFixed(2).padStart(5, "0")}`;
  }

  function sceneCaption(scene: NonNullable<ProjectData["timeline"]>[number]) {
    const captionLayer = scene.layers?.find((layer) => layer.type === "caption" || layer.type === "captions");
    const items = Array.isArray(captionLayer?.items) ? captionLayer.items as Array<Record<string, unknown>> : [];
    if (items[0]?.text) return String(items[0].text);
    const textLayer = scene.layers?.find((layer) => layer.type === "text" || layer.type === "lower_third");
    return String(textLayer?.text || "");
  }

  function commitReview(next: ProjectData, rebuild = false) {
    if (rebuild) {
      void onProjectPreviewChange(next);
    } else {
      onProjectChange(next);
    }
  }

  function addMarker(type = markerType) {
    if (!project || !currentSceneId) return;
    commitReview(addPreviewReviewMarker(project, { type, time: currentProjectTime, sceneId: currentSceneId, note: markerNote || undefined }));
    setMarkerNote("");
  }

  function addNote() {
    if (!project || !currentSceneId || !previewNote.trim()) return;
    commitReview(addPreviewReviewNote(project, { text: previewNote, time: currentProjectTime, sceneId: currentSceneId }));
    setPreviewNote("");
  }

  function setSceneStatus(status: "approved" | "needs_review" | "locked" | "regenerated" | "excluded") {
    if (!project || !currentSceneId) return;
    commitReview(setSceneReviewStatus(project, currentSceneId, status), status === "excluded");
  }

  function applyPauseEdit(rebuild = true) {
    if (!project || !currentSceneId) return;
    const patch: PauseEditPatch = {
      captionText: captionDraft,
      start: sceneStartDraft,
      duration: sceneDurationDraft,
      transitionType: transitionDraft,
      transitionDuration: transitionDurationDraft,
      zoomAmount: zoomDraft,
      lightingIntensity: lightingDraft,
      assetKey: assetDraft || undefined
    };
    commitReview(applyPreviewPauseEdit(project, currentSceneId, patch), rebuild);
  }

  function regenerate(action: PreviewRegenerateAction) {
    if (!project || !currentSceneId) return;
    commitReview(regeneratePreviewSection(project, currentSceneId, action, { fromTime: currentProjectTime, toTime: rangeEndDraft }), true);
  }

  return (
    <div className="preview-pane">
      <div className="preview-frame" ref={previewFrameRef}>
        {src ? (
          <>
            <video
              ref={videoRef}
              src={src}
              loop={loop}
              muted={muted}
              onPlay={(event) => { setIsPlaying(true); event.currentTarget.playbackRate = playbackRate; event.currentTarget.volume = volume; }}
              onPause={() => setIsPlaying(false)}
              onEnded={() => setIsPlaying(false)}
              onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
              onLoadedMetadata={(event) => {
                setVideoDuration(event.currentTarget.duration || 0);
                event.currentTarget.playbackRate = playbackRate;
                event.currentTarget.volume = volume;
              }}
            />
          </>
        ) : framePath ? (
          <>
            <img className="preview-still" src={window.ave.toFileUrl(framePath)} alt="" />
          </>
        ) : (
          <div className="empty-preview">Render a preview to scrub frames here.</div>
        )}
        <div className="preview-overlay-layer">
          {overlays.safeZones && (
            <>
              <div className="safe-zone title-zone" />
              <div className="safe-zone action-zone" />
            </>
          )}
          {overlays.captions && <div className="caption-boundary"><span>caption safe area</span></div>}
          {overlays.aspectGuides && (
            <div className="aspect-guides">
              <i />
              <i />
              <b />
              <b />
            </div>
          )}
          {overlays.crop && <div className="crop-preview-guide"><span>crop preview</span></div>}
          {overlays.sceneMarkers && (project?.timeline || []).map((scene) => {
            const left = duration ? (Number(scene.start || 0) / duration) * 100 : 0;
            return <span className="overlay-scene-marker" key={scene.id} style={{ left: `${left}%` }} title={scene.id} />;
          })}
          {overlays.aiSuggestions && markers.map((marker) => {
            const left = timelineDuration ? (Number(marker.time || 0) / timelineDuration) * 100 : 0;
            return <span className={`overlay-ai-marker ${marker.type}`} key={marker.id} style={{ left: `${left}%` }} title={`${marker.type}: ${marker.note || ""}`} />;
          })}
        </div>
        <div className="preview-status-badges">
          <span>{isPlaying ? "playing" : "paused"}</span>
          <span>{previewQualityMode === "draft" ? "Performance" : previewQualityMode === "high" ? "Full quality" : "Balanced"}</span>
          <span>{previewScope === "scene" ? "scene preview" : "full timeline"}</span>
        </div>
      </div>
      <div className="preview-controls interactive-controls">
        <div className="preview-toolbar">
          <button onClick={onInteractivePreview}><RefreshCw size={16} /> Build Preview Cache</button>
          <select value={previewQualityMode} onChange={(event) => setPreviewQualityMode(event.target.value)} title="Preview quality mode">
            <option value="draft">Performance</option>
            <option value="balanced">Balanced</option>
            <option value="high">Full quality</option>
          </select>
          <select value={previewScope} onChange={(event) => setPreviewScope(event.target.value as "full" | "scene")} title="Preview scope">
            <option value="full">full timeline</option>
            <option value="scene">selected scene only</option>
          </select>
          <select value={previewSceneId} onChange={(event) => jumpToScene(event.target.value)} title="Jump to scene">
            <option value="">jump to scene</option>
            {(project?.timeline || []).map((scene) => <option key={scene.id} value={scene.id}>{scene.id}</option>)}
          </select>
          <span>{timestamp(time)} / {timestamp(timelineDuration)}</span>
          {performanceNotice && <span className="preview-performance-note">{performanceNotice}</span>}
        </div>
        <div className="preview-toolbar">
          <button onClick={playPreview}><Play size={16} /> Play</button>
          <button onClick={pausePreview}><Pause size={16} /> Pause</button>
          <button onClick={stopPreview}>Stop</button>
          <button onClick={restartPreview}><RefreshCw size={16} /> Restart</button>
          <button onClick={() => syncVideo(time - 1 / Math.max(fps, 1))}>Frame -</button>
          <button onClick={() => syncVideo(time + 1 / Math.max(fps, 1))}>Frame +</button>
          <button onClick={onRealtimePreview}><MonitorPlay size={16} /> Cache Frame</button>
          <button onClick={toggleFullscreen}><Maximize2 size={16} /> Fullscreen</button>
        </div>
        <div className="preview-toolbar">
          <select value={playbackRate} onChange={(event) => setRate(Number(event.target.value))} title="Playback speed">
            <option value={0.25}>0.25x</option>
            <option value={0.5}>0.5x</option>
            <option value={1}>1x</option>
            <option value={1.5}>1.5x</option>
            <option value={2}>2x</option>
          </select>
          <button onClick={() => { const next = !muted; setMuted(next); if (videoRef.current) videoRef.current.muted = next; }}>{muted ? "Unmute" : "Mute"}</button>
          <label className="inline-control">
            Volume
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={volume}
              onChange={(event) => {
                const next = Number(event.target.value);
                setVolume(next);
                if (videoRef.current) videoRef.current.volume = next;
              }}
            />
          </label>
          <label className="check-control">
            <input type="checkbox" checked={loop} onChange={(event) => setLoop(event.target.checked)} />
            Loop preview
          </label>
          <span>final duration {timestamp(estimatedFinalDuration)}</span>
        </div>
        <div className="preview-toolbar overlay-toolbar">
          <span>Overlays</span>
          <label><input type="checkbox" checked={overlays.safeZones} onChange={() => toggleOverlay("safeZones")} /> Safe zones</label>
          <label><input type="checkbox" checked={overlays.captions} onChange={() => toggleOverlay("captions")} /> Captions</label>
          <label><input type="checkbox" checked={overlays.aspectGuides} onChange={() => toggleOverlay("aspectGuides")} /> Aspect guides</label>
          <label><input type="checkbox" checked={overlays.sceneMarkers} onChange={() => toggleOverlay("sceneMarkers")} /> Scene markers</label>
          <label><input type="checkbox" checked={overlays.aiSuggestions} onChange={() => toggleOverlay("aiSuggestions")} /> AI suggestions</label>
          <label><input type="checkbox" checked={overlays.crop} onChange={() => toggleOverlay("crop")} /> Crop preview</label>
        </div>
        <input
          type="range"
          min={0}
          max={Math.max(duration, 0)}
          step={0.05}
          value={Math.min(previewTimeSeconds, Math.max(duration, 0))}
          onChange={(event) => scrubTimeline(Number(event.target.value))}
          title="Realtime preview scrubber"
        />
        <input
          type="range"
          min={0}
          max={timelineDuration || 0}
          step={0.01}
          value={time}
          onChange={(event) => syncVideo(Number(event.target.value))}
          title="Playable preview scrubber"
        />
        <div className="preview-timeline">
          {(project?.timeline || []).map((scene) => {
            const left = duration ? (Number(scene.start || 0) / duration) * 100 : 0;
            const width = duration ? (Number(scene.duration || 0) / duration) * 100 : 0;
            return (
              <button
                key={scene.id}
                className="preview-scene-segment"
                style={{ left: `${left}%`, width: `${Math.max(width, 2)}%` }}
                onClick={() => jumpToScene(scene.id)}
                onMouseMove={(event) => setPreviewHover({
                  x: event.clientX + 14,
                  y: event.clientY + 14,
                  sceneId: scene.id,
                  time: Number(scene.start || 0),
                  frame: sceneThumbnail(scene.id)
                })}
                onMouseLeave={() => setPreviewHover(null)}
                title={`${scene.id} ${Number(scene.duration || 0).toFixed(2)}s`}
              >
                {scene.id}
              </button>
            );
          })}
          <div className="preview-playhead" style={{ left: `${playheadPercent}%` }} />
        </div>
        {waveformPath && (
          <div className="waveform-strip">
            <img src={window.ave.toFileUrl(waveformPath)} alt="" />
            <div className="preview-playhead" style={{ left: `${playheadPercent}%` }} />
          </div>
        )}
        {thumbnails.length > 0 && (
          <div className="scene-thumb-strip">
            {thumbnails.map((thumb) => (
              <button key={thumb.sceneId} className="scene-thumb" onClick={() => jumpToScene(thumb.sceneId)}>
                <img src={window.ave.toFileUrl(thumb.frame)} alt="" />
                <span>{thumb.sceneId}</span>
              </button>
            ))}
          </div>
        )}
        {previewHover && (
          <div className="timeline-hover-preview" style={{ left: previewHover.x, top: previewHover.y }}>
            {previewHover.frame ? <img src={window.ave.toFileUrl(previewHover.frame)} alt="" /> : <div className="timeline-hover-placeholder"><MonitorPlay size={24} /></div>}
            <strong>{previewHover.sceneId}</strong>
            <span>{previewHover.time.toFixed(2)}s</span>
          </div>
        )}
        {interactivePreview && (
          <div className="metric-grid">
            <span>mode <strong>{interactivePreview.qualityMode || previewQualityMode}</strong></span>
            <span>scope <strong>{interactivePreview.scope || previewScope}</strong></span>
            <span>cache <strong>{interactivePreview.cached ? "reused" : "fresh"}</strong></span>
            <span>fps <strong>{String(interactivePreview.fps || fps)}</strong></span>
          </div>
        )}
        {project && currentScene && (
          <div className="preview-review-grid">
            <section className="preview-review-card">
              <h3>Review Markers</h3>
              <div className="preview-toolbar">
                <select value={markerType} onChange={(event) => setMarkerType(event.target.value as PreviewMarkerType)}>
                  <option value="needs_cut">needs cut</option>
                  <option value="too_slow">too slow</option>
                  <option value="too_fast">too fast</option>
                  <option value="bad_caption">bad caption</option>
                  <option value="bad_zoom">bad zoom</option>
                  <option value="bad_transition">bad transition</option>
                  <option value="audio_issue">audio issue</option>
                  <option value="keep">keep this section</option>
                </select>
                <input value={markerNote} onChange={(event) => setMarkerNote(event.target.value)} placeholder="marker note" />
                <button onClick={() => addMarker()}><Plus size={15} /> Mark</button>
                <button onClick={() => addMarker("keep")}><CheckCircle2 size={15} /> Keep</button>
              </div>
              <div className="review-list">
                {markers.slice(-5).reverse().map((marker) => (
                  <div className={`review-item ${marker.resolved ? "resolved" : ""}`} key={marker.id}>
                    <strong>{marker.type.replace(/_/g, " ")}</strong>
                    <span>{marker.sceneId} at {timestamp(Number(marker.time || 0))}</span>
                    <small>{marker.note || (marker.resolved ? "resolved" : "open")}</small>
                  </div>
                ))}
                {!markers.length && <p className="muted">No review markers yet.</p>}
              </div>
            </section>

            <section className="preview-review-card">
              <h3>Pause And Edit</h3>
              <div className="control-grid">
                <label>
                  Scene
                  <input value={currentSceneId} readOnly />
                </label>
                <label>
                  Caption
                  <input value={captionDraft} onChange={(event) => setCaptionDraft(event.target.value)} />
                </label>
                <label>
                  Start
                  <input type="number" step={0.05} value={sceneStartDraft} onChange={(event) => setSceneStartDraft(Number(event.target.value))} />
                </label>
                <label>
                  Duration
                  <input type="number" min={0.1} step={0.05} value={sceneDurationDraft} onChange={(event) => setSceneDurationDraft(Number(event.target.value))} />
                </label>
                <label>
                  Transition
                  <select value={transitionDraft} onChange={(event) => setTransitionDraft(event.target.value)}>
                    <option value="cut">cut</option>
                    <option value="crossfade">crossfade</option>
                    <option value="fadeToBlack">fade to black</option>
                    <option value="slide">slide</option>
                    <option value="zoom">zoom</option>
                  </select>
                </label>
                <label>
                  Transition seconds
                  <input type="number" min={0} step={0.05} value={transitionDurationDraft} onChange={(event) => setTransitionDurationDraft(Number(event.target.value))} />
                </label>
                <label>
                  Zoom
                  <input type="number" min={0.1} step={0.05} value={zoomDraft} onChange={(event) => setZoomDraft(Number(event.target.value))} />
                </label>
                <label>
                  Lighting
                  <input type="number" min={0} max={1} step={0.05} value={lightingDraft} onChange={(event) => setLightingDraft(Number(event.target.value))} />
                </label>
                <label>
                  Replace asset
                  <select value={assetDraft} onChange={(event) => setAssetDraft(event.target.value)}>
                    <option value="">keep current</option>
                    {assetKeys.map((key) => <option key={key} value={key}>{key}</option>)}
                  </select>
                </label>
              </div>
              <div className="button-grid compact">
                <button onClick={() => applyPauseEdit(false)}><Save size={15} /> Apply JSON</button>
                <button onClick={() => applyPauseEdit(true)}><MonitorPlay size={15} /> Apply + Preview</button>
                <button onClick={() => currentSceneId && commitReview(applyPreviewPauseEdit(project, currentSceneId, { lockScene: true }))}>Lock Scene</button>
                <button onClick={() => currentSceneId && commitReview(applyPreviewPauseEdit(project, currentSceneId, { removeScene: true }), true)}>Remove Scene</button>
              </div>
            </section>

            <section className="preview-review-card">
              <h3>Regenerate From Preview</h3>
              <div className="control-grid">
                <label>
                  Range end
                  <input type="number" min={currentProjectTime} step={0.05} value={rangeEndDraft} onChange={(event) => setRangeEndDraft(Number(event.target.value))} />
                </label>
              </div>
              <div className="button-grid compact">
                <button onClick={() => regenerate("scene")}>Current Scene</button>
                <button onClick={() => regenerate("captions_from_here")}>Captions From Here</button>
                <button onClick={() => regenerate("transitions")}>Transitions</button>
                <button onClick={() => regenerate("music_sync")}>Music Sync</button>
                <button onClick={() => regenerate("pacing")}>Pacing</button>
                <button onClick={() => regenerate("selected_range")}>Selected Range</button>
              </div>
            </section>

            <section className="preview-review-card">
              <h3>Approval</h3>
              <div className="button-grid compact">
                <button onClick={() => setSceneStatus("approved")}><CheckCircle2 size={15} /> Approve</button>
                <button onClick={() => setSceneStatus("needs_review")}>Needs Review</button>
                <button onClick={() => setSceneStatus("locked")}>Lock</button>
                <button onClick={() => setSceneStatus("excluded")}>Exclude From Final</button>
              </div>
              <div className="metric-grid">
                <span>approved <strong>{readiness.approved}/{readiness.total}</strong></span>
                <span>gate <strong>{readiness.ready ? "ready" : "blocked"}</strong></span>
                <span>warnings <strong>{readiness.warnings.length}</strong></span>
                <span>duration <strong>{timestamp(estimatedFinalDuration)}</strong></span>
                <span>format <strong>{exportFormat}</strong></span>
                <span>preset <strong>{preset}</strong></span>
                <span>quality <strong>{qualityReport ? (qualityIssueCount ? `${qualityIssueCount} issue(s)` : "passed") : "not run"}</strong></span>
              </div>
              {readiness.warnings.slice(0, 4).map((warning) => <small className="warning-line" key={warning}>{warning}</small>)}
            </section>

            <section className="preview-review-card">
              <h3>Notes</h3>
              <div className="preview-toolbar">
                <input value={previewNote} onChange={(event) => setPreviewNote(event.target.value)} placeholder="make this smoother, zoom in more, use darker lighting..." />
                <button onClick={addNote}><Plus size={15} /> Add Note</button>
              </div>
              <div className="review-list">
                {notes.slice(-4).reverse().map((note) => (
                  <div className="review-item" key={String(note.id)}>
                    <strong>{String(note.sceneId)}</strong>
                    <span>{timestamp(Number(note.time || 0))}</span>
                    <small>{String(note.text || "")}</small>
                  </div>
                ))}
                {!notes.length && <p className="muted">Pause anywhere and leave a note tied to that timestamp.</p>}
              </div>
            </section>

            <section className="preview-review-card">
              <h3>A/B Versions</h3>
              <div className="button-grid compact">
                <button onClick={() => commitReview(savePreviewVersion(project, "A"))}>Save A</button>
                <button onClick={() => commitReview(savePreviewVersion(project, "B"))}>Save B</button>
                <button onClick={() => commitReview(restorePreviewVersion(project, "A"), true)}>Use A</button>
                <button onClick={() => commitReview(restorePreviewVersion(project, "B"), true)}>Use B</button>
              </div>
              <pre className="mini-pre">{versionComparison}</pre>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
