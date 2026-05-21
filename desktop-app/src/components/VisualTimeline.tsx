import { MonitorPlay, Plus, Redo2, Save, Scissors, Undo2, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useState, type DragEvent as ReactDragEvent, type PointerEvent as ReactPointerEvent } from "react";
import {
  addAssetLayerToScene,
  collectLayerTypes,
  normalizeTimelineMarkers,
  totalTimelineDuration,
  updateSceneTimingAdvanced,
  type LayerData,
  type ProjectData,
  type SceneData
} from "../lib/project";

type TimelineTrackId = "main" | "audio" | "captions" | "broll" | "graphics" | "effects" | "ai";

type TimelineTrackState = Record<TimelineTrackId, {
  locked: boolean;
  hidden: boolean;
  muted?: boolean;
  solo?: boolean;
}>;

type TimelineInteractivePreview = {
  sceneThumbnails?: Array<{
    sceneId: string;
    frame: string;
  }>;
};

export function VisualTimeline({
  project,
  onProjectChange,
  interactivePreview,
  onAutosaveNow,
  onDuplicateProject,
  versionCount = 0,
  recoveryCount = 0
}: {
  project: ProjectData;
  onProjectChange: (project: ProjectData) => void;
  interactivePreview?: TimelineInteractivePreview | null;
  onAutosaveNow?: () => void;
  onDuplicateProject?: () => void;
  versionCount?: number;
  recoveryCount?: number;
}) {
  const [zoom, setZoom] = useState(1);
  const [snapSeconds, setSnapSeconds] = useState(0.25);
  const [rippleEdits, setRippleEdits] = useState(true);
  const [selectedScene, setSelectedScene] = useState(0);
  const [markerLabel, setMarkerLabel] = useState("");
  const [renameDraft, setRenameDraft] = useState(project.timeline?.[0]?.id || "");
  const [groupName, setGroupName] = useState("");
  const [undoStack, setUndoStack] = useState<Array<{ label: string; project: ProjectData }>>([]);
  const [redoStack, setRedoStack] = useState<Array<{ label: string; project: ProjectData }>>([]);
  const [lastTimelineAction, setLastTimelineAction] = useState("ready");
  const [hoverClip, setHoverClip] = useState<{ x: number; y: number; sceneId: string; time: number; frame?: string } | null>(null);
  const [trackState, setTrackState] = useState<TimelineTrackState>({
    main: { locked: false, hidden: false },
    audio: { locked: false, hidden: false, muted: false, solo: false },
    captions: { locked: false, hidden: false },
    broll: { locked: false, hidden: false },
    graphics: { locked: false, hidden: false },
    effects: { locked: false, hidden: false },
    ai: { locked: false, hidden: false }
  });
  const duration = Math.max(totalTimelineDuration(project), 1);
  const pxPerSecond = 70 * zoom;
  const width = duration * pxPerSecond;
  const layerCounts = collectLayerTypes(project);
  const timelineMeta = project.metadata?.timeline as Record<string, unknown> | undefined;
  const savedTimelineMarkers = normalizeTimelineMarkers(timelineMeta?.markers, "marker");
  const reviewMeta = project.metadata?.previewReview as Record<string, unknown> | undefined;
  const previewMarkers = normalizeTimelineMarkers(reviewMeta?.markers, "review", true);
  const timelineMarkers = [...savedTimelineMarkers, ...previewMarkers];
  const selected = project.timeline?.[selectedScene];

  useEffect(() => {
    setRenameDraft(project.timeline?.[selectedScene]?.id || "");
  }, [project.timeline, selectedScene]);

  function clampSelected(index: number) {
    return Math.max(0, Math.min(index, Math.max((project.timeline?.length || 1) - 1, 0)));
  }

  function isMainLocked(sceneIndex = selectedScene) {
    return Boolean(trackState.main.locked || project.timeline?.[sceneIndex]?.locked);
  }

  function pushUndo(label: string) {
    setUndoStack((items) => [...items.slice(-24), { label, project: structuredClone(project) }]);
    setRedoStack([]);
    setLastTimelineAction(label);
  }

  function commitTimelineChange(next: ProjectData, label: string, nextSelection = selectedScene) {
    pushUndo(label);
    setSelectedScene(Math.max(0, Math.min(nextSelection, Math.max((next.timeline?.length || 1) - 1, 0))));
    onProjectChange(next);
  }

  function undoTimeline() {
    const item = undoStack.at(-1);
    if (!item) return;
    setUndoStack((items) => items.slice(0, -1));
    setRedoStack((items) => [...items.slice(-24), { label: "redo snapshot", project: structuredClone(project) }]);
    setLastTimelineAction(`undid ${item.label}`);
    setSelectedScene(0);
    onProjectChange(item.project);
  }

  function redoTimeline() {
    const item = redoStack.at(-1);
    if (!item) return;
    setRedoStack((items) => items.slice(0, -1));
    setUndoStack((items) => [...items.slice(-24), { label: "undo snapshot", project: structuredClone(project) }]);
    setLastTimelineAction("redid timeline action");
    setSelectedScene(0);
    onProjectChange(item.project);
  }

  function toggleTrack(track: TimelineTrackId, key: "locked" | "hidden" | "muted" | "solo") {
    setTrackState((state) => ({
      ...state,
      [track]: {
        ...state[track],
        [key]: !state[track][key]
      }
    }));
  }

  function trackForLayer(layer: LayerData): TimelineTrackId {
    if (layer.type === "audio" || layer.type === "music" || layer.type === "sfx") return "audio";
    if (layer.type === "caption" || layer.type === "captions" || layer.type === "subtitle") return "captions";
    if (layer.type === "text" || layer.type === "lower_third" || layer.type === "shape" || layer.type === "graphic") return "graphics";
    if (layer.type === "effect" || layer.type === "adjustment" || layer.type === "blur" || layer.type === "filter" || layer.type === "lut") return "effects";
    if (layer.type === "image" || layer.type === "overlay" || layer.type === "broll") return "broll";
    return "main";
  }

  function uniqueSceneId(base: string, scenes: SceneData[]) {
    const used = new Set(scenes.map((scene) => scene.id));
    let candidate = base;
    let index = 2;
    while (used.has(candidate)) {
      candidate = `${base}_${index}`;
      index += 1;
    }
    return candidate;
  }

  const beginResize = (sceneIndex: number, event: ReactPointerEvent) => {
    if (isMainLocked(sceneIndex)) return;
    event.preventDefault();
    event.stopPropagation();
    pushUndo("resize scene");
    const startX = event.clientX;
    const original = project.timeline?.[sceneIndex]?.duration || 1;
    const move = (moveEvent: PointerEvent) => {
      const delta = (moveEvent.clientX - startX) / pxPerSecond;
      onProjectChange(updateSceneTimingAdvanced(project, sceneIndex, { duration: Math.max(0.25, Number((original + delta).toFixed(3))) }, { ripple: rippleEdits, snapSeconds }));
    };
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  };

  const beginMove = (sceneIndex: number, event: ReactPointerEvent) => {
    if (isMainLocked(sceneIndex)) return;
    if ((event.target as HTMLElement).closest("button, input")) return;
    event.preventDefault();
    pushUndo("drag scene");
    const startX = event.clientX;
    const original = project.timeline?.[sceneIndex]?.start || 0;
    const move = (moveEvent: PointerEvent) => {
      const delta = (moveEvent.clientX - startX) / pxPerSecond;
      onProjectChange(updateSceneTimingAdvanced(project, sceneIndex, { start: Math.max(0, Number((original + delta).toFixed(3))) }, { ripple: false, snapSeconds }));
    };
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  };

  const dropAsset = (sceneIndex: number, event: ReactDragEvent) => {
    event.preventDefault();
    if (isMainLocked(sceneIndex)) return;
    const assetKey = event.dataTransfer.getData("text/plain");
    if (assetKey) commitTimelineChange(addAssetLayerToScene(project, sceneIndex, assetKey), "drop asset", sceneIndex);
  };

  const nudgeSelected = (delta: number) => {
    const scene = project.timeline?.[selectedScene];
    if (!scene || isMainLocked()) return;
    pushUndo("nudge scene");
    onProjectChange(updateSceneTimingAdvanced(project, selectedScene, { start: Math.max(0, Number(scene.start || 0) + delta) }, { ripple: false, snapSeconds }));
  };

  function splitSelectedScene() {
    if (!selected || isMainLocked() || selected.duration < 0.5) return;
    const scenes = structuredClone(project.timeline || []);
    const scene = scenes[selectedScene];
    const firstDuration = Math.max(0.25, Number((scene.duration / 2).toFixed(3)));
    const secondDuration = Math.max(0.25, Number((scene.duration - firstDuration).toFixed(3)));
    const first = { ...scene, duration: firstDuration };
    const second = {
      ...structuredClone(scene),
      id: uniqueSceneId(`${scene.id}_split`, scenes),
      start: Number((scene.start + firstDuration).toFixed(3)),
      duration: secondDuration
    };
    scenes.splice(selectedScene, 1, first, second);
    commitTimelineChange({ ...project, timeline: scenes }, "split scene", selectedScene + 1);
  }

  function trimSelected(delta: number) {
    if (!selected || isMainLocked()) return;
    const nextDuration = Math.max(0.25, Number((Number(selected.duration || 0) + delta).toFixed(3)));
    commitTimelineChange(updateSceneTimingAdvanced(project, selectedScene, { duration: nextDuration }, { ripple: rippleEdits, snapSeconds }), "trim scene");
  }

  function rippleDeleteSelected() {
    if (!selected || isMainLocked()) return;
    const scenes = structuredClone(project.timeline || []);
    const removed = scenes[selectedScene];
    scenes.splice(selectedScene, 1);
    if (rippleEdits) {
      for (const scene of scenes) {
        if (Number(scene.start || 0) > Number(removed.start || 0)) {
          scene.start = Math.max(0, Number((Number(scene.start || 0) - Number(removed.duration || 0)).toFixed(3)));
        }
      }
    }
    commitTimelineChange({ ...project, timeline: scenes }, "ripple delete", clampSelected(selectedScene - 1));
  }

  function addMarker() {
    if (!selected) return;
    const next = structuredClone(project);
    const metadata = { ...(next.metadata || {}) };
    const timeline = { ...((metadata.timeline as Record<string, unknown> | undefined) || {}) };
    const markers = Array.isArray(timeline.markers) ? [...(timeline.markers as Array<Record<string, unknown>>)] : [];
    markers.push({
      time: Number(selected.start || 0),
      sceneId: selected.id,
      type: "marker",
      label: markerLabel.trim() || selected.id
    });
    timeline.markers = markers;
    metadata.timeline = timeline;
    next.metadata = metadata;
    commitTimelineChange(next, "add marker");
    setMarkerLabel("");
  }

  function snapSelectedToMarker() {
    if (!selected || isMainLocked() || timelineMarkers.length === 0) return;
    const nearest = timelineMarkers.reduce((best, marker) => {
      const bestTime = Number(best.time || 0);
      const markerTime = Number(marker.time || 0);
      return Math.abs(markerTime - selected.start) < Math.abs(bestTime - selected.start) ? marker : best;
    }, timelineMarkers[0]);
    commitTimelineChange(updateSceneTimingAdvanced(project, selectedScene, { start: Number(nearest.time || 0) }, { ripple: false, snapSeconds }), "snap to marker");
  }

  function renameSelectedScene() {
    if (!selected || isMainLocked()) return;
    const nextName = renameDraft.trim();
    if (!nextName || nextName === selected.id) return;
    const next = structuredClone(project);
    if (!next.timeline?.[selectedScene]) return;
    const previousId = next.timeline[selectedScene].id;
    next.timeline[selectedScene].id = uniqueSceneId(nextName, next.timeline.filter((_, index) => index !== selectedScene));
    const metadata = next.metadata || {};
    const timeline = metadata.timeline as Record<string, unknown> | undefined;
    if (timeline && Array.isArray(timeline.markers)) {
      timeline.markers = (timeline.markers as Array<Record<string, unknown>>).map((marker) =>
        marker.sceneId === previousId ? { ...marker, sceneId: next.timeline?.[selectedScene]?.id } : marker
      );
    }
    commitTimelineChange(next, "rename scene");
  }

  function groupSelectedScene() {
    if (!selected || isMainLocked()) return;
    const next = structuredClone(project);
    if (!next.timeline?.[selectedScene]) return;
    next.timeline[selectedScene].group = groupName.trim() || `group_${selectedScene + 1}`;
    commitTimelineChange(next, "group scene");
  }

  function toggleSelectedSceneLock() {
    if (!selected) return;
    const next = structuredClone(project);
    if (!next.timeline?.[selectedScene]) return;
    next.timeline[selectedScene].locked = !next.timeline[selectedScene].locked;
    commitTimelineChange(next, next.timeline[selectedScene].locked ? "lock scene" : "unlock scene");
  }

  function layerPillsForTrack(track: TimelineTrackId) {
    return (project.timeline || []).flatMap((scene) =>
      scene.layers
        .map((layer, layerIndex) => ({ scene, layer, layerIndex }))
        .filter(({ layer }) => trackForLayer(layer) === track)
    );
  }

  function previewFrameForScene(sceneId: string) {
    return interactivePreview?.sceneThumbnails?.find((thumb) => thumb.sceneId === sceneId)?.frame;
  }

  const laneRows: Array<{ id: TimelineTrackId; title: string; hint: string }> = [
    { id: "main", title: "Main video", hint: `${project.timeline?.length || 0} scenes` },
    { id: "audio", title: "Audio", hint: `${project.audio?.length || 0} tracks` },
    { id: "captions", title: "Captions", hint: `${layerCounts.caption || layerCounts.captions || 0} layers` },
    { id: "broll", title: "B-roll", hint: `${layerCounts.image || 0} images` },
    { id: "graphics", title: "Text/graphics", hint: `${layerCounts.text || 0} text` },
    { id: "effects", title: "Effects", hint: "transitions + filters" },
    { id: "ai", title: "AI suggestions", hint: `${previewMarkers.length} markers` }
  ];

  function renderLaneBody(track: TimelineTrackId) {
    if (track === "main") {
      return (
        <>
          {timelineMarkers.map((marker, index) => (
            <span
              className="timeline-marker"
              key={`${String(marker.sceneId || "marker")}-${index}`}
              style={{ left: Number(marker.time || 0) * pxPerSecond }}
              title={`${String(marker.type || "marker")}: ${String(marker.label || "")}`}
            />
          ))}
          {(project.timeline || []).map((scene, index) => (
            <div
              className={`scene-block ${selectedScene === index ? "selected" : ""} ${scene.locked ? "locked" : ""}`}
              key={scene.id}
              onClick={() => setSelectedScene(index)}
              onPointerDown={(event) => beginMove(index, event)}
              onMouseMove={(event) => setHoverClip({
                x: event.clientX + 14,
                y: event.clientY + 14,
                sceneId: scene.id,
                time: Number(scene.start || 0),
                frame: previewFrameForScene(scene.id)
              })}
              onMouseLeave={() => setHoverClip(null)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => dropAsset(index, event)}
              style={{ left: scene.start * pxPerSecond, width: Math.max(scene.duration * pxPerSecond, 42) }}
            >
              <strong>{scene.id}</strong>
              <span>{scene.duration.toFixed(2)}s</span>
              {scene.group && <small>{scene.group}</small>}
              {scene.locked && <small>locked</small>}
              {scene.transitionOut && <small>{String(scene.transitionOut.type || "transition")}</small>}
              <button className="resize-handle" title="Drag timing handle" onPointerDown={(event) => beginResize(index, event)} />
            </div>
          ))}
        </>
      );
    }

    if (track === "audio") {
      return (
        <>
          {(project.audio || []).map((audio, index) => (
            <div
              key={index}
              className={`audio-pill ${trackState.audio.muted ? "muted-track" : ""} ${trackState.audio.solo ? "solo-track" : ""}`}
              style={{
                left: Number(audio.start || 0) * pxPerSecond,
                width: Math.max(Number(audio.duration || duration) * pxPerSecond, 130)
              }}
            >
              audio {String(audio.asset || "")}
            </div>
          ))}
          {layerPillsForTrack("audio").map(({ scene, layer, layerIndex }) => (
            <div
              key={`${scene.id}-audio-${layerIndex}`}
              className="audio-pill"
              style={{
                left: (scene.start + Number(layer.start || 0)) * pxPerSecond,
                width: Math.max(Number(layer.duration || scene.duration) * pxPerSecond, 60)
              }}
            >
              {layer.type} {layer.asset || ""}
            </div>
          ))}
        </>
      );
    }

    if (track === "effects") {
      return (
        <>
          {(project.timeline || []).map((scene) => scene.transitionOut && (
            <div
              key={`${scene.id}-transition`}
              className="layer-pill effect"
              style={{
                left: Math.max(0, (scene.start + scene.duration - Number(scene.transitionOut?.duration || 0.35)) * pxPerSecond),
                width: Math.max(Number(scene.transitionOut?.duration || 0.35) * pxPerSecond, 46)
              }}
            >
              transition {String(scene.transitionOut.type || "cut")}
            </div>
          ))}
          {layerPillsForTrack("effects").map(({ scene, layer, layerIndex }) => (
            <div
              key={`${scene.id}-effects-${layerIndex}`}
              className="layer-pill effect"
              style={{
                left: (scene.start + Number(layer.start || 0)) * pxPerSecond,
                width: Math.max(Number(layer.duration || scene.duration) * pxPerSecond, 46)
              }}
            >
              {layer.type}
            </div>
          ))}
        </>
      );
    }

    if (track === "ai") {
      return (
        <>
          {(project.timeline || []).map((scene) => (
            <div
              key={`${scene.id}-ai`}
              className={`layer-pill ai-pill ${scene.reviewStatus || ""}`}
              style={{
                left: Number(scene.start || 0) * pxPerSecond,
                width: Math.max(Number(scene.duration || 0) * pxPerSecond, 54)
              }}
            >
              {scene.reviewStatus || "review"} {scene.id}
            </div>
          ))}
          {previewMarkers.map((marker, index) => (
            <div
              key={`ai-marker-${index}`}
              className="layer-pill ai-pill marker-pill"
              style={{
                left: Number(marker.time || 0) * pxPerSecond,
                width: 120
              }}
            >
              {String(marker.label || marker.type || "note")}
            </div>
          ))}
        </>
      );
    }

    return (
      <>
        {layerPillsForTrack(track).map(({ scene, layer, layerIndex }) => (
          <div
            key={`${scene.id}-${track}-${layerIndex}`}
            className={`layer-pill ${layer.type}`}
            style={{
              left: (scene.start + Number(layer.start || 0)) * pxPerSecond,
              width: Math.max(Number(layer.duration || scene.duration) * pxPerSecond, 48)
            }}
          >
            {layer.type} {layer.asset || layer.text || ""}
          </div>
        ))}
      </>
    );
  }

  return (
    <div
      className="timeline-pane"
      tabIndex={0}
      onKeyDown={(event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
          event.preventDefault();
          undoTimeline();
          return;
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
          event.preventDefault();
          redoTimeline();
          return;
        }
        if (event.key === "Delete") {
          event.preventDefault();
          rippleDeleteSelected();
          return;
        }
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          nudgeSelected(event.shiftKey ? -snapSeconds * 4 : -snapSeconds);
        }
        if (event.key === "ArrowRight") {
          event.preventDefault();
          nudgeSelected(event.shiftKey ? snapSeconds * 4 : snapSeconds);
        }
      }}
    >
      <div className="timeline-safety-bar">
        <div>
          <strong>Timeline safety</strong>
          <span>{lastTimelineAction}</span>
          <span>{versionCount} versions</span>
          <span>{recoveryCount} restore points</span>
        </div>
        <div>
          <button onClick={undoTimeline} disabled={undoStack.length === 0}><Undo2 size={14} /> Undo</button>
          <button onClick={redoTimeline} disabled={redoStack.length === 0}><Redo2 size={14} /> Redo</button>
          <button onClick={onAutosaveNow} disabled={!onAutosaveNow}><Save size={14} /> Auto-save</button>
          <button onClick={onDuplicateProject} disabled={!onDuplicateProject}>Duplicate project</button>
          <button onClick={toggleSelectedSceneLock}>{selected?.locked ? "Unlock scene" : "Lock scene"}</button>
        </div>
      </div>
      <div className="timeline-tools">
        <div className="timeline-tool-group">
          <button onClick={splitSelectedScene} disabled={!selected || isMainLocked()}><Scissors size={15} /> Split</button>
          <button onClick={() => trimSelected(-snapSeconds)} disabled={!selected || isMainLocked()}>Trim -</button>
          <button onClick={() => trimSelected(snapSeconds)} disabled={!selected || isMainLocked()}>Trim +</button>
          <button onClick={rippleDeleteSelected} disabled={!selected || isMainLocked()}>Ripple delete</button>
        </div>
        <div className="timeline-tool-group">
          <button onClick={() => setZoom((value) => Math.max(0.5, Number((value - 0.25).toFixed(2))))}><ZoomOut size={15} /> Zoom</button>
          <button onClick={() => setZoom((value) => Math.min(4, Number((value + 0.25).toFixed(2))))}><ZoomIn size={15} /> Zoom</button>
          <label><input type="checkbox" checked={rippleEdits} onChange={(event) => setRippleEdits(event.target.checked)} /> ripple</label>
          <label>
            snap
            <select value={snapSeconds} onChange={(event) => setSnapSeconds(Number(event.target.value))}>
              <option value={0.05}>0.05s</option>
              <option value={0.1}>0.10s</option>
              <option value={0.25}>0.25s</option>
              <option value={0.5}>0.50s</option>
            </select>
          </label>
          <button onClick={snapSelectedToMarker} disabled={!selected || timelineMarkers.length === 0}>Snap marker</button>
        </div>
        <div className="timeline-tool-group timeline-tool-fields">
          <input value={renameDraft} onChange={(event) => setRenameDraft(event.target.value)} onBlur={renameSelectedScene} onKeyDown={(event) => event.key === "Enter" && renameSelectedScene()} aria-label="Rename selected scene" />
          <input value={groupName} onChange={(event) => setGroupName(event.target.value)} placeholder="group name" aria-label="Group name" />
          <button onClick={groupSelectedScene} disabled={!selected || isMainLocked()}>Group clips</button>
          <input value={markerLabel} onChange={(event) => setMarkerLabel(event.target.value)} placeholder="marker note" aria-label="Marker label" />
          <button onClick={addMarker} disabled={!selected}><Plus size={14} /> Marker</button>
        </div>
        <span>{duration.toFixed(1)}s</span>
        <span>selected {selected?.id || "-"}</span>
        <span>{Object.entries(layerCounts).map(([type, count]) => `${type}:${count}`).join(" | ")}</span>
      </div>
      <div className="timeline-scroll">
        <div className="time-ruler" style={{ width: width + 154 }}>
          {Array.from({ length: Math.ceil(duration) + 1 }).map((_, index) => (
            <span key={index} style={{ left: 154 + index * pxPerSecond }}>{index}s</span>
          ))}
        </div>
        <div className="timeline-lanes" style={{ width: width + 154 }}>
          {laneRows.map((lane) => (
            <div className={`timeline-lane ${lane.id} ${trackState[lane.id].hidden ? "hidden" : ""}`} key={lane.id}>
              <div className="timeline-lane-header">
                <strong>{lane.title}</strong>
                <span>{lane.hint}</span>
                <div className="track-controls">
                  <button onClick={() => toggleTrack(lane.id, "locked")} className={trackState[lane.id].locked ? "active" : ""}>
                    {trackState[lane.id].locked ? "Locked" : "Lock"}
                  </button>
                  <button onClick={() => toggleTrack(lane.id, "hidden")} className={trackState[lane.id].hidden ? "active" : ""}>
                    {trackState[lane.id].hidden ? "Hidden" : "Hide"}
                  </button>
                  {lane.id === "audio" && (
                    <>
                      <button onClick={() => toggleTrack("audio", "muted")} className={trackState.audio.muted ? "active" : ""}>
                        {trackState.audio.muted ? "Muted" : "Mute"}
                      </button>
                      <button onClick={() => toggleTrack("audio", "solo")} className={trackState.audio.solo ? "active" : ""}>
                        {trackState.audio.solo ? "Soloed" : "Solo"}
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div className="timeline-lane-body" style={{ width }}>
                {trackState[lane.id].hidden ? <span className="track-hidden-label">track hidden</span> : renderLaneBody(lane.id)}
              </div>
            </div>
          ))}
        </div>
        {hoverClip && (
          <div className="timeline-hover-preview" style={{ left: hoverClip.x, top: hoverClip.y }}>
            {hoverClip.frame ? <img src={window.ave.toFileUrl(hoverClip.frame)} alt="" /> : <div className="timeline-hover-placeholder"><MonitorPlay size={24} /></div>}
            <strong>{hoverClip.sceneId}</strong>
            <span>{hoverClip.time.toFixed(2)}s</span>
          </div>
        )}
      </div>
    </div>
  );
}
