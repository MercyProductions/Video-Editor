export type ProjectData = {
  metadata?: Record<string, unknown>;
  exportPreset?: string;
  stylePreset?: string;
  project?: {
    width?: number;
    height?: number;
    fps?: number;
    duration?: number;
    background?: string;
    exportPreset?: string;
  };
  assets?: Record<string, string>;
  timeline?: SceneData[];
  audio?: Array<Record<string, unknown>>;
  captions?: Array<Record<string, unknown>>;
};

export type PreviewMarkerType =
  | "needs_cut"
  | "too_slow"
  | "too_fast"
  | "bad_caption"
  | "bad_zoom"
  | "bad_transition"
  | "audio_issue"
  | "keep";

export type PreviewSceneStatus = "approved" | "needs_review" | "locked" | "regenerated" | "excluded";

export type PreviewReviewMarker = {
  id: string;
  type: PreviewMarkerType;
  time: number;
  sceneId: string;
  note?: string;
  resolved?: boolean;
  createdAt: string;
};

export type PreviewReviewNote = {
  id: string;
  time: number;
  sceneId: string;
  text: string;
  createdAt: string;
};

export type PauseEditPatch = {
  captionText?: string;
  start?: number;
  duration?: number;
  transitionType?: string;
  transitionDuration?: number;
  zoomAmount?: number;
  lightingIntensity?: number;
  assetKey?: string;
  lockScene?: boolean;
  excludeScene?: boolean;
  removeScene?: boolean;
};

export type PreviewRegenerateAction =
  | "scene"
  | "captions_from_here"
  | "transitions"
  | "music_sync"
  | "pacing"
  | "selected_range";

export type SceneData = {
  id: string;
  start: number;
  duration: number;
  layers: LayerData[];
  transitionOut?: Record<string, unknown>;
  group?: string;
  nestedScene?: boolean;
  timelineMarkers?: Array<Record<string, unknown>>;
  reviewStatus?: PreviewSceneStatus;
  locked?: boolean;
  excludeFromFinal?: boolean;
  [key: string]: unknown;
};

export type LayerData = {
  type: string;
  asset?: string;
  text?: string;
  start?: number;
  duration?: number;
  layout?: string;
  [key: string]: unknown;
};

export function parseProject(text: string): { data?: ProjectData; error?: string } {
  try {
    const data = JSON.parse(text) as ProjectData;
    return { data };
  } catch (error) {
    return { error: error instanceof Error ? error.message : String(error) };
  }
}

export function formatProject(data: ProjectData): string {
  return JSON.stringify(data, null, 2);
}

export function blankProject(): ProjectData {
  return {
    metadata: {
      createdBy: "Automatic Video Editor Desktop"
    },
    exportPreset: "youtube_1080p",
    project: {
      width: 1920,
      height: 1080,
      fps: 60,
      duration: 8,
      background: "#05070d"
    },
    assets: {},
    timeline: [
      {
        id: "scene_1",
        start: 0,
        duration: 8,
        layers: [
          {
            type: "text",
            text: "New Project",
            layout: "center",
            fontSize: 72,
            color: "#ffffff",
            strokeColor: "#000000",
            strokeWidth: 2
          }
        ]
      }
    ],
    audio: []
  };
}

export function totalTimelineDuration(data: ProjectData): number {
  return Math.max(
    Number(data.project?.duration || 0),
    ...(data.timeline || []).map((scene) => Number(scene.start || 0) + Number(scene.duration || 0)),
    0
  );
}

export function updateSceneTiming(data: ProjectData, sceneIndex: number, patch: Partial<SceneData>): ProjectData {
  const next = structuredClone(data);
  if (!next.timeline?.[sceneIndex]) return next;
  next.timeline[sceneIndex] = { ...next.timeline[sceneIndex], ...patch };
  const duration = totalTimelineDuration(next);
  next.project = { ...next.project, duration: Math.max(duration, Number(next.project?.duration || 0)) };
  return next;
}

export function updateSceneTimingAdvanced(
  data: ProjectData,
  sceneIndex: number,
  patch: Partial<SceneData>,
  options: { ripple?: boolean; snapSeconds?: number } = {}
): ProjectData {
  const next = structuredClone(data);
  const scene = next.timeline?.[sceneIndex];
  if (!scene) return next;
  const snap = Math.max(Number(options.snapSeconds || 0), 0);
  const originalDuration = Number(scene.duration || 0);
  const snappedPatch = { ...patch };
  if (typeof snappedPatch.start === "number" && snap > 0) snappedPatch.start = snapValue(snappedPatch.start, snap);
  if (typeof snappedPatch.duration === "number" && snap > 0) snappedPatch.duration = Math.max(snap, snapValue(snappedPatch.duration, snap));
  next.timeline![sceneIndex] = { ...scene, ...snappedPatch };
  const durationDelta = Number(next.timeline![sceneIndex].duration || 0) - originalDuration;
  if (options.ripple && Math.abs(durationDelta) > 0.0001) {
    for (let index = sceneIndex + 1; index < next.timeline!.length; index += 1) {
      next.timeline![index].start = Number(((next.timeline![index].start || 0) + durationDelta).toFixed(3));
    }
  }
  next.project = { ...next.project, duration: totalTimelineDuration(next) };
  return next;
}

export function addScene(data: ProjectData): ProjectData {
  const next = structuredClone(data);
  const timeline = next.timeline || [];
  const start = totalTimelineDuration(next);
  timeline.push({
    id: `scene_${timeline.length + 1}`,
    start,
    duration: 4,
    layers: [
      {
        type: "text",
        text: `Scene ${timeline.length + 1}`,
        layout: "lower_third",
        fontSize: 54,
        color: "#ffffff",
        strokeColor: "#000000",
        strokeWidth: 2
      }
    ],
    transitionOut: { type: "crossfade", duration: 0.4 }
  });
  next.timeline = timeline;
  next.project = { ...next.project, duration: totalTimelineDuration(next) };
  return next;
}

export function addImportedAssets(data: ProjectData, assets: ImportedAsset[]): ProjectData {
  const next = structuredClone(data);
  next.assets = { ...(next.assets || {}) };
  for (const asset of assets) {
    let key = asset.key;
    let suffix = 1;
    while (next.assets[key]) {
      key = `${asset.key}_${suffix++}`;
    }
    next.assets[key] = asset.path;
  }
  return next;
}

export function addAssetToFirstScene(data: ProjectData, asset: ImportedAsset): ProjectData {
  const next = addImportedAssets(data, [asset]);
  const timeline = next.timeline || [];
  if (!timeline[0]) return next;
  const type = asset.type === "image" ? "image" : asset.type === "video" ? "video" : null;
  if (!type) return next;
  timeline[0].layers.push({
    type,
    asset: asset.key,
    layout: type === "image" ? "pip" : "center",
    autoFit: type === "video" ? "cover" : undefined
  });
  return next;
}

export function addAssetLayerToScene(data: ProjectData, sceneIndex: number, assetKey: string): ProjectData {
  const next = structuredClone(data);
  const scene = next.timeline?.[sceneIndex];
  const assetPath = next.assets?.[assetKey] || "";
  if (!scene || !assetPath) return next;

  const kind = inferAssetKind(assetPath);
  if (kind === "audio") {
    next.audio = [
      ...(next.audio || []),
      {
        asset: assetKey,
        start: scene.start,
        duration: scene.duration,
        volume: 0.8
      }
    ];
    return next;
  }

  if (kind === "unknown") return next;
  scene.layers.push({
    type: kind,
    asset: assetKey,
    layout: kind === "image" ? "pip" : "center",
    autoFit: kind === "video" ? "cover" : undefined
  });
  return next;
}

export function explainProject(data: ProjectData): string {
  const scenes = data.timeline || [];
  const layers = scenes.reduce((count, scene) => count + (scene.layers?.length || 0), 0);
  const audio = data.audio?.length || 0;
  const preset = data.exportPreset || data.project?.exportPreset || "custom";
  return [
    `Project: ${data.project?.width || "?"}x${data.project?.height || "?"} at ${data.project?.fps || "?"}fps.`,
    `Duration: ${data.project?.duration || totalTimelineDuration(data)} seconds.`,
    `Preset: ${preset}.`,
    `Timeline: ${scenes.length} scenes, ${layers} layers, ${audio} audio tracks.`,
    `Assets: ${Object.keys(data.assets || {}).length} mapped asset references.`
  ].join("\n");
}

function inferAssetKind(assetPath: string): "image" | "video" | "audio" | "unknown" {
  const clean = assetPath.split(/[?#]/)[0].toLowerCase();
  if (/\.(png|jpg|jpeg|webp|bmp|gif|tiff|tif|svg)$/.test(clean)) return "image";
  if (/\.(mp4|mov|mkv|avi|webm|flv|wmv|mpeg|mpg|m4v|ts|mts|m2ts)$/.test(clean)) return "video";
  if (/\.(wav|mp3|m4a|aac|flac|ogg)$/.test(clean)) return "audio";
  return "unknown";
}

export function suggestBetterTransitions(data: ProjectData): ProjectData {
  const next = structuredClone(data);
  const timeline = next.timeline || [];
  timeline.forEach((scene, index) => {
    if (index === timeline.length - 1) {
      delete scene.transitionOut;
      return;
    }
    const nextScene = timeline[index + 1];
    const shortCut = scene.duration <= 2.2 || nextScene.duration <= 2.2;
    scene.transitionOut = shortCut ? { type: "cut", duration: 0 } : { type: "crossfade", duration: 0.45 };
  });
  next.metadata = { ...(next.metadata || {}), transitionSuggestion: "Applied cut for very short scenes and crossfade for longer scenes." };
  return next;
}

export function collectLayerTypes(data: ProjectData): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const scene of data.timeline || []) {
    for (const layer of scene.layers || []) {
      counts[layer.type] = (counts[layer.type] || 0) + 1;
    }
  }
  return counts;
}

export function sceneAtTime(data: ProjectData, time: number): SceneData | null {
  const scenes = data.timeline || [];
  return scenes.find((scene) => Number(scene.start || 0) <= time && time < Number(scene.start || 0) + Number(scene.duration || 0)) || scenes[scenes.length - 1] || null;
}

export function addPreviewReviewMarker(data: ProjectData, marker: Omit<PreviewReviewMarker, "id" | "createdAt">): ProjectData {
  const next = ensurePreviewReview(data);
  const review = next.metadata!.previewReview as Record<string, unknown>;
  const markers = Array.isArray(review.markers) ? review.markers as PreviewReviewMarker[] : [];
  review.markers = [
    ...markers,
    {
      ...marker,
      id: `marker_${Date.now()}_${markers.length + 1}`,
      time: round(marker.time),
      createdAt: new Date().toISOString()
    }
  ];
  review.enforceExportGate = true;
  return next;
}

export function addPreviewReviewNote(data: ProjectData, note: Omit<PreviewReviewNote, "id" | "createdAt">): ProjectData {
  const next = ensurePreviewReview(data);
  const review = next.metadata!.previewReview as Record<string, unknown>;
  const notes = Array.isArray(review.notes) ? review.notes as PreviewReviewNote[] : [];
  review.notes = [
    ...notes,
    {
      ...note,
      id: `note_${Date.now()}_${notes.length + 1}`,
      time: round(note.time),
      createdAt: new Date().toISOString()
    }
  ];
  review.enforceExportGate = true;
  return next;
}

export function setSceneReviewStatus(data: ProjectData, sceneId: string, status: PreviewSceneStatus): ProjectData {
  const next = ensurePreviewReview(data);
  const scene = next.timeline?.find((item) => item.id === sceneId);
  if (!scene) return next;
  scene.reviewStatus = status;
  scene.locked = status === "locked" ? true : scene.locked;
  scene.excludeFromFinal = status === "excluded";
  const review = next.metadata!.previewReview as Record<string, unknown>;
  review.sceneStatuses = { ...(review.sceneStatuses as Record<string, string> || {}), [sceneId]: status };
  if (status === "approved" || status === "locked") {
    review.markers = (Array.isArray(review.markers) ? review.markers as PreviewReviewMarker[] : []).map((marker) =>
      marker.sceneId === sceneId ? { ...marker, resolved: true } : marker
    );
  }
  review.enforceExportGate = true;
  return next;
}

export function applyPreviewPauseEdit(data: ProjectData, sceneId: string, patch: PauseEditPatch): ProjectData {
  const next = ensurePreviewReview(data);
  const timeline = next.timeline || [];
  const index = timeline.findIndex((scene) => scene.id === sceneId);
  const scene = timeline[index];
  if (!scene || scene.locked) return next;

  if (patch.removeScene) {
    timeline.splice(index, 1);
    compactTimeline(next);
    appendReviewChange(next, `Removed scene ${sceneId}`);
    return next;
  }

  if (typeof patch.start === "number") scene.start = Math.max(0, round(patch.start));
  if (typeof patch.duration === "number") scene.duration = Math.max(0.1, round(patch.duration));
  if (patch.transitionType) {
    scene.transitionOut = {
      type: patch.transitionType,
      duration: Math.max(0, Number(patch.transitionDuration ?? scene.transitionOut?.duration ?? 0.35))
    };
  }
  if (typeof patch.zoomAmount === "number") {
    const media = firstMediaLayer(scene);
    if (media) {
      media.scale = Math.max(0.1, round(patch.zoomAmount));
      media.animation = { ...(typeof media.animation === "object" && media.animation ? media.animation as Record<string, unknown> : {}), in: "zoomIn", duration: 0.45 };
    }
  }
  if (typeof patch.lightingIntensity === "number") {
    const amount = Math.max(0, Math.min(1, patch.lightingIntensity));
    scene.postProcessing = {
      ...(scene.postProcessing as Record<string, unknown> || {}),
      glow: round(amount * 0.5),
      vignette: round(0.18 + amount * 0.45),
      colorGrade: {
        contrast: round(1 + amount * 0.22),
        brightness: round(-amount * 0.04),
        saturation: round(1 + amount * 0.08)
      }
    };
  }
  if (patch.assetKey) {
    const media = firstMediaLayer(scene);
    if (media) media.asset = patch.assetKey;
  }
  if (typeof patch.captionText === "string") {
    updateSceneCaption(scene, patch.captionText);
  }
  if (patch.lockScene) scene.locked = true;
  if (patch.excludeScene) {
    scene.excludeFromFinal = true;
    scene.reviewStatus = "excluded";
  }

  next.project = { ...next.project, duration: totalTimelineDuration(next) };
  appendReviewChange(next, `Edited scene ${sceneId} from preview controls`);
  return next;
}

export function regeneratePreviewSection(
  data: ProjectData,
  sceneId: string,
  action: PreviewRegenerateAction,
  options: { fromTime?: number; toTime?: number } = {}
): ProjectData {
  const next = ensurePreviewReview(data);
  const scene = next.timeline?.find((item) => item.id === sceneId);
  if (!scene || scene.locked) return next;

  if (action === "scene") {
    updateSceneCaption(scene, readableSceneTitle(scene.id));
    scene.transitionOut = { type: "crossfade", duration: 0.35 };
    const media = firstMediaLayer(scene);
    if (media) {
      media.camera = {
        mode: "dynamic_zoom",
        zoom: 1.08,
        intensity: 0.35,
        duration: Math.min(3, Math.max(1, Number(scene.duration || 1)))
      };
    }
    scene.reviewStatus = "regenerated";
  }
  if (action === "captions_from_here") {
    for (const item of next.timeline || []) {
      if (Number(item.start || 0) >= Number(scene.start || 0) && !item.locked) updateSceneCaption(item, readableSceneTitle(item.id));
    }
  }
  if (action === "transitions") {
    next.timeline?.forEach((item, index) => {
      if (index < (next.timeline?.length || 0) - 1 && !item.locked) {
        item.transitionOut = Number(item.duration || 0) < 2.4 ? { type: "cut", duration: 0 } : { type: "crossfade", duration: 0.35 };
      }
    });
  }
  if (action === "music_sync") {
    const beat = 0.5;
    for (const item of next.timeline || []) {
      if (!item.locked) {
        item.start = snapValue(Number(item.start || 0), beat);
        item.duration = Math.max(beat, snapValue(Number(item.duration || beat), beat));
      }
    }
    next.audio = (next.audio || []).map((track) => ({ ...track, start: snapValue(Number(track.start || 0), beat), fadeIn: track.fadeIn ?? 0.5, fadeOut: track.fadeOut ?? 0.75 }));
  }
  if (action === "pacing") {
    for (const item of next.timeline || []) {
      if (!item.locked) item.duration = Math.max(1.2, Math.min(Number(item.duration || 2.5), 4.5));
    }
    compactTimeline(next);
  }
  if (action === "selected_range") {
    const from = Number(options.fromTime ?? scene.start);
    const to = Number(options.toTime ?? scene.start + scene.duration);
    for (const item of next.timeline || []) {
      const overlaps = Number(item.start || 0) < to && Number(item.start || 0) + Number(item.duration || 0) > from;
      if (overlaps && !item.locked) {
        item.transitionOut = { type: "crossfade", duration: 0.25 };
        updateSceneCaption(item, readableSceneTitle(item.id));
      }
    }
  }

  next.project = { ...next.project, duration: totalTimelineDuration(next) };
  appendReviewChange(next, `Regenerated ${action.replace(/_/g, " ")} from preview`);
  return next;
}

export function savePreviewVersion(data: ProjectData, slot: "A" | "B", label?: string): ProjectData {
  const next = ensurePreviewReview(data);
  const review = next.metadata!.previewReview as Record<string, unknown>;
  const versions = { ...(review.versions as Record<string, unknown> || {}) };
  versions[slot] = {
    label: label || `Version ${slot}`,
    createdAt: new Date().toISOString(),
    summary: versionSummary(next),
    project: projectSnapshot(next)
  };
  review.versions = versions;
  review.activeVersion = slot;
  appendReviewChange(next, `Saved Version ${slot}`);
  return next;
}

export function restorePreviewVersion(data: ProjectData, slot: "A" | "B"): ProjectData {
  const review = data.metadata?.previewReview as Record<string, unknown> | undefined;
  const version = (review?.versions as Record<string, { project?: ProjectData }> | undefined)?.[slot];
  if (!version?.project) return data;
  const restored = structuredClone(version.project);
  restored.metadata = {
    ...(restored.metadata || {}),
    previewReview: {
      ...review,
      activeVersion: slot,
      restoredAt: new Date().toISOString()
    }
  };
  appendReviewChange(restored, `Restored Version ${slot}`);
  return restored;
}

export function comparePreviewVersions(data: ProjectData): string {
  const review = data.metadata?.previewReview as Record<string, unknown> | undefined;
  const versions = review?.versions as Record<string, { summary?: Record<string, unknown> }> | undefined;
  const a = versions?.A?.summary;
  const b = versions?.B?.summary;
  if (!a || !b) return "Save Version A and Version B to compare timing, captions, and style.";
  return [
    `Timing: A ${a.duration}s / B ${b.duration}s`,
    `Scenes: A ${a.sceneCount} / B ${b.sceneCount}`,
    `Captions: A ${a.captionCount} / B ${b.captionCount}`,
    `Style: A ${a.style || "custom"} / B ${b.style || "custom"}`
  ].join("\n");
}

export function previewExportReadiness(data: ProjectData): { active: boolean; ready: boolean; warnings: string[]; approved: number; total: number } {
  const review = data.metadata?.previewReview as Record<string, unknown> | undefined;
  const active = Boolean(review?.enforceExportGate);
  const scenes = (data.timeline || []).filter((scene) => !scene.excludeFromFinal);
  const unresolvedMarkers = (Array.isArray(review?.markers) ? review?.markers as PreviewReviewMarker[] : []).filter((marker) => !marker.resolved && marker.type !== "keep");
  const unapproved = scenes.filter((scene) => scene.reviewStatus !== "approved" && scene.reviewStatus !== "locked");
  const warnings = [
    ...unresolvedMarkers.map((marker) => `${marker.sceneId}: ${marker.type.replace(/_/g, " ")} at ${marker.time}s`),
    ...unapproved.map((scene) => `${scene.id}: ${scene.reviewStatus || "needs approval"}`)
  ];
  return {
    active,
    ready: !active || warnings.length === 0,
    warnings,
    approved: scenes.length - unapproved.length,
    total: scenes.length
  };
}

function ensurePreviewReview(data: ProjectData): ProjectData {
  const next = structuredClone(data);
  next.metadata = { ...(next.metadata || {}) };
  next.metadata.previewReview = {
    markers: [],
    notes: [],
    changes: [],
    sceneStatuses: {},
    ...(next.metadata.previewReview as Record<string, unknown> || {})
  };
  return next;
}

function appendReviewChange(data: ProjectData, summary: string): void {
  data.metadata = { ...(data.metadata || {}) };
  const review = data.metadata.previewReview as Record<string, unknown> | undefined;
  if (!review) return;
  const changes = Array.isArray(review.changes) ? review.changes as Array<Record<string, unknown>> : [];
  review.changes = [...changes.slice(-30), { summary, createdAt: new Date().toISOString() }];
  review.enforceExportGate = true;
}

function firstMediaLayer(scene: SceneData): LayerData | undefined {
  return scene.layers?.find((layer) => layer.type === "video" || layer.type === "image");
}

function updateSceneCaption(scene: SceneData, text: string): void {
  const clean = text.trim();
  if (!clean) return;
  const caption = scene.layers?.find((layer) => layer.type === "caption" || layer.type === "captions");
  if (caption) {
    const items = Array.isArray(caption.items) ? caption.items as Array<Record<string, unknown>> : [];
    caption.items = items.length
      ? [{ ...items[0], text: clean }, ...items.slice(1)]
      : [{ text: clean, start: 0, duration: Math.max(0.5, Number(scene.duration || 2)) }];
    return;
  }
  const textLayer = scene.layers?.find((layer) => layer.type === "text" || layer.type === "lower_third");
  if (textLayer) {
    textLayer.text = clean;
    return;
  }
  scene.layers = [
    ...(scene.layers || []),
    {
      type: "text",
      text: clean,
      layout: "lower_third",
      fontSize: 48,
      color: "#ffffff",
      strokeColor: "#000000",
      strokeWidth: 3,
      box: true,
      boxColor: "#00000099",
      boxPadding: 12
    }
  ];
}

function compactTimeline(data: ProjectData): void {
  let cursor = 0;
  for (const scene of data.timeline || []) {
    scene.start = round(cursor);
    cursor += Number(scene.duration || 0);
  }
  data.project = { ...data.project, duration: round(cursor) };
}

function readableSceneTitle(sceneId: string): string {
  return sceneId.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function projectSnapshot(data: ProjectData): ProjectData {
  const snapshot = structuredClone(data);
  if (snapshot.metadata?.previewReview) {
    const review = snapshot.metadata.previewReview as Record<string, unknown>;
    snapshot.metadata.previewReview = { ...review, versions: undefined };
  }
  return snapshot;
}

function versionSummary(data: ProjectData): Record<string, unknown> {
  const sceneCount = data.timeline?.filter((scene) => !scene.excludeFromFinal).length || 0;
  const captionCount = (data.timeline || []).reduce((count, scene) => count + (scene.layers || []).filter((layer) => layer.type === "caption" || layer.type === "captions" || layer.type === "text").length, 0);
  return {
    duration: totalTimelineDuration(data),
    sceneCount,
    captionCount,
    style: data.stylePreset || data.exportPreset || data.project?.exportPreset || "custom"
  };
}

function round(value: number) {
  return Number(value.toFixed(3));
}

function snapValue(value: number, snapSeconds: number) {
  return Number((Math.round(value / snapSeconds) * snapSeconds).toFixed(3));
}
