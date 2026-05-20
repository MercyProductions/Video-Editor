import Editor, { OnMount } from "@monaco-editor/react";
import {
  Bell,
  Bot,
  Captions,
  CheckCircle2,
  ChevronDown,
  Clock,
  CircleHelp,
  Download,
  Eye,
  FileJson,
  FileText,
  FolderOpen,
  Image,
  Import,
  Keyboard,
  LayoutTemplate,
  ListVideo,
  Maximize2,
  Mic,
  MonitorPlay,
  MoreVertical,
  Music,
  Pause,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  RefreshCcw,
  Redo2,
  Save,
  Scissors,
  Search,
  Settings,
  Sparkles,
  Trash2,
  Undo2,
  Video,
  Wand2,
  X,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import {
  addAssetLayerToScene,
  addAssetToFirstScene,
  addImportedAssets,
  addPreviewReviewMarker,
  addPreviewReviewNote,
  addScene,
  applyPreviewPauseEdit,
  blankProject,
  collectLayerTypes,
  comparePreviewVersions,
  explainProject,
  formatProject,
  parseProject,
  PauseEditPatch,
  PreviewMarkerType,
  PreviewRegenerateAction,
  PreviewReviewMarker,
  previewExportReadiness,
  LayerData,
  ProjectData,
  regeneratePreviewSection,
  restorePreviewVersion,
  savePreviewVersion,
  SceneData,
  sceneAtTime,
  setSceneReviewStatus,
  suggestBetterTransitions,
  totalTimelineDuration,
  updateSceneTimingAdvanced
} from "./lib/project";

type Tab =
  | "home"
  | "editor"
  | "aiStudio"
  | "captionsMode"
  | "templatesMode"
  | "reviewMode"
  | "exportMode"
  | "diagnostics"
  | "beginner"
  | "json"
  | "timeline"
  | "preview"
  | "assets"
  | "director"
  | "storyboard"
  | "workflow"
  | "product";

type TimelineTrackId = "main" | "audio" | "captions" | "broll" | "graphics" | "effects" | "ai";

type TimelineTrackState = Record<TimelineTrackId, {
  locked: boolean;
  hidden: boolean;
  muted?: boolean;
  solo?: boolean;
}>;
type AppModal =
  | "import"
  | "ai"
  | "aiReview"
  | "templates"
  | "templateCustomizer"
  | "captionStyle"
  | "export"
  | "renderProgress"
  | "errorRecovery"
  | "recoveryPrompt"
  | "versionCompare"
  | "onboarding"
  | "shortcuts"
  | "workspace"
  | "settings"
  | "help"
  | "json"
  | "logs"
  | null;
type FinalReviewStatus = "pending" | "approved" | "needs_changes";
type FinalReviewCheck = {
  id: string;
  title: string;
  detail: string;
  severity: "pass" | "info" | "warning" | "error";
  category: string;
  suggestion?: string;
  sceneId?: string;
  time?: number;
};
type RenderJob = {
  runId: string;
  label: string;
  outputPath: string;
  status: "running" | "complete" | "failed";
  logs: string[];
};
type GenerationReviewState = {
  planPath: string | null;
  hook: string;
  style: string;
  tone: string;
  duration: number | null;
  readyForFinalRender: boolean;
  unresolved: string[];
  warnings: string[];
  scenes: Array<{ key: string; label: string; caption?: string; status?: string }>;
  reasoning?: string;
};
type PendingAiPlan = {
  source: "quick" | "prompt" | "youtubeShort" | "content" | "director" | "template";
  title: string;
  prompt: string;
  text: string;
  path: string | null;
  data: Record<string, unknown>;
  review: GenerationReviewState;
  preset: string;
  form?: BeginnerFormState;
  renderQuality?: "preview" | "final";
};
type WorkflowContext = {
  breadcrumbs: string[];
  title: string;
  description: string;
  meta: string[];
};
type BeginnerTemplateCard = {
  key: string;
  name: string;
  aspectRatio: string;
  platform: string;
  pacing: string;
  captionStyle: string;
};
type TemplateCustomizerState = {
  key: string;
  name: string;
  platform: string;
  duration: number;
  captionStyle: string;
  pacing: string;
  transitionStyle: string;
  musicIntensity: string;
  introOutroStyle: string;
  applyBranding: boolean;
  source: "beginner" | "json";
};
type BeginnerFormState = {
  quickPrompt: string;
  mediaFile: string | null;
  imageFolder: string | null;
  assetFolder: string | null;
  musicPath: string | null;
  logoPath: string | null;
  template: string;
  targetPlatform: string;
  productName: string;
  goal: string;
  keyFeatures: string;
  vibe: string;
  duration: number;
};
type QuickCreateState = {
  mediaFile: string | null;
  platform: string;
  style: string;
  prompt: string;
};
type BeginnerSmartDefaults = {
  aspectRatio: string;
  resolution: string;
  fps: number;
  exportPreset: string;
  pacing: string;
  captionSize: number;
  transitionIntensity: number;
  audioNormalization: string;
};
type FrictionReport = {
  eventCount: number;
  slowOperations: number;
  failedOperations: number;
  repeatedSettings: number;
  recent: Array<Record<string, unknown>>;
  topLabels: Array<{ label: string; count: number }>;
};
type ActivityKind = "info" | "success" | "warning" | "error";
type ProcessingActivity = {
  id: string;
  time: string;
  label: string;
  detail?: string;
  kind: ActivityKind;
};
type ProcessingWorker = {
  name: string;
  status: "idle" | "queued" | "running" | "complete" | "blocked";
  progress?: number;
};
type ProcessingState = {
  isActive: boolean;
  currentStage: string;
  activeTask: string;
  progress: number;
  etaSeconds?: number;
  currentAsset?: string;
  currentScene?: string;
  startedAt?: number;
  reasoning: string[];
  workers: ProcessingWorker[];
};
type ManagedTaskKind =
  | "ai_analysis"
  | "caption_generation"
  | "audio_transcription"
  | "render_export"
  | "thumbnail_generation"
  | "media_import"
  | "proxy_generation"
  | "url_download"
  | "project_io"
  | "diagnostics";
type ManagedTaskStatus = "queued" | "running" | "paused" | "completed" | "failed" | "canceled" | "warning";
type ManagedTask = {
  id: string;
  kind: ManagedTaskKind;
  label: string;
  stage: string;
  status: ManagedTaskStatus;
  progress: number;
  etaSeconds?: number;
  currentAsset?: string;
  currentScene?: string;
  cpuPercent?: number;
  gpuPercent?: number;
  warnings?: string[];
  errors?: string[];
  canPause?: boolean;
  canResume?: boolean;
  canCancel?: boolean;
  runId?: string;
  detail?: string;
  startedAt: number;
  updatedAt: number;
  completedAt?: number;
};
type NotificationKind = "info" | "success" | "warning" | "error";
type NotificationAction = "renderProgress" | "aiReview" | "captions" | "assets" | "export" | "settings" | "diagnostics";
type AppNotification = {
  id: string;
  title: string;
  message: string;
  kind: NotificationKind;
  time: string;
  read: boolean;
  action?: NotificationAction;
  detail?: string;
};
type SystemMetrics = {
  cpuPercent: number;
  gpuPercent: number;
  memoryUsedMb: number;
  memoryTotalMb: number;
  gpuProcessActive: boolean;
  gpuMode: string;
  sampledAt: number;
};
type CollaborationMessage = {
  role: "user" | "assistant";
  text: string;
  time: string;
};
type CollaborationSceneAction = "approve" | "reject" | "regenerate" | "lock" | "skip" | "faster" | "slower";
type ProactiveSuggestion = {
  id: string;
  category: "workflow" | "issue" | "optimization" | "opportunity" | "coaching";
  severity: "info" | "warning" | "critical";
  title: string;
  detail: string;
  action: string;
  command?: string;
  sceneId?: string;
  time?: number;
  duration?: number;
};
type BackgroundImprovement = {
  id: string;
  type: "alternate_hook" | "alternate_caption" | "thumbnail_candidate" | "pacing_improvement";
  title: string;
  detail: string;
  sceneId?: string;
  time?: number;
  text?: string;
};
type ProactiveAnalysis = {
  suggestions: ProactiveSuggestion[];
  issues: ProactiveSuggestion[];
  optimizations: ProactiveSuggestion[];
  opportunities: ProactiveSuggestion[];
  coaching: ProactiveSuggestion[];
  summary: {
    pacingScore: number;
    readabilityScore: number;
    opportunityCount: number;
    warningCount: number;
  };
};
type SceneThumbnail = {
  sceneId: string;
  start: number;
  duration: number;
  frame: string;
};
type InteractivePreviewState = {
  previewVideo?: string;
  sceneThumbnails?: SceneThumbnail[];
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
type FinalPreflightIssue = {
  id: string;
  category: string;
  severity: string;
  message: string;
  scene?: string | null;
  asset?: string | null;
  accepted?: boolean;
  blocking?: boolean;
  safeAutoFix?: boolean;
  autoFix?: { type?: string; label?: string } | null;
  suggestion?: string;
};
type FinalPreflightReport = {
  ready?: boolean;
  exportReadinessScore?: number;
  blockingCount?: number;
  warningsRemaining?: number;
  issueCount?: number;
  issues?: FinalPreflightIssue[];
  scores?: Record<string, number>;
  summary?: Record<string, unknown>;
};
type ExportWarning = {
  id: string;
  title: string;
  message: string;
  suggestion: string;
  severity: "error" | "warning" | "info";
};
type CaptionWorkflowEntry = {
  id: string;
  sceneId: string;
  sceneIndex: number;
  layerIndex: number;
  itemIndex: number | null;
  type: string;
  text: string;
  localStart: number;
  absoluteStart: number;
  duration: number;
  layer: LayerData;
};
type MonacoInstance = Parameters<OnMount>[1];

const templateLabels: Record<string, string> = {
  youtube_intro: "YouTube Intro",
  tiktok_reels_short: "TikTok/Reels",
  gaming_montage: "Gaming Montage",
  product_promo: "Product Promo",
  lyric_video: "Lyric Video",
  slideshow: "Slideshow",
  meme_edit: "Meme Edit",
  tutorial_video: "Tutorial"
};

const defaultUiSettings: AppSettings = {
  theme: "aegis",
  autosave: true,
  autosaveIntervalSeconds: 120,
  previewTimeSeconds: 1,
  keyboardShortcuts: true,
  onboardingComplete: false,
  defaultWorkflow: "quick",
  defaultPlatform: "youtube_shorts",
  defaultStyle: "cinematic",
  defaultExportFolder: null,
  beginnerTips: true,
  workspacePreset: "editing",
  panelDock: "standard",
  uiScale: "medium",
  accentColor: "#6db5a5",
  leftRailWidth: 260,
  rightRailWidth: 360,
  leftRailOpen: true,
  rightRailOpen: true,
  monitorPositions: {}
};

const beginnerTemplates: BeginnerTemplateCard[] = [
  { key: "premium_product_showcase", name: "Premium Product Showcase", aspectRatio: "16:9", platform: "youtube", pacing: "Smooth feature reveals", captionStyle: "Polished lower thirds" },
  { key: "youtube_short", name: "YouTube Short", aspectRatio: "9:16", platform: "shorts", pacing: "Fast hook-body-payoff", captionStyle: "Large captions" },
  { key: "tiktok_reels_edit", name: "TikTok/Reels Edit", aspectRatio: "9:16", platform: "tiktok", pacing: "Trend-fast cuts", captionStyle: "Punchy captions" },
  { key: "software_demo", name: "Software Demo", aspectRatio: "16:9", platform: "youtube", pacing: "Readable walkthrough", captionStyle: "Quiet UI captions" },
  { key: "cybersecurity_tool_showcase", name: "Cybersecurity Tool Showcase", aspectRatio: "9:16", platform: "shorts", pacing: "Premium risk-to-result", captionStyle: "Bold red/white captions" },
  { key: "gaming_montage", name: "Gaming Montage", aspectRatio: "9:16", platform: "shorts", pacing: "High-energy highlights", captionStyle: "Short hype captions" },
  { key: "tutorial_walkthrough", name: "Tutorial Walkthrough", aspectRatio: "16:9", platform: "youtube", pacing: "Step-by-step", captionStyle: "Safe readable captions" },
  { key: "minimal_saas_promo", name: "Minimal SaaS Promo", aspectRatio: "16:9", platform: "youtube", pacing: "Restrained problem/solution", captionStyle: "Small premium captions" },
  { key: "cinematic_trailer", name: "Cinematic Trailer", aspectRatio: "16:9", platform: "youtube", pacing: "Slow build and payoff", captionStyle: "Cinematic title captions" },
  { key: "before_after_reveal", name: "Before/After Reveal", aspectRatio: "9:16", platform: "shorts", pacing: "Problem-first reveal", captionStyle: "Before/after highlights" }
];

const defaultBeginnerForm: BeginnerFormState = {
  quickPrompt: "Create a premium red/black cinematic showcase for my automatic troubleshooter. Show runtime scans, anti-cheat conflicts, Windows security settings, and launch blockers in under 30 seconds.",
  mediaFile: null,
  imageFolder: null,
  assetFolder: null,
  musicPath: null,
  logoPath: null,
  template: "premium_product_showcase",
  targetPlatform: "youtube",
  productName: "Automatic Troubleshooter",
  goal: "Show how it scans launch blockers and fixes common setup problems.",
  keyFeatures: "Missing runtimes\nAnti-cheat conflicts\nWindows security settings\nLaunch blockers",
  vibe: "premium red black cinematic",
  duration: 30
};

const defaultQuickCreate: QuickCreateState = {
  mediaFile: null,
  platform: "shorts",
  style: "cinematic",
  prompt: "Make this into a YouTube Short."
};

function templateNameFromKey(templateKey: string) {
  return beginnerTemplates.find((template) => template.key === templateKey)?.name || templateKey.replace(/_/g, " ");
}

function presetForOnboardingPlatform(platform: string) {
  const value = platform.toLowerCase();
  if (value.includes("tiktok")) return "tiktok_reels";
  if (value.includes("reel") || value.includes("instagram")) return "instagram_reels";
  if (value.includes("short")) return "shorts";
  return "youtube_1080p";
}

function outputPathFromDefaultFolder(folder: string | null | undefined, projectTitle: string, quality: "preview" | "final", format: string) {
  if (!folder) return null;
  const cleanFolder = folder.replace(/[\\/]+$/, "");
  if (!cleanFolder) return null;
  const sep = cleanFolder.includes("\\") ? "\\" : "/";
  const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
  const baseName = `${projectTitle || "automatic-video"}-${quality}-${stamp}`.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 72) || `automatic-video-${quality}`;
  return `${cleanFolder}${sep}${baseName}.${format || "mp4"}`;
}

function templateCustomizerFromKey(templateKey: string, jsonTemplates: string[] = []): TemplateCustomizerState {
  const beginner = beginnerTemplates.find((template) => template.key === templateKey);
  if (beginner) {
    const defaults = templateQuickDefaults(beginner.key, beginner.platform);
    return {
      key: beginner.key,
      name: beginner.name,
      platform: normalizeTemplatePlatform(beginner.platform),
      duration: defaults.duration,
      captionStyle: beginner.captionStyle,
      pacing: beginner.pacing,
      transitionStyle: inferTemplateTransition(beginner),
      musicIntensity: inferTemplateMusicIntensity(beginner),
      introOutroStyle: inferTemplateIntroOutro(beginner),
      applyBranding: /product|promo|saas|cyber|trailer/i.test(beginner.name),
      source: "beginner"
    };
  }
  const fallbackKey = jsonTemplates.includes(templateKey) ? templateKey : templateKey;
  return {
    key: fallbackKey,
    name: templateLabels[fallbackKey] || friendlyPresetName(fallbackKey),
    platform: "youtube",
    duration: templateKey === "tiktok_reels_short" ? 24 : templateKey === "youtube_intro" ? 8 : 30,
    captionStyle: /lyric|tutorial|meme/i.test(templateKey) ? "Large readable captions" : "Clean lower thirds",
    pacing: /gaming|meme|tiktok/i.test(templateKey) ? "Fast cuts" : "Balanced",
    transitionStyle: /gaming|meme/i.test(templateKey) ? "flash cuts" : "crossfade",
    musicIntensity: /gaming|meme|tiktok/i.test(templateKey) ? "high" : "medium",
    introOutroStyle: /intro/i.test(templateKey) ? "logo reveal" : "title card + CTA",
    applyBranding: /product|intro|tutorial/i.test(templateKey),
    source: "json"
  };
}

function formFromTemplateCustomizer(customizer: TemplateCustomizerState, current: BeginnerFormState): BeginnerFormState {
  const beginner = beginnerTemplates.find((template) => template.key === customizer.key);
  const goal = current.goal.trim() || `Create a polished ${customizer.name} video.`;
  const details = [
    current.vibe,
    customizer.captionStyle,
    customizer.pacing,
    customizer.transitionStyle,
    `${customizer.musicIntensity} music`,
    customizer.introOutroStyle,
    customizer.applyBranding ? "with branding/logo" : ""
  ].filter(Boolean).join(" ");
  return {
    ...current,
    template: beginner?.key || customizer.key,
    targetPlatform: customizer.platform,
    duration: customizer.duration,
    vibe: details,
    goal,
    quickPrompt: current.quickPrompt.trim() || `${goal} Use ${customizer.name}, ${details}, and keep the edit reviewable before applying.`
  };
}

function templatePreviewSummary(customizer: TemplateCustomizerState) {
  return [
    `${customizer.name} is staged as a review-first template.`,
    `Platform: ${templatePlatformLabel(customizer.platform)}.`,
    `Duration: about ${customizer.duration}s.`,
    `Captions: ${customizer.captionStyle}.`,
    `Pacing: ${customizer.pacing}.`,
    `Transitions: ${customizer.transitionStyle}.`,
    `Music intensity: ${customizer.musicIntensity}.`,
    "Applying this template will generate a Template Plan Review before the timeline changes."
  ].join("\n");
}

function normalizeTemplatePlatform(platform: string) {
  const value = platform.toLowerCase();
  if (value.includes("short")) return "shorts";
  if (value.includes("tiktok")) return "tiktok";
  if (value.includes("reel") || value.includes("instagram")) return "instagram_reels";
  if (value.includes("square")) return "square";
  return "youtube";
}

function templatePlatformLabel(platform: string) {
  const labels: Record<string, string> = {
    shorts: "YouTube Shorts",
    tiktok: "TikTok",
    instagram_reels: "Instagram Reels",
    youtube: "YouTube normal video",
    square: "Square social"
  };
  return labels[platform] || friendlyPresetName(platform);
}

function inferTemplateTransition(template: BeginnerTemplateCard) {
  const value = `${template.name} ${template.pacing}`.toLowerCase();
  if (/gaming|hype|trend|tiktok/.test(value)) return "fast cuts";
  if (/cinematic|premium|trailer|product/.test(value)) return "smooth cinematic";
  if (/tutorial|educational|walkthrough/.test(value)) return "clean cuts";
  return "crossfade";
}

function inferTemplateMusicIntensity(template: BeginnerTemplateCard) {
  const value = `${template.name} ${template.pacing}`.toLowerCase();
  if (/gaming|hype|tiktok|trend/.test(value)) return "high";
  if (/tutorial|educational|podcast|minimal/.test(value)) return "low";
  return "medium";
}

function inferTemplateIntroOutro(template: BeginnerTemplateCard) {
  const value = template.name.toLowerCase();
  if (/product|promo|saas|cyber/.test(value)) return "logo reveal + CTA";
  if (/tutorial|walkthrough|educational/.test(value)) return "step title + recap";
  if (/gaming|short|tiktok/.test(value)) return "hook title + quick CTA";
  return "cinematic title + fadeout";
}

function categoryForTemplate(name: string) {
  const value = name.toLowerCase();
  if (/short|youtube intro/.test(value)) return "YouTube Shorts";
  if (/tiktok/.test(value)) return "TikTok";
  if (/reel|instagram/.test(value)) return "Instagram Reels";
  if (/gaming/.test(value)) return "Gaming Clips";
  if (/podcast/.test(value)) return "Podcast Clips";
  if (/educational|education/.test(value)) return "Educational";
  if (/product|promo|saas|cyber/.test(value)) return "Product Promo";
  if (/cinematic|trailer/.test(value)) return "Cinematic";
  if (/meme|reaction/.test(value)) return "Meme / Reaction";
  if (/tutorial|walkthrough/.test(value)) return "Tutorial";
  return "Product Promo";
}

function requiredMediaForTemplate(name: string) {
  const value = name.toLowerCase();
  if (/slideshow/.test(value)) return "image folder";
  if (/lyric|podcast/.test(value)) return "audio";
  if (/product|promo|saas|cyber/.test(value)) return "video + logo optional";
  if (/gaming|meme|reaction|short|tiktok|reel/.test(value)) return "video";
  if (/tutorial|educational|walkthrough/.test(value)) return "screen recording";
  return "video or images";
}

function friendlyPresetName(presetValue: string) {
  return presetValue
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function workspacePresetSettings(settings: AppSettings, preset: WorkspacePreset): AppSettings {
  const base = { ...settings, workspacePreset: preset };
  const presets: Record<WorkspacePreset, Partial<AppSettings>> = {
    beginner: { panelDock: "preview_focus", leftRailWidth: 248, rightRailWidth: 300, leftRailOpen: false, rightRailOpen: false, uiScale: "large" },
    ai: { panelDock: "standard", leftRailWidth: 270, rightRailWidth: 390, leftRailOpen: true, rightRailOpen: true, uiScale: "medium" },
    editing: { panelDock: "standard", leftRailWidth: 280, rightRailWidth: 370, leftRailOpen: true, rightRailOpen: true, uiScale: "medium" },
    captions: { panelDock: "standard", leftRailWidth: 250, rightRailWidth: 410, leftRailOpen: true, rightRailOpen: true, uiScale: "medium" },
    export: { panelDock: "preview_focus", leftRailWidth: 230, rightRailWidth: 420, leftRailOpen: false, rightRailOpen: true, uiScale: "medium" },
    minimal: { panelDock: "preview_focus", leftRailWidth: 220, rightRailWidth: 300, leftRailOpen: false, rightRailOpen: false, uiScale: "small" }
  };
  return { ...base, ...presets[preset] };
}

function tabForWorkspacePreset(preset: WorkspacePreset): Tab {
  if (preset === "beginner") return "beginner";
  if (preset === "ai") return "aiStudio";
  if (preset === "captions") return "captionsMode";
  if (preset === "export") return "exportMode";
  return "editor";
}

function workflowContextFor({
  activeTab,
  project,
  projectTitle,
  projectPath,
  preset,
  exportFormat,
  generationReview,
  previewSceneId,
  beginnerForm,
  preflightBlockingCount,
  preflightWarningCount
}: {
  activeTab: Tab;
  project: ProjectData | null;
  projectTitle: string;
  projectPath: string | null;
  preset: string;
  exportFormat: string;
  generationReview: GenerationReviewState | null;
  previewSceneId: string;
  beginnerForm: BeginnerFormState;
  preflightBlockingCount: number;
  preflightWarningCount: number;
}): WorkflowContext {
  const resolution = project?.project ? `${project.project.width}x${project.project.height}` : "No project loaded";
  const duration = project ? `${totalTimelineDuration(project).toFixed(1)}s` : "0.0s";
  const sceneCount = `${project?.timeline?.length || 0} scenes`;
  const assetCount = `${Object.keys(project?.assets || {}).length} assets`;
  const sourceState = projectPath ? "Saved project" : "Unsaved project";

  switch (activeTab) {
    case "home":
      return {
        breadcrumbs: ["Project Hub", projectPath ? "Recent Project" : "New Project"],
        title: "Project Hub",
        description: "Start, open, import, or hand the first move to AI from one clean launch point.",
        meta: [sourceState, projectTitle]
      };
    case "editor":
      return {
        breadcrumbs: ["Editor", previewSceneId ? `Scene ${previewSceneId}` : "Timeline"],
        title: "Editor Workspace",
        description: "Preview the generated edit, adjust timing, and keep the timeline visible while you work.",
        meta: [resolution, duration, sceneCount]
      };
    case "preview":
      return {
        breadcrumbs: ["Editor", "Preview"],
        title: "Interactive Preview",
        description: "Review playback, scrub scenes, and check the edit before committing to final export.",
        meta: [resolution, duration, preset]
      };
    case "timeline":
      return {
        breadcrumbs: ["Editor", "Timeline"],
        title: "Timeline",
        description: "Inspect scenes, tracks, captions, transitions, and timing from the JSON-backed edit.",
        meta: [sceneCount, duration, `${project?.project?.fps || "?"} fps`]
      };
    case "assets":
      return {
        breadcrumbs: ["Editor", "Media Bin"],
        title: "Media Bin",
        description: "Review imported videos, images, audio, generated assets, and missing media warnings.",
        meta: [assetCount, sourceState]
      };
    case "aiStudio":
      return {
        breadcrumbs: ["AI Studio", generationReview ? "Generated Plan" : "Prompt"],
        title: generationReview ? "Generated Plan" : "AI Studio",
        description: generationReview
          ? "Review the hook, script, scenes, captions, and reasoning before applying changes."
          : "Generate or improve an edit plan while keeping the project JSON as the source of truth.",
        meta: [generationReview ? `${generationReview.scenes.length} proposed scenes` : "Ready for prompt", generationReview?.style || "Style selectable"]
      };
    case "director":
      return {
        breadcrumbs: ["AI Studio", "Director"],
        title: "AI Director",
        description: "Ask for pacing, captions, transitions, or scene improvements with explainable changes.",
        meta: [sceneCount, duration]
      };
    case "storyboard":
      return {
        breadcrumbs: ["AI Studio", "Storyboard"],
        title: "Storyboard",
        description: "Review scene summaries, thumbnails, timing, and transition intent before rendering.",
        meta: [sceneCount, duration]
      };
    case "captionsMode":
      return {
        breadcrumbs: ["Captions", "Subtitle Timing"],
        title: "Captions",
        description: "Generate, style, and review captions for readability and platform-safe placement.",
        meta: [sceneCount, duration]
      };
    case "templatesMode":
      return {
        breadcrumbs: ["Templates", "Template Picker"],
        title: "Templates",
        description: "Choose a focused starting point for Shorts, TikTok, tutorials, product promos, and more.",
        meta: ["Beginner-safe presets", "JSON templates"]
      };
    case "beginner":
      return {
        breadcrumbs: ["Templates", templateNameFromKey(beginnerForm.template)],
        title: "Beginner Auto Video",
        description: "Use media, a template, and simple product details to generate the JSON edit behind the scenes.",
        meta: [beginnerForm.targetPlatform, `${beginnerForm.duration}s`, beginnerForm.vibe || "Default vibe"]
      };
    case "reviewMode":
      return {
        breadcrumbs: ["Review", "Final Cut"],
        title: "Final Review",
        description: "Watch the final cut, run quality checks, leave timestamped notes, and approve the edit before export.",
        meta: [duration, preflightBlockingCount ? `${preflightBlockingCount} blocking issues` : `${preflightWarningCount} warnings`, preset]
      };
    case "exportMode":
      return {
        breadcrumbs: ["Export", `${friendlyPresetName(preset)} ${resolution}`],
        title: "Export",
        description: "Run preflight, render preview or final output, and package the video for upload.",
        meta: [exportFormat.toUpperCase(), duration, preflightBlockingCount ? `${preflightBlockingCount} blocking issues` : `${preflightWarningCount} warnings`]
      };
    case "product":
      return {
        breadcrumbs: ["Export", "Delivery Package"],
        title: "Product Delivery",
        description: "Create posting packages, variants, repurposed versions, thumbnails, and reusable settings.",
        meta: [exportFormat.toUpperCase(), preset, duration]
      };
    case "diagnostics":
      return {
        breadcrumbs: ["Logs / Diagnostics", "Render Logs"],
        title: "Logs / Diagnostics",
        description: "Inspect AI activity, render logs, JSON, recovery tools, and technical details without crowding editing.",
        meta: [sceneCount, assetCount]
      };
    case "json":
      return {
        breadcrumbs: ["Logs / Diagnostics", "JSON Timeline Viewer"],
        title: "Timeline JSON",
        description: "Advanced view for editing the project source directly.",
        meta: [sourceState, sceneCount]
      };
    case "workflow":
      return {
        breadcrumbs: ["Logs / Diagnostics", "Workflow Tools"],
        title: "Workflow Automation",
        description: "Review local production workflow helpers, profiles, automation hooks, and reuse tools.",
        meta: [sourceState, duration]
      };
    default:
      return {
        breadcrumbs: ["Editor", "Workspace"],
        title: "Workspace",
        description: "Use the focused workflow tabs to move through editing, AI, captions, templates, export, and diagnostics.",
        meta: [resolution, duration]
      };
  }
}

const idleProcessingState: ProcessingState = {
  isActive: false,
  currentStage: "Idle",
  activeTask: "Ready",
  progress: 0,
  reasoning: [],
  workers: []
};

const emptyProactiveAnalysis: ProactiveAnalysis = {
  suggestions: [],
  issues: [],
  optimizations: [],
  opportunities: [],
  coaching: [],
  summary: {
    pacingScore: 100,
    readabilityScore: 100,
    opportunityCount: 0,
    warningCount: 0
  }
};

function App() {
  const [engine, setEngine] = useState<EngineInfo | null>(null);
  const [projectText, setProjectText] = useState(() => formatProject(blankProject()));
  const [projectPath, setProjectPath] = useState<string | null>(null);
  const [recent, setRecent] = useState<RecentProject[]>([]);
  const [uiMode, setUiMode] = useState<"beginner" | "advanced">("advanced");
  const [activeTab, setActiveTab] = useState<Tab>("home");
  const [status, setStatus] = useState("Ready");
  const [validation, setValidation] = useState<EngineResult | null>(null);
  const [assets, setAssets] = useState<AssetCheck[]>([]);
  const [prompt, setPrompt] = useState("Create a 20 second gaming montage with fast cuts, red black theme, captions, and bass drop transitions.");
  const [contentMode, setContentMode] = useState("youtube_shorts");
  const [contentTone, setContentTone] = useState("cinematic");
  const [generationReview, setGenerationReview] = useState<GenerationReviewState | null>(null);
  const [pendingAiPlan, setPendingAiPlan] = useState<PendingAiPlan | null>(null);
  const [generationPlanPath, setGenerationPlanPath] = useState<string | null>(null);
  const [generationLocks, setGenerationLocks] = useState<string[]>([]);
  const [directorGoal, setDirectorGoal] = useState("Make this feel like a fast gaming montage");
  const [aiNotes, setAiNotes] = useState("");
  const [directorReport, setDirectorReport] = useState<Record<string, unknown> | null>(null);
  const [storyboard, setStoryboard] = useState<Record<string, unknown> | null>(null);
  const [assetReport, setAssetReport] = useState<Record<string, unknown> | null>(null);
  const [history, setHistory] = useState<HistoryVersion[]>([]);
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [renderQueueItems, setRenderQueueItems] = useState<RenderQueueItem[]>([]);
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const [renderJobs, setRenderJobs] = useState<RenderJob[]>([]);
  const [renderLogs, setRenderLogs] = useState<string[]>([]);
  const [preset, setPreset] = useState("youtube_1080p");
  const [exportFormat, setExportFormat] = useState<"mp4" | "mov" | "mkv" | "webm" | "gif">("mp4");
  const [quality, setQuality] = useState<"preview" | "final">("preview");
  const [useCache, setUseCache] = useState(true);
  const [resume, setResume] = useState(false);
  const [gpu, setGpu] = useState(false);
  const [settings, setSettings] = useState<AppSettings>(defaultUiSettings);
  const [appError, setAppError] = useState("");
  const [realtimePreview, setRealtimePreview] = useState<Record<string, unknown> | null>(null);
  const [interactivePreview, setInteractivePreview] = useState<InteractivePreviewState | null>(null);
  const [previewTimeSeconds, setPreviewTimeSeconds] = useState(defaultUiSettings.previewTimeSeconds);
  const [previewSceneId, setPreviewSceneId] = useState("");
  const [previewQualityMode, setPreviewQualityMode] = useState("balanced");
  const [previewLayerMode, setPreviewLayerMode] = useState("all");
  const [previewScope, setPreviewScope] = useState<"full" | "scene">("full");
  const [qualityReport, setQualityReport] = useState<Record<string, unknown> | null>(null);
  const [finalPreflightReport, setFinalPreflightReport] = useState<FinalPreflightReport | null>(null);
  const [finalReviewStatus, setFinalReviewStatus] = useState<FinalReviewStatus>("pending");
  const [watchFinalCutOpen, setWatchFinalCutOpen] = useState(false);
  const [manifestReport, setManifestReport] = useState<Record<string, unknown> | null>(null);
  const [repurposeReport, setRepurposeReport] = useState<Record<string, unknown> | null>(null);
  const [postingPackageReport, setPostingPackageReport] = useState<Record<string, unknown> | null>(null);
  const [postExportReview, setPostExportReview] = useState<Record<string, unknown> | null>(null);
  const [postExportTemplate, setPostExportTemplate] = useState<Record<string, unknown> | null>(null);
  const [postExportVariants, setPostExportVariants] = useState<Record<string, unknown> | null>(null);
  const [postExportNote, setPostExportNote] = useState<Record<string, unknown> | null>(null);
  const [templatePacks, setTemplatePacks] = useState<TemplatePack[]>([]);
  const [recoveryPoints, setRecoveryPoints] = useState<RecoveryPoint[]>([]);
  const [startupRecovery, setStartupRecovery] = useState<StartupRecoveryState | null>(null);
  const [projectHealth, setProjectHealth] = useState<ProjectHealthReport | null>(null);
  const [versionComparison, setVersionComparison] = useState<VersionComparison | null>(null);
  const [socialTargets, setSocialTargets] = useState(["youtube_shorts", "tiktok", "instagram_reels", "youtube_landscape", "discord", "x_twitter"]);
  const [hardeningStatus, setHardeningStatus] = useState<HardeningStatus | null>(null);
  const [workflowDashboard, setWorkflowDashboard] = useState<Record<string, unknown> | null>(null);
  const [feedbackAnalysis, setFeedbackAnalysis] = useState<Record<string, unknown> | null>(null);
  const [feedbackReview, setFeedbackReview] = useState<Record<string, unknown> | null>(null);
  const [creatorIdentity, setCreatorIdentity] = useState<Record<string, unknown> | null>(null);
  const [evolutionReport, setEvolutionReport] = useState<Record<string, unknown> | null>(null);
  const [beginnerForm, setBeginnerForm] = useState<BeginnerFormState>(defaultBeginnerForm);
  const [quickCreate, setQuickCreate] = useState<QuickCreateState>(defaultQuickCreate);
  const [guidedStep, setGuidedStep] = useState(1);
  const [beginnerSummary, setBeginnerSummary] = useState<Record<string, unknown> | null>(null);
  const [frictionReport, setFrictionReport] = useState<FrictionReport | null>(null);
  const [adaptiveMemory, setAdaptiveMemory] = useState<AdaptiveWorkflowMemory | null>(null);
  const [processing, setProcessing] = useState<ProcessingState>(idleProcessingState);
  const [localTasks, setLocalTasks] = useState<ManagedTask[]>([]);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [notificationCenterOpen, setNotificationCenterOpen] = useState(false);
  const [activityFeed, setActivityFeed] = useState<ProcessingActivity[]>([]);
  const [processingCollapsed, setProcessingCollapsed] = useState(true);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [renderActivityMinimized, setRenderActivityMinimized] = useState(false);
  const [assistantDraft, setAssistantDraft] = useState("");
  const [assistantMessages, setAssistantMessages] = useState<CollaborationMessage[]>([]);
  const [proactiveMuted, setProactiveMuted] = useState(false);
  const [ignoredSuggestedEditIds, setIgnoredSuggestedEditIds] = useState<string[]>([]);
  const [savedSuggestedEdits, setSavedSuggestedEdits] = useState<ProactiveSuggestion[]>([]);
  const [disabledSuggestionTypes, setDisabledSuggestionTypes] = useState<string[]>([]);
  const [leftRailOpen, setLeftRailOpen] = useState(true);
  const [rightRailOpen, setRightRailOpen] = useState(true);
  const [aiPromptBuilderOpen, setAiPromptBuilderOpen] = useState(false);
  const [backgroundImprovements, setBackgroundImprovements] = useState<BackgroundImprovement[]>([]);
  const [appModal, setAppModal] = useState<AppModal>(null);
  const [templateCustomizer, setTemplateCustomizer] = useState<TemplateCustomizerState | null>(null);

  const parsed = useMemo(() => parseProject(projectText), [projectText]);
  const project = parsed.data;
  const proactiveAnalysis = useMemo(
    () => project ? analyzeProactiveAssistance(project, adaptiveMemory, renderQueueItems, preset, useCache) : emptyProactiveAnalysis,
    [project, adaptiveMemory, renderQueueItems, preset, useCache]
  );
  const suggestedEdits = useMemo(
    () => project ? buildSuggestedEdits(project, proactiveAnalysis, assetReport, finalPreflightReport) : [],
    [project, proactiveAnalysis, assetReport, finalPreflightReport]
  );
  const finalReviewChecks = useMemo(
    () => project ? buildFinalReviewChecks(project, assets, assetReport, finalPreflightReport, preset, exportFormat, qualityReport) : [],
    [project, assets, assetReport, finalPreflightReport, preset, exportFormat, qualityReport]
  );
  const managedTasks = useMemo(
    () => buildManagedTasks(localTasks, renderQueueItems, processing, systemMetrics),
    [localTasks, renderQueueItems, processing, systemMetrics]
  );
  const monacoRef = useRef<MonacoInstance | null>(null);
  const latestProjectRef = useRef({ text: projectText, path: projectPath, preset });
  const lastActivityKeyRef = useRef("");
  const lastAutosaveTextRef = useRef("");
  const skippedInitialAutosaveRef = useRef(false);
  const activeManagedTaskIdRef = useRef<string | null>(null);
  const managedTaskCounterRef = useRef(0);
  const missingMediaNotificationRef = useRef("");
  const updateAvailableNotificationRef = useRef(false);

  const configureMonaco = useCallback((monaco: MonacoInstance, schema: Record<string, unknown>) => {
    monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
      validate: true,
      allowComments: false,
      schemas: [
        {
          uri: "https://automatic-video-editor.local/project.schema.json",
          fileMatch: ["*"],
          schema
        }
      ]
    });
  }, []);

  useEffect(() => {
    window.ave.getEngineInfo().then(setEngine);
    window.ave.getRecentProjects().then(setRecent);
    const offLog = window.ave.onRenderLog((event) => {
      setRenderLogs((logs) => [...logs.slice(-300), event.line]);
      setRenderJobs((jobs) =>
        jobs.map((job) => (job.runId === event.runId ? { ...job, logs: [...job.logs.slice(-80), event.line] } : job))
      );
      syncProcessingFromRenderLog(event.line);
    });
    const offComplete = window.ave.onRenderComplete((event) => {
      setPreviewPath(event.outputPath);
      setStatus(event.exitCode === 0 ? (event.packagePath ? `Render complete. Package: ${event.packagePath}` : "Render complete") : "Render failed");
      addNotification(
        event.exitCode === 0 ? "Export finished" : "Render failed",
        event.exitCode === 0 ? (event.packagePath ? `Package ready: ${event.packagePath}` : event.outputPath) : `Check render logs for ${event.runId}.`,
        event.exitCode === 0 ? "success" : "error",
        "renderProgress",
        event.outputPath
      );
      if (event.exitCode !== 0) {
        void window.ave.logFriction({ event: "failed_export", label: event.runId, outputPath: event.outputPath });
      }
      void recordAdaptiveEvent({
        event: event.exitCode === 0 ? "render_success" : "render_failed",
        exportPreset: latestProjectRef.current.preset,
        note: event.outputPath,
        correction: event.exitCode === 0 ? "successful_export" : "export_retry"
      });
      finishProcessing(event.exitCode === 0 ? "Render complete" : "Render failed", event.exitCode === 0 ? "success" : "error");
      setRenderJobs((jobs) =>
        jobs.map((job) => (job.runId === event.runId ? { ...job, status: event.exitCode === 0 ? "complete" : "failed" } : job))
      );
    });
    const offQueue = window.ave.onRenderQueue((items) => {
      setRenderQueueItems(items);
      syncProcessingFromQueue(items);
    });
    window.ave.getRenderQueue().then((items) => {
      setRenderQueueItems(items);
      syncProcessingFromQueue(items);
    });
    window.ave.startupRecovery().then((state) => {
      setStartupRecovery(state);
      if (state.crashed && state.latestRecovery) {
        setRecoveryPoints([state.latestRecovery]);
        setAppModal("recoveryPrompt");
        setStatus("Recover unsaved project?");
      }
    }).catch(() => undefined);
    window.ave.listPlugins().then(setPlugins).catch(() => setPlugins([]));
    window.ave.getSettings().then((value) => {
      setSettings(value);
      setPreviewTimeSeconds(value.previewTimeSeconds);
      applyWorkspaceLayout(value);
      applyOnboardingDefaults(value);
      if (!value.onboardingComplete) setAppModal((current) => current || "onboarding");
    }).catch(() => setSettings(defaultUiSettings));
    window.ave.listTemplatePacks().then(setTemplatePacks).catch(() => setTemplatePacks([]));
    window.ave.getAdaptiveWorkflowMemory({ text: projectText, projectPath, profile: "Default Creator" })
      .then((memory) => {
        setAdaptiveMemory(memory);
        applyAdaptiveDefaults(memory);
      })
      .catch(() => setAdaptiveMemory(null));
    return () => {
      offLog();
      offComplete();
      offQueue();
    };
  }, []);

  useEffect(() => {
    if (!projectText.trim()) return;
    window.ave
      .checkAssets({ text: projectText, projectPath })
      .then(setAssets)
      .catch(() => setAssets([]));
  }, [projectText, projectPath]);

  useEffect(() => {
    const missing = assets.filter((asset) => !asset.exists);
    const signature = missing.map((asset) => `${asset.key}:${asset.path}`).sort().join("|");
    if (!signature || signature === missingMediaNotificationRef.current) return;
    missingMediaNotificationRef.current = signature;
    addNotification(
      "Missing media warning",
      `${missing.length} asset${missing.length === 1 ? "" : "s"} need relinking before final export.`,
      "warning",
      "assets",
      missing.slice(0, 3).map((asset) => asset.key).join(", ")
    );
  }, [assets]);

  useEffect(() => {
    if (engine && monacoRef.current) configureMonaco(monacoRef.current, engine.schema);
  }, [engine, configureMonaco]);

  useEffect(() => {
    if (!projectPath) {
      setHistory([]);
      return;
    }
    window.ave.listHistory({ projectPath }).then(setHistory).catch(() => setHistory([]));
  }, [projectPath]);

  useEffect(() => {
    latestProjectRef.current = { text: projectText, path: projectPath, preset };
  }, [projectText, projectPath, preset]);

  useEffect(() => {
    window.ave.getAdaptiveWorkflowMemory({ text: projectText, projectPath, profile: "Default Creator" })
      .then(setAdaptiveMemory)
      .catch(() => undefined);
  }, [projectPath]);

  useEffect(() => {
    setProcessingCollapsed(true);
  }, [uiMode]);

  useEffect(() => {
    const hasActiveWork = processing.isActive ||
      renderQueueItems.some((item) => item.status === "queued" || item.status === "running") ||
      localTasks.some((task) => task.status === "queued" || task.status === "running" || task.status === "paused");
    if (!hasActiveWork && appModal !== "renderProgress") return;
    let canceled = false;
    const refresh = async () => {
      try {
        const metrics = await window.ave.systemMetrics();
        if (!canceled) setSystemMetrics(metrics);
      } catch {
        if (!canceled) setSystemMetrics(null);
      }
    };
    void refresh();
    const interval = window.setInterval(refresh, 1500);
    return () => {
      canceled = true;
      window.clearInterval(interval);
    };
  }, [processing.isActive, renderQueueItems, localTasks, appModal]);

  useEffect(() => {
    if (!project || processing.isActive || renderQueueItems.some((item) => item.status === "queued" || item.status === "running")) return;
    const timer = window.setTimeout(() => {
      setBackgroundImprovements(buildBackgroundImprovementQueue(project, adaptiveMemory, proactiveAnalysis));
    }, 900);
    return () => window.clearTimeout(timer);
  }, [project, projectText, adaptiveMemory, proactiveAnalysis, processing.isActive, renderQueueItems]);

  useEffect(() => {
    if (!settings.autosave) return;
    const interval = window.setInterval(() => {
      const current = latestProjectRef.current;
      void captureAutosave("autosave", current.text, current.path);
    }, Math.max(10, settings.autosaveIntervalSeconds) * 1000);
    return () => window.clearInterval(interval);
  }, [settings.autosave, settings.autosaveIntervalSeconds]);

  useEffect(() => {
    if (!settings.autosave || !projectText.trim()) return;
    if (!skippedInitialAutosaveRef.current) {
      skippedInitialAutosaveRef.current = true;
      lastAutosaveTextRef.current = projectText;
      return;
    }
    if (projectText === lastAutosaveTextRef.current) return;
    const timer = window.setTimeout(() => {
      void captureAutosave("timeline_change", projectText, projectPath);
    }, 18000);
    return () => window.clearTimeout(timer);
  }, [projectText, projectPath, settings.autosave]);

  useEffect(() => {
    if (!settings.keyboardShortcuts) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) return;
      const key = event.key.toLowerCase();
      if (key === "s") {
        event.preventDefault();
        saveProject();
      } else if (key === "o") {
        event.preventDefault();
        openProject();
      } else if (key === "enter") {
        event.preventDefault();
        render("Preview render", "preview");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  useEffect(() => {
    try {
      window.localStorage.setItem("ave.recovery.session", JSON.stringify({
        updatedAt: new Date().toISOString(),
        projectPath,
        pendingAiPlan,
        generationReview,
        generationPlanPath,
        beginnerForm,
        beginnerSummary,
        preset,
        exportFormat,
        quality,
        previewSceneId,
        previewQualityMode,
        contentMode,
        contentTone
      }));
    } catch {
      // Local UI session recovery is best-effort; autosave files remain the authoritative recovery path.
    }
  }, [projectPath, pendingAiPlan, generationReview, generationPlanPath, beginnerForm, beginnerSummary, preset, exportFormat, quality, previewSceneId, previewQualityMode, contentMode, contentTone]);

  const updateProject = useCallback((data: ProjectData, reason = "timeline_edit") => {
    const nextText = formatProject(data);
    if (nextText !== projectText) void captureAutosave(`before_${safeRecoveryReason(reason)}`, projectText, projectPath);
    setProjectText(nextText);
  }, [projectText, projectPath]);

  const onEditorMount: OnMount = (_editor, monaco) => {
    monacoRef.current = monaco;
    if (engine) configureMonaco(monaco, engine.schema);
  };

  function pushActivity(label: string, kind: ActivityKind = "info", detail?: string) {
    const key = `${kind}:${label}:${detail || ""}`;
    if (lastActivityKeyRef.current === key) return;
    lastActivityKeyRef.current = key;
    const now = new Date();
    setActivityFeed((feed) => [
      {
        id: `${now.getTime()}-${Math.random().toString(16).slice(2)}`,
        time: now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        label,
        detail,
        kind
      },
      ...feed
    ].slice(0, 120));
  }

  function addNotification(title: string, message: string, kind: NotificationKind = "info", action?: NotificationAction, detail?: string) {
    const now = new Date();
    const key = `${title}|${message}|${kind}`;
    setNotifications((items) => {
      if (items[0] && `${items[0].title}|${items[0].message}|${items[0].kind}` === key) return items;
      return [
        {
          id: `${now.getTime()}-${Math.random().toString(16).slice(2)}`,
          title,
          message,
          kind,
          action,
          detail,
          read: false,
          time: now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        },
        ...items
      ].slice(0, 60);
    });
  }

  function markNotificationsRead() {
    setNotifications((items) => items.map((item) => ({ ...item, read: true })));
  }

  function dismissNotification(id: string) {
    setNotifications((items) => items.filter((item) => item.id !== id));
  }

  function clearNotifications() {
    setNotifications([]);
    setNotificationCenterOpen(false);
  }

  function openNotificationAction(action?: NotificationAction) {
    if (!action) return;
    if (action === "renderProgress") setAppModal("renderProgress");
    if (action === "aiReview") setAppModal("aiReview");
    if (action === "captions") {
      setUiMode("advanced");
      setActiveTab("captionsMode");
    }
    if (action === "assets") {
      setUiMode("advanced");
      setActiveTab("assets");
      setRightRailOpen(true);
    }
    if (action === "export") {
      setUiMode("advanced");
      setActiveTab("exportMode");
      setAppModal("export");
    }
    if (action === "settings") setAppModal("settings");
    if (action === "diagnostics") {
      setUiMode("advanced");
      setActiveTab("diagnostics");
    }
    setNotificationCenterOpen(false);
    markNotificationsRead();
  }

  function createManagedTask(kind: ManagedTaskKind, label: string, stage: string, detail?: string) {
    const id = `task-${Date.now()}-${managedTaskCounterRef.current++}`;
    const now = Date.now();
    const task: ManagedTask = {
      id,
      kind,
      label,
      stage,
      detail,
      status: "running",
      progress: 4,
      canCancel: true,
      canPause: false,
      canResume: false,
      startedAt: now,
      updatedAt: now
    };
    activeManagedTaskIdRef.current = id;
    setLocalTasks((tasks) => [task, ...tasks].slice(0, 80));
    return id;
  }

  function updateManagedTask(id: string | null, patch: Partial<ManagedTask>) {
    if (!id) return;
    setLocalTasks((tasks) => tasks.map((task) => task.id === id
      ? updateTaskRecord(task, patch)
      : task
    ));
  }

  function finishManagedTask(id: string | null, statusValue: ManagedTaskStatus, stage: string, warnings: string[] = [], errors: string[] = []) {
    if (!id) return;
    setLocalTasks((tasks) => tasks.map((task) => {
      if (task.id !== id) return task;
      if (task.status === "canceled") return { ...task, completedAt: Date.now(), updatedAt: Date.now() };
      return {
        ...task,
        status: statusValue,
        stage,
        progress: statusValue === "completed" ? 100 : task.progress,
        warnings: [...(task.warnings || []), ...warnings],
        errors: [...(task.errors || []), ...errors],
        canCancel: false,
        canPause: false,
        canResume: false,
        completedAt: Date.now(),
        updatedAt: Date.now()
      };
    }));
    if (activeManagedTaskIdRef.current === id) activeManagedTaskIdRef.current = null;
  }

  async function pauseManagedTask(task: ManagedTask) {
    if (task.runId || task.kind === "render_export") {
      setRenderQueueItems(await window.ave.pauseRenderQueue());
      pushActivity("Render queue paused", "warning", task.label);
      return;
    }
    updateManagedTask(task.id, { status: "paused", stage: "Paused by user", canResume: true, canPause: false });
    pushActivity(`Paused ${task.label}`, "warning");
  }

  async function resumeManagedTask(task: ManagedTask) {
    if (task.runId || task.kind === "render_export") {
      setRenderQueueItems(await window.ave.resumeRenderQueue());
      pushActivity("Render queue resumed", "info", task.label);
      return;
    }
    updateManagedTask(task.id, { status: "running", stage: "Resumed", canResume: false, canPause: false });
    pushActivity(`Resumed ${task.label}`, "info");
  }

  async function cancelManagedTask(task: ManagedTask) {
    if (task.runId) {
      setRenderQueueItems(await window.ave.cancelRenderJob({ runId: task.runId }));
      pushActivity("Canceled render job", "warning", task.label);
      return;
    }
    updateManagedTask(task.id, {
      status: "canceled",
      stage: "Cancel requested",
      canCancel: false,
      canPause: false,
      canResume: false,
      warnings: [...(task.warnings || []), "The current engine call may finish, but this task is no longer treated as active."]
    });
    if (activeManagedTaskIdRef.current === task.id) {
      activeManagedTaskIdRef.current = null;
      setProcessing((current) => ({ ...current, isActive: false, currentStage: "Canceled", activeTask: task.label }));
    }
    pushActivity(`Canceled ${task.label}`, "warning");
  }

  function clearCompletedManagedTasks() {
    setLocalTasks((tasks) => tasks.filter((task) => ["queued", "running", "paused"].includes(task.status)));
    pushActivity("Cleared completed background tasks", "info");
  }

  function beginProcessing(label: string, stage = "Starting", detail?: string) {
    createManagedTask(inferTaskKind(label, stage), label, stage, detail);
    setProcessingCollapsed(uiMode === "beginner");
    setProcessing({
      isActive: true,
      currentStage: stage,
      activeTask: label,
      progress: 4,
      startedAt: Date.now(),
      currentAsset: undefined,
      currentScene: undefined,
      etaSeconds: undefined,
      reasoning: reasoningForAction(label),
      workers: workersForAction(label)
    });
    pushActivity(`${label} started`, "info", detail || stage);
  }

  function updateProcessing(patch: Partial<ProcessingState>, activity?: string, kind: ActivityKind = "info", detail?: string) {
    setProcessing((current) => ({
      ...current,
      ...patch,
      isActive: patch.isActive ?? current.isActive,
      progress: Math.max(current.progress, Number(patch.progress ?? current.progress))
    }));
    updateManagedTask(activeManagedTaskIdRef.current, {
      stage: patch.currentStage || undefined,
      progress: typeof patch.progress === "number" ? patch.progress : undefined,
      etaSeconds: patch.etaSeconds,
      currentAsset: patch.currentAsset,
      currentScene: patch.currentScene,
      status: patch.isActive === false ? "completed" : "running",
      cpuPercent: systemMetrics?.cpuPercent,
      gpuPercent: systemMetrics?.gpuPercent
    });
    if (activity) pushActivity(activity, kind, detail);
  }

  function finishProcessing(label: string, kind: ActivityKind = "success") {
    const taskId = activeManagedTaskIdRef.current;
    setProcessing((current) => ({
      ...current,
      isActive: false,
      currentStage: kind === "success" ? "Complete" : "Needs attention",
      activeTask: label,
      progress: kind === "success" ? 100 : current.progress,
      etaSeconds: kind === "success" ? 0 : current.etaSeconds,
      workers: current.workers.map((worker) => ({ ...worker, status: kind === "success" ? "complete" : worker.status }))
    }));
    finishManagedTask(
      taskId,
      kind === "success" ? "completed" : kind === "error" ? "failed" : "warning",
      kind === "success" ? "Complete" : "Needs attention",
      kind === "warning" ? [label] : [],
      kind === "error" ? [label] : []
    );
    if (kind !== "info") setProcessingCollapsed(true);
    pushActivity(label, kind);
  }

  async function captureAutosave(reason = "autosave", textOverride = projectText, pathOverride = projectPath) {
    if (!textOverride.trim()) return null;
    try {
      const point = await window.ave.autosaveProject({ text: textOverride, projectPath: pathOverride, reason });
      if (point) {
        lastAutosaveTextRef.current = textOverride;
        setRecoveryPoints((points) => [point, ...points.filter((item) => item.path !== point.path)].slice(0, 12));
        pushActivity(`Recovery point saved: ${reason.replace(/_/g, " ")}`, "success", point.timestamp || point.path);
      }
      return point;
    } catch {
      pushActivity("Autosave failed", "warning", reason);
      return null;
    }
  }

  async function recordProjectVersion(name: string, summary: Record<string, unknown>, nextText = projectText, oldText = projectText, pathOverride = projectPath) {
    const version = await window.ave.recordHistory({
      projectPath: pathOverride,
      oldText,
      newText: nextText,
      summary: {
        name,
        summary: name,
        ...summary,
        timestamp: new Date().toISOString(),
        reversible: true
      }
    });
    const nextPath = typeof version?.projectPath === "string" ? version.projectPath : pathOverride;
    if (nextPath) setHistory(await window.ave.listHistory({ projectPath: nextPath }));
    return version;
  }

  async function commitProjectTextChange(name: string, nextText: string, summary: Record<string, unknown> = {}, nextPathOverride = projectPath) {
    if (!nextText.trim()) return null;
    if (nextText === projectText) {
      setProjectText(nextText);
      return null;
    }
    await captureAutosave(`before_${safeRecoveryReason(name)}`, projectText, nextPathOverride);
    const version = await recordProjectVersion(`Before ${name}`, {
      source: "safe_project_mutation",
      safeEditRule: "restore_point_before_project_change",
      ...summary
    }, nextText, projectText, nextPathOverride);
    const nextPath = typeof version?.projectPath === "string" ? version.projectPath : nextPathOverride;
    if (!projectPath && nextPath) setProjectPath(nextPath);
    setProjectText(nextText);
    void captureAutosave(`after_${safeRecoveryReason(name)}`, nextText, nextPath);
    return version;
  }

  function safeRecoveryReason(value: string) {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "project_change";
  }

  function restoreLocalSessionState() {
    try {
      const raw = window.localStorage.getItem("ave.recovery.session");
      if (!raw) return;
      const session = JSON.parse(raw) as Record<string, unknown>;
      if (session.pendingAiPlan) setPendingAiPlan(session.pendingAiPlan as PendingAiPlan);
      if (session.generationReview) setGenerationReview(session.generationReview as GenerationReviewState);
      if (typeof session.generationPlanPath === "string") setGenerationPlanPath(session.generationPlanPath);
      if (session.beginnerForm) setBeginnerForm(session.beginnerForm as BeginnerFormState);
      if (session.beginnerSummary) setBeginnerSummary(session.beginnerSummary as Record<string, unknown>);
      if (typeof session.preset === "string") setPreset(session.preset);
      if (typeof session.exportFormat === "string") setExportFormat(session.exportFormat as typeof exportFormat);
      if (session.quality === "preview" || session.quality === "final") setQuality(session.quality);
      if (typeof session.previewSceneId === "string") setPreviewSceneId(session.previewSceneId);
      if (typeof session.previewQualityMode === "string") setPreviewQualityMode(session.previewQualityMode);
      if (typeof session.contentMode === "string") setContentMode(session.contentMode);
      if (typeof session.contentTone === "string") setContentTone(session.contentTone);
    } catch {
      pushActivity("Session UI state could not be restored", "warning");
    }
  }

  function syncProcessingFromRenderLog(line: string) {
    const signal = renderLogSignal(line);
    if (!signal) return;
    updateProcessing(signal.patch, signal.activity, signal.kind, signal.detail);
  }

  function syncProcessingFromQueue(items: RenderQueueItem[]) {
    const active = items.find((item) => item.status === "running") || items.find((item) => item.status === "queued");
    if (!active) return;
    const stage = active.status === "queued" ? "Waiting in render queue" : active.currentScene ? `Rendering ${active.currentScene}` : "Rendering";
    const progress = Number(active.progressPercent || 2);
    const workers = [
      { name: "Render worker", status: active.status === "running" ? "running" : "queued", progress },
      { name: "Preview cache", status: useCache ? "running" : "idle", progress: useCache ? Math.min(100, progress + 8) : undefined },
      { name: "Encoder", status: active.currentScene === "export" ? "running" : "queued", progress: active.currentScene === "export" ? progress : undefined },
      { name: "Delivery package", status: active.packageStatus === "completed" ? "complete" : active.packageStatus === "running" ? "running" : active.packageStatus === "failed" ? "blocked" : "queued" }
    ] as ProcessingWorker[];
    updateProcessing({
      isActive: true,
      currentStage: stage,
      activeTask: active.label,
      progress,
      etaSeconds: active.estimatedRemainingSeconds,
      currentScene: active.currentScene,
      workers
    }, active.currentScene ? `Rendering ${active.currentScene}` : `${active.label} ${active.status}`, "info", `ETA ${formatEta(active.estimatedRemainingSeconds)}`);
  }

  function appendAssistantMessage(role: "user" | "assistant", text: string) {
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setAssistantMessages((messages) => [...messages.slice(-20), { role, text, time: now }]);
  }

  function applyAdaptiveDefaults(memory: AdaptiveWorkflowMemory | null = adaptiveMemory, force = false) {
    const defaults = memory?.smartDefaults || {};
    const preferredTemplate = stringDefault(defaults.template);
    const targetPlatform = stringDefault(defaults.targetPlatform);
    const preferredDuration = numberDefault(defaults.duration);
    const preferredVibe = [stringDefault(defaults.lightingProfile), stringDefault(defaults.pacing)].filter(Boolean).join(" ").trim();
    setBeginnerForm((current) => ({
      ...current,
      template: preferredTemplate && (force || current.template === defaultBeginnerForm.template) ? preferredTemplate : current.template,
      targetPlatform: targetPlatform && (force || current.targetPlatform === defaultBeginnerForm.targetPlatform) ? targetPlatform : current.targetPlatform,
      duration: preferredDuration && (force || current.duration === defaultBeginnerForm.duration) ? preferredDuration : current.duration,
      vibe: preferredVibe && (force || current.vibe === defaultBeginnerForm.vibe) ? preferredVibe : current.vibe
    }));
    const exportPreset = stringDefault(defaults.exportPreset);
    if (exportPreset && (force || preset === "youtube_1080p")) setPreset(exportPreset);
    pushActivity(force ? "Applied adaptive defaults" : "Loaded adaptive workflow memory", "success", exportPreset || preferredTemplate || "local-only");
  }

  async function refreshAdaptiveMemory(applyDefaults = false) {
    const memory = await window.ave.getAdaptiveWorkflowMemory({ text: projectText, projectPath, profile: "Default Creator" });
    setAdaptiveMemory(memory);
    if (applyDefaults) applyAdaptiveDefaults(memory, true);
    setStatus(applyDefaults ? "Adaptive defaults applied" : "Adaptive workflow memory refreshed");
  }

  async function recordAdaptiveEvent(payload: Record<string, unknown>) {
    const current = latestProjectRef.current;
    try {
      const memory = await window.ave.recordAdaptiveWorkflowEvent({
        ...payload,
        text: typeof payload.text === "string" ? payload.text : current.text,
        projectPath: typeof payload.projectPath === "string" ? payload.projectPath : current.path,
        profile: String(payload.profile || "Default Creator")
      });
      setAdaptiveMemory(memory);
    } catch {
      // Adaptive memory should never block editing or rendering.
    }
  }

  function applyProactiveSuggestion(suggestion: ProactiveSuggestion) {
    if (!project) return;
    let next = project;
    if (suggestion.action === "shorten_intro") {
      next = shortenScene(next, suggestion.sceneId || next.timeline?.[0]?.id || "", 0.72);
    } else if (suggestion.action === "improve_captions") {
      sendCollaborationInstruction("slow down the captions and improve readability");
      void recordAdaptiveEvent({ event: "proactive_suggestion_applied", correction: suggestion.action, note: suggestion.title });
      return;
    } else if (suggestion.action === "smooth_transitions") {
      next = suggestBetterTransitions(next);
    } else if (suggestion.action === "add_transition_here") {
      next = suggestBetterTransitions(next);
    } else if (suggestion.action === "add_zoom") {
      next = applyZoomSuggestion(next, suggestion.sceneId || next.timeline?.[0]?.id || "", 1.12);
    } else if (suggestion.action === "add_caption_here") {
      next = addCaptionSuggestion(next, suggestion.sceneId || sceneAtTime(next, Number(suggestion.time || 0))?.id || next.timeline?.[0]?.id || "");
    } else if (suggestion.action === "add_hook") {
      next = replaceFirstSceneText(next, alternateHookText(productNameFromProject(next), "clean_professional", firstTextLayerValue(next)));
      const firstSceneId = next.timeline?.[0]?.id;
      if (firstSceneId) next = shortenScene(next, firstSceneId, 0.7);
    } else if (suggestion.action === "remove_silence") {
      const time = Number(suggestion.time || 0);
      const scene = sceneAtTime(next, time) || next.timeline?.[0];
      if (scene) {
        const silenceDuration = Math.max(0, Number(suggestion.duration || 0));
        if (silenceDuration > 0 && Number(scene.duration || 0) > 0.9) {
          const currentDuration = Number(scene.duration || 0);
          const trimAmount = Math.min(silenceDuration, Math.max(0, currentDuration - 0.9), currentDuration * 0.7);
          const factor = Math.max(0.1, (currentDuration - trimAmount) / currentDuration);
          next = shortenScene(next, scene.id, factor);
        }
        next = addPreviewReviewMarker(next, {
          type: "needs_cut",
          time,
          sceneId: scene.id,
          note: suggestion.detail
        });
      }
    } else if (suggestion.action === "reduce_motion") {
      sendCollaborationInstruction("remove excessive motion");
      void recordAdaptiveEvent({ event: "proactive_suggestion_applied", correction: suggestion.action, note: suggestion.title });
      return;
    } else if (suggestion.action === "enable_proxies") {
      setPreviewQualityMode("proxy");
      setUseCache(true);
      setStatus("Proxy preview and cache enabled");
      void recordAdaptiveEvent({ event: "proactive_suggestion_applied", correction: suggestion.action, note: suggestion.title });
      return;
    } else if (suggestion.action === "review_scene" && suggestion.sceneId) {
      next = setSceneReviewStatus(next, suggestion.sceneId, "needs_review");
    } else if (suggestion.action === "preview_moment") {
      setPreviewTimeSeconds(Number(suggestion.time || 0));
      setActiveTab("preview");
      setStatus(`Jumped to ${formatTimestamp(Number(suggestion.time || 0))}`);
      void recordAdaptiveEvent({ event: "proactive_suggestion_applied", correction: suggestion.action, note: suggestion.title, previewTime: suggestion.time });
      return;
    } else if (suggestion.command) {
      sendCollaborationInstruction(suggestion.command);
      void recordAdaptiveEvent({ event: "proactive_suggestion_applied", correction: suggestion.action, note: suggestion.title });
      return;
    }
    updateProject(next);
    setStatus(`Applied suggestion: ${suggestion.title}`);
    pushActivity(`Applied proactive suggestion`, "success", suggestion.title);
    void recordAdaptiveEvent({ event: "proactive_suggestion_applied", correction: suggestion.action, note: suggestion.title, duration: project ? totalTimelineDuration(project) : undefined });
  }

  function ignoreSuggestedEdit(suggestion: ProactiveSuggestion) {
    setIgnoredSuggestedEditIds((ids) => [...new Set([...ids, suggestion.id])]);
    setStatus(`Ignored suggestion: ${suggestion.title}`);
    void recordAdaptiveEvent({ event: "suggested_edit_ignored", correction: suggestion.action, note: suggestion.title });
  }

  function saveSuggestedEdit(suggestion: ProactiveSuggestion) {
    setSavedSuggestedEdits((items) => items.some((item) => item.id === suggestion.id) ? items : [...items, suggestion]);
    setStatus(`Saved suggestion: ${suggestion.title}`);
    void recordAdaptiveEvent({ event: "suggested_edit_saved", correction: suggestion.action, note: suggestion.title });
  }

  function disableSuggestionType(action: string) {
    setDisabledSuggestionTypes((types) => [...new Set([...types, action])]);
    setStatus(`Disabled suggestion type: ${friendlyPresetName(action)}`);
    void recordAdaptiveEvent({ event: "suggestion_type_disabled", correction: action });
  }

  function applyBackgroundImprovement(improvement: BackgroundImprovement) {
    if (!project) return;
    let next = project;
    if (improvement.type === "alternate_hook" && improvement.text) {
      next = replaceFirstSceneText(next, improvement.text);
    } else if (improvement.type === "alternate_caption" && improvement.sceneId && improvement.text) {
      next = applyPreviewPauseEdit(next, improvement.sceneId, { captionText: improvement.text });
    } else if (improvement.type === "pacing_improvement" && improvement.sceneId) {
      next = shortenScene(next, improvement.sceneId, 0.86);
    } else if (improvement.type === "thumbnail_candidate") {
      setPreviewTimeSeconds(Number(improvement.time || 0));
      setActiveTab("preview");
      setStatus(`Thumbnail candidate queued at ${formatTimestamp(Number(improvement.time || 0))}`);
      setBackgroundImprovements((items) => items.filter((item) => item.id !== improvement.id));
      void recordAdaptiveEvent({ event: "background_improvement_applied", correction: improvement.type, note: improvement.title, previewTime: improvement.time });
      return;
    }
    updateProject(next);
    setBackgroundImprovements((items) => items.filter((item) => item.id !== improvement.id));
    setStatus(`Applied background improvement: ${improvement.title}`);
    pushActivity("Applied background improvement", "success", improvement.title);
    void recordAdaptiveEvent({ event: "background_improvement_applied", correction: improvement.type, note: improvement.title });
  }

  function applyCollaborationSceneAction(sceneId: string, action: CollaborationSceneAction) {
    if (!project) return;
    const index = (project.timeline || []).findIndex((scene) => scene.id === sceneId);
    const scene = project.timeline?.[index];
    if (!scene) return;
    let next = project;
    let message = "";
    if (action === "approve") {
      next = setSceneReviewStatus(project, sceneId, "approved");
      message = `Approved ${sceneId}`;
    } else if (action === "reject") {
      next = setSceneReviewStatus(project, sceneId, "needs_review");
      message = `${sceneId} marked for review`;
    } else if (action === "regenerate") {
      next = regeneratePreviewSection(project, sceneId, "scene", { fromTime: scene.start, toTime: scene.start + scene.duration });
      message = `${sceneId} regenerated locally`;
    } else if (action === "lock") {
      next = applyPreviewPauseEdit(project, sceneId, { lockScene: true });
      message = `${sceneId} locked`;
    } else if (action === "skip") {
      next = applyPreviewPauseEdit(project, sceneId, { excludeScene: true });
      message = `${sceneId} skipped from final export`;
    } else if (action === "faster" || action === "slower") {
      const factor = action === "faster" ? 0.86 : 1.14;
      next = updateSceneTimingAdvanced(project, index, { duration: Math.max(0.6, Number((scene.duration * factor).toFixed(3))) }, { ripple: true, snapSeconds: 0.05 });
      message = `${sceneId} pacing ${action}`;
    }
    updateProject(next);
    pushActivity(message, action === "reject" ? "warning" : "success");
    appendAssistantMessage("assistant", message);
    void recordAdaptiveEvent({
      event: "scene_action",
      correction: action,
      note: sceneId,
      duration: scene.duration,
      style: project.stylePreset || project.metadata?.stylePreset || null
    });
  }

  function editCollaborationCaption(sceneId: string, text: string) {
    if (!project) return;
    const next = applyPreviewPauseEdit(project, sceneId, { captionText: text });
    updateProject(next);
    pushActivity(`Edited caption in ${sceneId}`, "success", text);
  }

  async function previewCollaborationScene(sceneId: string) {
    if (!project) return;
    setPreviewSceneId(sceneId);
    setPreviewScope("scene");
    setActiveTab("preview");
    await productAction("Partial scene preview", async () => {
      const result = await window.ave.interactivePreview({
        text: projectText,
        projectPath,
        qualityMode: previewQualityMode,
        scope: "scene",
        sceneId
      });
      if (result.data) {
        const nextPreview = result.data as InteractivePreviewState;
        setInteractivePreview(nextPreview);
        if (nextPreview.previewVideo) setPreviewPath(nextPreview.previewVideo);
      }
      setStatus(result.ok ? `Partial preview ready for ${sceneId}` : result.stderr || result.stdout || "Partial preview failed");
    });
  }

  function sendCollaborationInstruction(instructionOverride?: string) {
    const instruction = (instructionOverride ?? assistantDraft).trim();
    if (!instruction || !project) return;
    appendAssistantMessage("user", instruction);
    const result = applyAssistantInstruction(project, instruction);
    updateProject(result.project);
    setAssistantDraft("");
    setAiNotes(result.summary);
    appendAssistantMessage("assistant", result.summary);
    pushActivity("Applied live assistant instruction", "success", result.summary);
    void recordAdaptiveEvent({
      event: "assistant_instruction",
      correction: classifyWorkflowInstruction(instruction),
      note: instruction,
      style: result.project.stylePreset || result.project.metadata?.stylePreset || null
    });
    updateProcessing({
      currentStage: "Live collaboration edit applied",
      activeTask: instruction,
      progress: Math.max(processing.progress, 34),
      reasoning: [result.summary, ...processing.reasoning].slice(0, 5)
    });
  }

  async function openProject() {
    const file = await window.ave.openProject();
    if (!file) return;
    setProjectText(file.text);
    setProjectPath(file.path);
    setStatus(`Opened ${file.name}`);
    setUiMode("advanced");
    setActiveTab("json");
    setRecent(await window.ave.getRecentProjects());
    setRecoveryPoints(await window.ave.listRecovery({ projectPath: file.path }));
    setProjectHealth(null);
  }

  async function saveProject() {
    const file = await window.ave.saveProject({ path: projectPath, text: projectText });
    setProjectPath(file.path);
    setStatus(`Saved ${file.name}`);
    setRecent(await window.ave.getRecentProjects());
    await captureAutosave("manual_save", projectText, file.path);
  }

  async function saveAs() {
    const file = await window.ave.saveProjectAs({ text: projectText });
    if (!file) return;
    setProjectPath(file.path);
    setStatus(`Saved ${file.name}`);
    setRecent(await window.ave.getRecentProjects());
    await captureAutosave("manual_save_as", projectText, file.path);
  }

  async function newProjectSafely(startTab: Tab = "editor") {
    await captureAutosave("before_new_project", projectText, projectPath);
    setProjectText(formatProject(blankProject()));
    setProjectPath(null);
    setProjectHealth(null);
    setGenerationReview(null);
    setPendingAiPlan(null);
    setUiMode("advanced");
    setActiveTab(startTab);
    setStatus("New project started. Previous edit was autosaved.");
  }

  async function validate() {
    const result = await window.ave.validateJson({ text: projectText });
    setValidation(result);
    setStatus(result.ok ? "JSON is valid" : "Validation failed");
  }

  async function repair() {
    const result = await window.ave.repairJson({ text: projectText });
    setValidation(result);
    if (result.ok && result.text) {
      await commitProjectTextChange("JSON repair", result.text, { source: "repair_json" });
      setStatus("JSON repaired");
    } else {
      setStatus("Repair failed");
    }
  }

  async function createFromTemplate(template: string) {
    beginProcessing("Template plan", `Preparing ${templateLabels[template] || template}`, "review-first");
    const result = await window.ave.createTemplate({ template });
    if (result.ok && result.text) {
      const parsedTemplate = parseProject(result.text).data;
      const reviewState = reviewFromProjectText(result.text, {}, result.path || null, `Template plan for ${templateLabels[template] || template}. Review scenes, captions, effects, and export settings before applying.`);
      setPendingAiPlan({
        source: "template",
        title: "Template Plan Review",
        prompt: `Apply template: ${templateLabels[template] || template}`,
        text: result.text,
        path: result.path || null,
        data: { templateKey: template },
        review: reviewState,
        preset: parsedTemplate?.exportPreset || parsedTemplate?.project?.exportPreset || preset
      });
      setGenerationReview(reviewState);
      setStatus(`Template plan ready: ${templateLabels[template] || template}`);
      addNotification("AI plan ready", `Template plan ready: ${templateLabels[template] || template}`, "success", "aiReview", `${reviewState.scenes.length} scenes`);
      setUiMode("advanced");
      setActiveTab("templatesMode");
      setAppModal("aiReview");
      finishProcessing("Template plan ready for review", "success");
    } else {
      setStatus(result.stderr || result.stdout || "Template failed");
      finishProcessing(result.stderr || result.stdout || "Template failed", "error");
    }
  }

  async function generateTemplatePlanFromForm(formToUse: BeginnerFormState) {
    await productAction("Template Plan", async () => {
      const quick = beginnerRequestFromForm(formToUse);
      const templateName = templateNameFromKey(quick.template);
      updateProcessing({
        currentStage: "Building template edit plan",
        activeTask: templateName,
        progress: 18,
        currentAsset: quick.mediaFile || quick.imageFolder || quick.assetFolder || undefined
      }, `Preparing ${templateName}`, "info", "Template changes are staged for review before touching the timeline.");
      const result = await window.ave.beginnerAutoTemplate({
        mediaFile: quick.mediaFile,
        imageFolder: quick.imageFolder,
        assetFolder: quick.assetFolder,
        musicPath: quick.musicPath,
        logoPath: quick.logoPath,
        targetPlatform: quick.targetPlatform,
        template: quick.template,
        productName: quick.productName,
        goal: quick.goal,
        keyFeatures: quick.keyFeatures,
        vibe: quick.vibe,
        duration: quick.duration,
        quality: "preview",
        render: false,
        cache: true
      });
      if (result.ok && result.text) {
        const sceneCount = parseProject(result.text).data?.timeline?.length || 0;
        const presetValue = quick.targetPlatform === "youtube" ? "youtube_1080p" : quick.targetPlatform === "tiktok" ? "tiktok_reels" : quick.targetPlatform;
        const reviewState = reviewFromProjectText(result.text, result.data || {}, result.path || null, `Template plan for ${templateName}. Review the scenes, cuts, captions, effects, and export settings before applying.`);
        setPendingAiPlan({
          source: "template",
          title: "Template Plan Review",
          prompt: formToUse.quickPrompt || `Apply ${templateName}`,
          text: result.text,
          path: result.path || null,
          data: { ...(result.data || {}), templateKey: quick.template },
          review: reviewState,
          preset: presetValue,
          form: formToUse,
          renderQuality: "preview"
        });
        setGenerationReview(reviewState);
        setBeginnerSummary(result.data || null);
        setBeginnerForm(formToUse);
        setStatus(`Template plan ready: ${templateName}`);
        addNotification("AI plan ready", `Template plan ready: ${templateName}`, "success", "aiReview", `${sceneCount} scenes`);
        updateProcessing({
          currentStage: "Template plan ready",
          activeTask: "Review before applying to timeline",
          progress: 100,
          currentScene: `${sceneCount} scenes generated`
        }, `Built ${sceneCount} proposed scenes`, "success", "The current timeline has not been overwritten.");
        setUiMode("advanced");
        setActiveTab("templatesMode");
        setAppModal("aiReview");
      } else {
        setStatus(result.stderr || result.stdout || "Template plan failed");
      }
    });
  }

  function openTemplateCustomizer(templateKey: string, duplicate = false) {
    const customizer = templateCustomizerFromKey(templateKey, engine?.templates || []);
    setTemplateCustomizer({
      ...customizer,
      name: duplicate ? `${customizer.name} Copy` : customizer.name
    });
    setAppModal("templateCustomizer");
    setStatus(duplicate ? `Duplicated template for customization: ${customizer.name}` : `Customizing ${customizer.name}`);
  }

  function previewTemplate(templateKey: string) {
    const customizer = templateCustomizerFromKey(templateKey, engine?.templates || []);
    setTemplateCustomizer(customizer);
    setAiNotes(templatePreviewSummary(customizer));
    setAppModal("templateCustomizer");
    setStatus(`Previewing template settings: ${customizer.name}`);
  }

  async function applyTemplatePlan(templateKey: string) {
    const customizer = templateCustomizerFromKey(templateKey, engine?.templates || []);
    if (customizer.source === "json") {
      await createFromTemplate(templateKey);
      return;
    }
    await generateTemplatePlanFromForm(formFromTemplateCustomizer(customizer, beginnerForm));
  }

  async function applyTemplateCustomization() {
    if (!templateCustomizer) {
      setStatus("No template customization is open.");
      return;
    }
    setAppModal(null);
    if (templateCustomizer.source === "json") {
      await createFromTemplate(templateCustomizer.key);
      return;
    }
    await generateTemplatePlanFromForm(formFromTemplateCustomizer(templateCustomizer, beginnerForm));
  }

  function saveTemplateCustomization() {
    if (!templateCustomizer) return;
    try {
      window.localStorage.setItem(`ave.myTemplate.${templateCustomizer.key}`, JSON.stringify({ ...templateCustomizer, savedAt: new Date().toISOString() }));
      setStatus(`Saved template preset locally: ${templateCustomizer.name}`);
    } catch {
      setStatus("Template preset could not be saved locally.");
    }
  }

  function saveTemplatePreset(templateKey: string) {
    const customizer = templateCustomizerFromKey(templateKey, engine?.templates || []);
    try {
      window.localStorage.setItem(`ave.myTemplate.${templateKey}`, JSON.stringify({ ...customizer, savedAt: new Date().toISOString() }));
      setStatus(`Saved template preset locally: ${customizer.name}`);
    } catch {
      setStatus("Template preset could not be saved locally.");
    }
  }

  async function generateBeginnerAutoVideo(renderQuality: "preview" | "final", formOverride?: BeginnerFormState) {
    await productAction("Beginner Auto Video", async () => {
      const formToUse = formOverride || beginnerForm;
      const quick = beginnerRequestFromForm(formToUse);
      updateProcessing({
        currentStage: "Generating auto-template plan",
        activeTask: quick.productName,
        progress: 14,
        currentAsset: quick.mediaFile || quick.imageFolder || quick.assetFolder || undefined
      }, "Interpreting quick-create prompt", "info", quick.goal);
      const result = await window.ave.beginnerAutoTemplate({
        mediaFile: quick.mediaFile,
        imageFolder: quick.imageFolder,
        assetFolder: quick.assetFolder,
        musicPath: quick.musicPath,
        logoPath: quick.logoPath,
        targetPlatform: quick.targetPlatform,
        template: quick.template,
        productName: quick.productName,
        goal: quick.goal,
        keyFeatures: quick.keyFeatures,
        vibe: quick.vibe,
        duration: quick.duration,
        quality: renderQuality,
        render: false,
        cache: true
      });
      if (result.ok && result.text) {
        const sceneCount = parseProject(result.text).data?.timeline?.length || 0;
        const presetValue = quick.targetPlatform === "youtube" ? "youtube_1080p" : quick.targetPlatform === "tiktok" ? "tiktok_reels" : quick.targetPlatform;
        const reviewState = reviewFromProjectText(result.text, result.data || {}, result.path || null, `Create a ${quick.targetPlatform} edit for ${quick.productName}.`);
        const pendingPlan: PendingAiPlan = {
          source: "quick",
          title: "AI Edit Plan",
          prompt: formToUse.quickPrompt,
          text: result.text,
          path: result.path || null,
          data: result.data || {},
          review: reviewState,
          preset: presetValue,
          form: formToUse,
          renderQuality
        };
        setPendingAiPlan(pendingPlan);
        setGenerationReview(reviewState);
        setBeginnerSummary(result.data || null);
        void recordAdaptiveEvent({
          event: "beginner_auto_video",
          template: quick.template,
          targetPlatform: quick.targetPlatform,
          exportPreset: presetValue,
          duration: quick.duration,
          style: quick.vibe,
          pacing: selectedPacingForTemplate(quick.template),
          mediaPath: quick.mediaFile || quick.assetFolder || quick.imageFolder || null,
          prompt: formToUse.quickPrompt,
          note: `${renderQuality}_plan_review`
        });
        setStatus("AI edit plan ready for review");
        addNotification("AI plan ready", "Beginner auto video plan is ready to review.", "success", "aiReview", `${sceneCount} proposed scenes`);
        updateProcessing({
          currentStage: "AI plan ready",
          activeTask: "Review before applying to timeline",
          progress: 100,
          currentScene: `${sceneCount} scenes generated`
        }, `Built ${sceneCount} proposed scenes`, "success", "Review the plan, then apply it to the timeline.");
        setUiMode("beginner");
        setActiveTab("beginner");
        setAppModal("aiReview");
        setRecent(await window.ave.getRecentProjects());
      } else {
        setStatus(result.stderr || result.stdout || "Beginner Auto Video failed");
      }
    });
  }

  async function pickQuickCreateMedia() {
    const path = await window.ave.beginnerPickMedia();
    if (!path) return;
    setQuickCreate((current) => ({ ...current, mediaFile: path }));
    setBeginnerForm((current) => ({ ...current, mediaFile: path }));
    void recordAdaptiveEvent({ event: "media_imported", mediaPath: path, note: "quick_create_media" });
  }

  async function generateQuickCreateEdit() {
    let request = quickCreate;
    if (!request.mediaFile) {
      const path = await window.ave.beginnerPickMedia();
      if (!path) {
        setStatus("Select a video first, then Quick Create can generate the edit.");
        return;
      }
      request = { ...request, mediaFile: path };
      setQuickCreate(request);
      void recordAdaptiveEvent({ event: "media_imported", mediaPath: path, note: "quick_create_media" });
    }
    const nextForm = beginnerFormFromQuickCreate(beginnerForm, request);
    setBeginnerForm(nextForm);
    setUiMode("beginner");
    setActiveTab("beginner");
    await generateBeginnerAutoVideo("preview", nextForm);
  }

  async function guidedImportMedia() {
    await pickQuickCreateMedia();
    setGuidedStep(2);
  }

  function guidedApplyToTimeline() {
    if (generationReview) {
      void approveGeneratedPlan("all", "approved");
      setStatus("AI plan approved and ready for timeline preview");
    } else {
      void generateBeginnerAutoVideo("preview");
    }
    setUiMode("advanced");
    setActiveTab("editor");
    setGuidedStep(6);
  }

  async function applyPendingAiPlan() {
    if (!pendingAiPlan) {
      setStatus("No AI plan is waiting for approval.");
      return;
    }
    const targetPath = pendingAiPlan.path || projectPath;
    const versionName = pendingAiPlan.source === "template" ? "Before template apply" : "Before AI edit";
    const version = await recordProjectVersion(versionName, {
      source: pendingAiPlan.source,
      prompt: pendingAiPlan.prompt,
      style: pendingAiPlan.review.style,
      duration: pendingAiPlan.review.duration,
      sceneCount: parseProject(pendingAiPlan.text).data?.timeline?.length || pendingAiPlan.review.scenes.length,
      safeEditRule: "restore_point_before_ai_or_template"
    }, pendingAiPlan.text, projectText, targetPath);
    await captureAutosave(versionName.toLowerCase().replace(/\s+/g, "_"), projectText, targetPath);
    const appliedPath = targetPath || (typeof version?.projectPath === "string" ? version.projectPath : null);
    setProjectText(pendingAiPlan.text);
    setProjectPath(appliedPath);
    setPreset(pendingAiPlan.preset);
    setGenerationReview(pendingAiPlan.review);
    setGenerationPlanPath(pendingAiPlan.review.planPath);
    if (pendingAiPlan.source === "quick" && pendingAiPlan.form) {
      setBeginnerForm(pendingAiPlan.form);
      setBeginnerSummary(pendingAiPlan.data || null);
      setUiMode("beginner");
      setActiveTab("beginner");
    } else {
      setUiMode("advanced");
      setActiveTab("editor");
    }
    setAiNotes(simplePlanExplanation(pendingAiPlan));
    if (appliedPath) {
      setHistory(await window.ave.listHistory({ projectPath: appliedPath }));
      setRecoveryPoints(await window.ave.listRecovery({ projectPath: appliedPath }));
    }
    setStatus(version?.id ? `AI plan applied. Restore version saved: ${version.id}` : "AI plan applied. Restore point saved.");
    setPendingAiPlan(null);
    setAppModal(null);
  }

  function editPendingAiPlan() {
    if (pendingAiPlan?.source === "quick") {
      if (pendingAiPlan.form) setBeginnerForm(pendingAiPlan.form);
      setUiMode("beginner");
      setActiveTab("beginner");
      setAppModal(null);
    } else if (pendingAiPlan?.source === "template") {
      const key = pendingAiPlan.form?.template || String(pendingAiPlan.data?.templateKey || "");
      const customizer = templateCustomizerFromKey(key, engine?.templates || []);
      setTemplateCustomizer(pendingAiPlan.form ? {
        ...customizer,
        platform: pendingAiPlan.form.targetPlatform,
        duration: pendingAiPlan.form.duration,
        captionStyle: customizer.captionStyle,
        pacing: customizer.pacing
      } : customizer);
      setActiveTab("templatesMode");
      setAppModal("templateCustomizer");
    } else {
      setAppModal("ai");
    }
    setStatus("Edit the instructions, then regenerate the plan.");
  }

  async function regeneratePendingAiPlan() {
    const plan = pendingAiPlan;
    if (!plan) {
      setStatus("No AI plan is waiting to regenerate.");
      return;
    }
    const source = plan.source;
    const form = plan.form;
    setPendingAiPlan(null);
    if (source === "quick") {
      await generateBeginnerAutoVideo(plan.renderQuality || "preview", form || beginnerForm);
    } else if (source === "template") {
      if (form) await generateTemplatePlanFromForm(form);
      else await createFromTemplate(String(plan.data?.templateKey || plan.prompt.replace(/^Apply template:\s*/i, "")));
    } else if (source === "youtubeShort") {
      await generateYouTubeShort();
    } else if (source === "content") {
      await generateContentMode("full");
    } else if (source === "director") {
      await runDirector();
    } else {
      await generateFromPrompt();
    }
  }

  async function savePendingAiPlanAsTemplate() {
    if (!pendingAiPlan) {
      setStatus("No AI plan is available to save.");
      return;
    }
    const saved = await window.ave.saveProjectAs({ text: pendingAiPlan.text });
    setStatus(saved ? `Saved AI plan as reusable project template: ${saved.name}` : "Template save canceled");
  }

  async function generateFromPrompt() {
    beginProcessing("Prompt JSON", "Generating project JSON", prompt);
    const result = await window.ave.aiGenerate({ prompt });
    if (result.ok && result.text) {
      const reviewState = reviewFromProjectText(result.text, {}, result.path || null, "AI generated a project from your prompt.");
      setPendingAiPlan({
        source: "prompt",
        title: "AI Edit Plan",
        prompt,
        text: result.text,
        path: result.path || null,
        data: {},
        review: reviewState,
        preset
      });
      setGenerationReview(reviewState);
      setStatus("AI edit plan ready for review");
      addNotification("AI plan ready", "Prompt-generated edit plan is ready to review.", "success", "aiReview", `${reviewState.scenes.length} scenes`);
      setUiMode("advanced");
      setAppModal("aiReview");
      finishProcessing("Prompt plan generated", "success");
    } else {
      setStatus(result.stderr || result.stdout || "AI generation failed");
      finishProcessing("Prompt JSON failed", "error");
    }
  }

  async function generateYouTubeShort() {
    beginProcessing("YouTube Short", "Creating hook/body/outro structure", prompt);
    const result = await window.ave.youtubeShort({ prompt, style: "auto" });
    if (result.ok && result.text) {
      const hook = typeof result.data?.hook === "string" ? result.data.hook : "Short generated";
      const duration = typeof result.data?.duration === "number" ? `${result.data.duration}s` : "vertical";
      const reviewState = reviewFromProjectText(result.text, result.data || {}, result.path || null, `YouTube Short plan. Hook: ${hook}`);
      setPendingAiPlan({
        source: "youtubeShort",
        title: "AI Edit Plan",
        prompt,
        text: result.text,
        path: result.path || null,
        data: result.data || {},
        review: reviewState,
        preset: "shorts"
      });
      setGenerationReview(reviewState);
      setAiNotes(`YouTube Short plan ready.\nHook: ${hook}\nDuration: ${duration}\nReview it before applying to the timeline.`);
      setStatus("YouTube Short plan ready for review");
      addNotification("AI plan ready", "YouTube Short plan is ready to review.", "success", "aiReview", hook);
      setUiMode("advanced");
      setAppModal("aiReview");
      updateProcessing({ currentStage: "Short plan ready", progress: 100, currentScene: `${parseProject(result.text).data?.timeline?.length || "Generated"} scenes` }, "Generated YouTube Short plan", "success", hook);
      finishProcessing("YouTube Short plan generated", "success");
    } else {
      setStatus(result.stderr || result.stdout || "YouTube Short generation failed");
      finishProcessing("YouTube Short failed", "error");
    }
  }

  async function generateContentMode(regenerate = "full", promptOverride?: string, toneOverride?: string) {
    const promptToUse = promptOverride || prompt;
    const toneToUse = toneOverride || contentTone;
    beginProcessing(regenerate === "full" ? "Content Mode" : `Regenerate ${regenerate}`, stageForRegeneration(regenerate), promptToUse);
    const result = await window.ave.contentGenerate({
      prompt: promptToUse,
      mode: contentMode,
      tone: toneToUse,
      style: "auto",
      existingPlan: regenerate === "full" ? null : generationPlanPath,
      regenerate,
      locks: generationLocks
    });
    if (result.ok && result.text) {
      const presetValue = typeof result.data?.targetPlatform === "string" && result.data.targetPlatform === "tiktok" ? "tiktok_reels" : "shorts";
      const hook = typeof result.data?.hook === "string" ? result.data.hook : "Content generated";
      const duration = typeof result.data?.duration === "number" ? `${result.data.duration}s` : "generated";
      const planPath = typeof result.data?.contentPlanPath === "string" ? result.data.contentPlanPath : null;
      setGenerationPlanPath(planPath);
      const reviewState = readGenerationReview(result.data || {}, planPath);
      const fallbackReview = reviewState.scenes.length ? reviewState : reviewFromProjectText(result.text, result.data || {}, planPath, `Content plan. Hook: ${hook}`);
      setPendingAiPlan({
        source: "content",
        title: "AI Edit Plan",
        prompt: promptToUse,
        text: result.text,
        path: result.path || null,
        data: result.data || {},
        review: fallbackReview,
        preset: presetValue
      });
      setGenerationReview(fallbackReview);
      setAiNotes(`Content plan ready for review.\nMode: ${contentMode}\nStyle: ${toneToUse}\nHook: ${hook}\nDuration: ${duration}\nApprove sections before final export.`);
      setStatus(regenerate === "full" ? "Content review plan generated" : `Regenerated ${regenerate}`);
      addNotification("AI plan ready", regenerate === "full" ? "Content generation plan is ready to review." : `Regenerated ${regenerate} is ready to review.`, "success", "aiReview", hook);
      setUiMode("advanced");
      setAppModal("aiReview");
      updateProcessing({
        currentStage: "Review plan ready",
        progress: 100,
        currentScene: `${fallbackReview.scenes.length || "Generated"} review scenes`
      }, "Generated reviewable scene plan", "success", hook);
      finishProcessing("Content generation complete", "success");
    } else {
      setStatus(result.stderr || result.stdout || "Content generation failed");
      finishProcessing("Content generation failed", "error");
    }
  }

  async function runAutonomousPipeline() {
    beginProcessing("Autonomous Pipeline", "Planning script, scenes, style, review, and preview", prompt);
    const platformValue = preset === "youtube_1080p" ? "youtube_landscape" : preset === "tiktok_reels" ? "tiktok" : preset === "instagram_reels" ? "instagram_reels" : preset;
    const result = await window.ave.autonomousPipeline({
      prompt,
      assetsFolder: beginnerForm.assetFolder || null,
      musicPath: beginnerForm.musicPath || null,
      logoPath: beginnerForm.logoPath || null,
      platform: platformValue,
      contentType: contentMode,
      vibe: contentTone,
      duration: beginnerForm.duration || null,
      variants: 4,
      renderPreview: false,
      quality: "preview",
      cache: true
    });
    if (result.ok && result.text) {
      const planPath = typeof result.data?.contentPlanPath === "string" ? result.data.contentPlanPath : null;
      setGenerationPlanPath(planPath);
      const reviewState = readGenerationReview(result.data || {}, planPath);
      const fallbackReview = reviewState.scenes.length ? reviewState : reviewFromProjectText(result.text, result.data || {}, planPath, "Autonomous pipeline prepared a reviewable edit plan.");
      setGenerationReview(fallbackReview);
      const planning = result.data?.planning as Record<string, unknown> | undefined;
      const qualityReview = result.data?.qualityReview as Record<string, unknown> | undefined;
      const hook = typeof planning?.hookStrategy === "string" ? planning.hookStrategy : "autonomous structure";
      const score = typeof qualityReview?.readinessScore === "number" ? qualityReview.readinessScore : null;
      const reasoning = typeof result.data?.reasoning === "string" ? result.data.reasoning : typeof result.data?.reasoning === "undefined" && typeof result.data?.review === "object" ? "" : "";
      const explanation = typeof result.data?.reasoning === "string" ? result.data.reasoning : typeof result.data?.explainabilityTextPath === "string" ? `Explainability written to ${result.data.explainabilityTextPath}` : "";
      setPendingAiPlan({
        source: "content",
        title: "AI Edit Plan",
        prompt,
        text: result.text,
        path: result.path || null,
        data: result.data || {},
        review: fallbackReview,
        preset
      });
      setAiNotes(`Autonomous production plan ready.\nHook strategy: ${hook}\nReadiness: ${score ?? "review needed"}/100\n${explanation || reasoning || "Review and approve sections before final export."}`);
      setStatus("Autonomous production plan ready for review");
      addNotification("AI plan ready", "Autonomous production plan is ready to review.", "success", "aiReview", `Readiness ${score ?? "pending"}/100`);
      setUiMode("advanced");
      setAppModal("aiReview");
      updateProcessing({
        currentStage: "Autonomous plan ready",
        activeTask: "Review packet, variants, and quality report generated",
        progress: 100,
        currentScene: `${parseProject(result.text).data?.timeline?.length || "Generated"} scenes`
      }, "Autonomous production plan complete", "success", "Review before applying to timeline.");
      void recordAdaptiveEvent({
        event: "autonomous_pipeline",
        targetPlatform: platformValue,
        exportPreset: preset,
        duration: typeof planning?.duration === "number" ? planning.duration : undefined,
        style: typeof result.data?.styleDirection === "object" ? String((result.data.styleDirection as Record<string, unknown>).stylePreset || "") : null,
        pacing: contentTone,
        projectPath: result.path || null,
        text: prompt
      });
      finishProcessing("Autonomous pipeline generated", "success");
    } else {
      setStatus(result.stderr || result.stdout || "Autonomous pipeline failed");
      finishProcessing("Autonomous pipeline failed", "error");
    }
  }

  async function approveGeneratedPlan(section = "all", statusValue = "approved") {
    if (!generationPlanPath) {
      setStatus("No content plan is ready for approval");
      return;
    }
    const result = await window.ave.contentApprove({ planPath: generationPlanPath, section, status: statusValue });
    if (result.ok && result.data) {
      setGenerationReview(reviewDataToState(result.data, generationPlanPath, generationReview?.reasoning));
      setStatus(section === "all" ? "Generated plan approved" : `${section} marked ${statusValue}`);
    } else {
      setStatus(result.stderr || result.stdout || "Approval update failed");
    }
  }

  function lockGenerationSection(section: string) {
    setGenerationLocks((locks) => Array.from(new Set([...locks, section])));
    setStatus(`Locked ${section} for future regenerations`);
  }

  async function importAssets() {
    beginProcessing("Asset import", "Importing selected media");
    const imported = await window.ave.importAssets({ projectPath });
    if (!imported.length || !project) {
      finishProcessing("Asset import canceled", "warning");
      return;
    }
    updateProject(addImportedAssets(project, imported));
    setStatus(`Imported ${imported.length} assets`);
    finishProcessing(`Imported ${imported.length} asset(s)`, "success");
  }

  async function replaceProjectAsset(assetKey: string) {
    beginProcessing("Replace media", `Choosing replacement for ${assetKey}`);
    const imported = await window.ave.importAssets({ projectPath });
    const replacement = imported[0];
    if (!replacement || !project) {
      finishProcessing("Replace media canceled", "warning");
      return;
    }
    const next = structuredClone(project);
    next.assets = { ...(next.assets || {}), [assetKey]: replacement.path };
    updateProject(next);
    setStatus(`Replaced ${assetKey} with ${replacement.path}`);
    finishProcessing(`Replaced ${assetKey}`, "success");
  }

  async function generateCaptionsFromTranscript() {
    const transcript = await window.ave.pickTranscript();
    if (!transcript) return;
    beginProcessing("Captions", "Generating captions", transcript);
    const result = await window.ave.addCaptions({ text: projectText, transcriptPath: transcript, mode: "word", style: "tiktok" });
    if (result.ok && result.text) {
      await commitProjectTextChange("caption generation", result.text, { source: "captions", transcriptPath: transcript, mode: "word" });
      setStatus("Captions generated from transcript");
      setActiveTab("captionsMode");
      addNotification("Caption generation complete", "Generated captions from the selected transcript.", "success", "captions", transcript);
      finishProcessing("Captions generated", "success");
    } else {
      setStatus(result.stderr || result.stdout || "Caption generation failed");
      finishProcessing("Caption generation failed", "error");
    }
  }

  async function importCaptionFile() {
    const transcript = await window.ave.pickTranscript();
    if (!transcript) return;
    beginProcessing("Import captions", "Importing SRT / VTT", transcript);
    const result = await window.ave.addCaptions({ text: projectText, transcriptPath: transcript, mode: "sentence", style: "clean" });
    if (result.ok && result.text) {
      await commitProjectTextChange("caption import", result.text, { source: "caption_import", transcriptPath: transcript, mode: "sentence" });
      setStatus("Imported captions into the JSON timeline");
      setActiveTab("captionsMode");
      addNotification("Caption generation complete", "Imported captions into the JSON timeline.", "success", "captions", transcript);
      finishProcessing("Caption import complete", "success");
    } else {
      setStatus(result.stderr || result.stdout || "Caption import failed");
      finishProcessing("Caption import failed", "error");
    }
  }

  function applyCaptionPreset(style: string) {
    if (!project) {
      setStatus(`Caption style preset selected: ${style}`);
      return;
    }
    updateProject(applyCaptionStylePreset(project, style));
    setStatus(`Applied caption style preset: ${style}`);
  }

  async function render(label: string, renderQuality: "preview" | "final") {
    beginProcessing(label, renderQuality === "final" ? "Preparing final export" : "Preparing preview render", `${preset} ${exportFormat}`);
    let renderProjectPath = projectPath;
    if (renderQuality === "final" && generationReview && !generationReview.readyForFinalRender) {
      setStatus(`Final render blocked: ${generationReview.unresolved.length} generated section(s) still need approval`);
      setActiveTab("timeline");
      finishProcessing("Final render blocked by approvals", "warning");
      return;
    }
    if (renderQuality === "final" && project) {
      const readiness = previewExportReadiness(project);
      if (readiness.active && !readiness.ready) {
        setStatus(`Final export blocked: ${readiness.warnings.length} preview review issue(s) remain`);
        setActiveTab("preview");
        finishProcessing("Final render blocked by preview review", "warning");
        return;
      }
      const preflight = await runFinalPreflight(false);
      if (preflight && !preflight.ready) {
        const blockingIssue = (preflight.issues || []).find((issue) => issue.blocking);
        const issueDetail = blockingIssue ? ` - ${blockingIssue.message}` : "";
        setStatus(`Final export blocked by preflight: ${preflight.blockingCount || 0} blocking issue(s)${issueDetail}`);
        setRightRailOpen(true);
        setActiveTab("preview");
        finishProcessing("Final render blocked by preflight", "warning");
        return;
      }
      const version = await recordProjectVersion("Before final export", {
        source: "export",
        exportPreset: preset,
        format: exportFormat,
        safeEditRule: "export_does_not_modify_source_timeline"
      });
      if (!renderProjectPath && typeof version?.projectPath === "string") {
        renderProjectPath = version.projectPath;
        setProjectPath(version.projectPath);
      }
      await captureAutosave("before_final_export", projectText, renderProjectPath);
    }
    const result = await window.ave.startRender({
      text: projectText,
      projectPath: renderProjectPath,
      outputPath: outputPathFromDefaultFolder(settings.defaultExportFolder, projectTitle, renderQuality, exportFormat),
      quality: renderQuality,
      preset,
      format: exportFormat,
      generatePlaceholders: true,
      cache: useCache,
      resume,
      gpu,
      label,
      priority: renderQuality === "final" ? 10 : 0,
      createDeliveryPackage: renderQuality === "final",
      packagePlatforms: deliveryPlatformsForPreset(preset),
      packageTitle: project ? packageTitleForProject(project) : null
    });
    setRenderJobs((jobs) => [
      { runId: result.runId, label, outputPath: result.outputPath, status: "running", logs: [] },
      ...jobs
    ]);
    updateProcessing({ currentStage: "Queued render worker", activeTask: label, progress: 2 }, `${label} queued`, "info", result.outputPath);
    setStatus(`${label} queued`);
    void recordAdaptiveEvent({
      event: "render_queued",
      exportPreset: preset,
      duration: project ? totalTimelineDuration(project) : undefined,
      note: label,
      style: project?.stylePreset || project?.metadata?.stylePreset || null
    });
  }

  async function runDirector() {
    beginProcessing("AI Director", "Analyzing project pacing", directorGoal);
    const result = await window.ave.runDirector({ text: projectText, projectPath, goal: directorGoal });
    if (result.ok && result.text) {
      const data = result.report || {};
      const reviewState = reviewFromProjectText(result.text, data, result.path || projectPath || null, String(data.summary || "AI Director prepared an edit plan."));
      setPendingAiPlan({
        source: "director",
        title: "AI Edit Plan",
        prompt: directorGoal,
        text: result.text,
        path: result.path || projectPath || null,
        data,
        review: reviewState,
        preset
      });
      setDirectorReport(data);
      setGenerationReview(reviewState);
      setAiNotes(String(data.summary || "AI Director plan ready. Review before applying to the timeline."));
      setStatus("AI Director plan ready for review");
      addNotification("AI plan ready", "AI Director prepared an edit plan for review.", "success", "aiReview", String(data.summary || directorGoal));
      setAppModal("aiReview");
      finishProcessing("AI Director plan ready", "success");
    } else {
      setStatus(result.stderr || result.stdout || "AI Director failed");
      finishProcessing("AI Director failed", "error");
    }
  }

  async function buildStoryboard() {
    beginProcessing("Storyboard", "Generating scene thumbnails", projectPath || "current project");
    const result = await window.ave.generateStoryboard({ text: projectText, projectPath });
    if (result.ok && result.data) {
      setStoryboard(result.data);
      setStatus("Storyboard generated");
      setActiveTab("storyboard");
      finishProcessing("Storyboard generated", "success");
    } else {
      setStatus(result.stderr || result.stdout || "Storyboard failed");
      finishProcessing("Storyboard failed", "error");
    }
  }

  async function runAssetIntelligence() {
    beginProcessing("Asset intelligence", "Analyzing media metadata", projectPath || "current project");
    const result = await window.ave.analyzeAssets({ text: projectText, projectPath });
    if (result.data) {
      setAssetReport(result.data);
      setStatus(result.ok ? "Asset intelligence complete" : "Asset intelligence found issues");
      setActiveTab("assets");
      finishProcessing(result.ok ? "Asset intelligence complete" : "Asset intelligence needs review", result.ok ? "success" : "warning");
    } else {
      setStatus(result.stderr || result.stdout || "Asset analysis failed");
      finishProcessing("Asset intelligence failed", "error");
    }
  }

  async function resolveBroll() {
    beginProcessing("B-roll resolver", "Selecting matching local assets", projectPath || "current project");
    const result = await window.ave.resolveBroll({ text: projectText, projectPath });
    if (result.ok && result.text) {
      await commitProjectTextChange("B-roll resolution", result.text, { source: "resolve_broll" });
      setStatus("B-roll placeholders resolved");
      finishProcessing("B-roll placeholders resolved", "success");
    } else {
      setStatus(result.stderr || result.stdout || "B-roll resolution failed");
      finishProcessing("B-roll resolution failed", "error");
    }
  }

  async function productAction(label: string, action: () => Promise<void>) {
    const started = performance.now();
    try {
      setAppError("");
      beginProcessing(label, stageForAction(label));
      await action();
      const elapsedMs = Math.round(performance.now() - started);
      if (elapsedMs > 2500) {
        void window.ave.logFriction({ event: "slow_operation", label, elapsedMs, projectPath, uiMode });
      }
      finishProcessing(`${label} complete`, "success");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setAppError(`${label}: ${message}`);
      setStatus(`${label} failed`);
      void window.ave.logFriction({ event: "failed_operation", label, message, projectPath, uiMode });
      finishProcessing(`${label} failed`, "error");
    }
  }

  async function generateRealtimePreview() {
    await productAction("Realtime preview", async () => {
      const result = await window.ave.realtimePreview({
        text: projectText,
        projectPath,
        time: previewTimeSeconds,
        sceneId: previewSceneId || null,
        qualityMode: previewQualityMode,
        layerMode: previewLayerMode
      });
      if (result.data) setRealtimePreview(result.data);
      setStatus(result.ok ? "Realtime frame cached" : result.stderr || result.stdout || "Realtime preview failed");
    });
  }

  async function generateInteractivePreview() {
    await productAction("Interactive preview", async () => {
      const selectedScene = previewScope === "scene" ? previewSceneId || project?.timeline?.[0]?.id || null : null;
      if (selectedScene && !previewSceneId) setPreviewSceneId(selectedScene);
      const result = await window.ave.interactivePreview({
        text: projectText,
        projectPath,
        qualityMode: previewQualityMode,
        scope: previewScope,
        sceneId: selectedScene
      });
      if (result.data) {
        const nextPreview = result.data as InteractivePreviewState;
        setInteractivePreview(nextPreview);
        if (nextPreview.previewVideo) setPreviewPath(nextPreview.previewVideo);
      }
      setStatus(result.ok ? "Interactive preview cache ready" : result.stderr || result.stdout || "Interactive preview failed");
    });
  }

  async function updateProjectAndRefreshPreview(nextProject: ProjectData) {
    const nextText = formatProject(nextProject);
    await captureAutosave("before_preview_edit", projectText, projectPath);
    setProjectText(nextText);
    await productAction("Preview edit", async () => {
      const selectedScene = previewScope === "scene" ? previewSceneId || nextProject.timeline?.[0]?.id || null : null;
      const result = await window.ave.interactivePreview({
        text: nextText,
        projectPath,
        qualityMode: previewQualityMode,
        scope: previewScope,
        sceneId: selectedScene
      });
      if (result.data) {
        const nextPreview = result.data as InteractivePreviewState;
        setInteractivePreview(nextPreview);
        if (nextPreview.previewVideo) setPreviewPath(nextPreview.previewVideo);
      }
      setStatus(result.ok ? "Preview updated from review edit" : result.stderr || result.stdout || "Preview update failed");
    });
  }

  async function runQualityCheck() {
    await productAction("Quality check", async () => {
      const result = await window.ave.qualityCheck({ text: projectText, projectPath });
      if (result.data) setQualityReport(result.data);
      setStatus(result.ok ? "Quality check passed" : "Quality check found issues");
    });
  }

  async function runFinalPreflight(updateStatus = true): Promise<FinalPreflightReport | null> {
    try {
      const result = await window.ave.finalPreflight({
        text: projectText,
        projectPath,
        previewVideo: previewPath,
        format: exportFormat
      });
      const report = (result.data || null) as FinalPreflightReport | null;
      if (report) setFinalPreflightReport(report);
      if (updateStatus) {
        setStatus(report?.ready ? "Final preflight passed" : `Final preflight found ${report?.warningsRemaining ?? report?.issueCount ?? 0} issue(s)`);
      }
      const missingIssue = (report?.issues || []).find((issue) => /missing|asset|media|file/i.test(`${issue.category} ${issue.message}`));
      if (missingIssue) {
        addNotification("Missing media warning", missingIssue.message, missingIssue.blocking ? "error" : "warning", "assets", missingIssue.suggestion || undefined);
      }
      return report;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setAppError(`Final preflight: ${message}`);
      setStatus("Final preflight failed");
      return null;
    }
  }

  async function repairFinalPreflight(mode: string, issueId?: string | null) {
    const bulkMode = mode === "all" || mode === "safe_all" || mode === "accept_all";
    if (bulkMode) {
      setStatus("Bulk preflight repair is disabled. Approve fixes one issue at a time.");
      window.alert("Preflight fixes are applied one issue at a time so the project is never modified without your explicit approval.");
      return;
    }
    const issue = (finalPreflightReport?.issues || []).find((item) => item.id === issueId);
    if (!issueId || !issue) {
      setStatus("Select a specific preflight issue before applying a fix.");
      return;
    }
    if (mode === "selected" && !issue.safeAutoFix) {
      setStatus("This preflight issue does not have a safe automatic fix.");
      window.alert("This issue needs a manual edit. No project changes were made.");
      return;
    }
    const actionLabel = mode === "ignore"
      ? "accept this issue as intentional"
      : `apply this suggested fix: ${issue.autoFix?.label || issue.suggestion || issue.category}`;
    const approved = window.confirm(`Preflight approval required\n\nIssue:\n${issue.message}\n\nAction:\n${actionLabel}\n\nThis will update the project JSON. Continue?`);
    if (!approved) {
      setStatus("Preflight change canceled");
      return;
    }
    await productAction("Preflight repair", async () => {
      const result = await window.ave.repairPreflight({
        text: projectText,
        projectPath,
        previewVideo: previewPath,
        format: exportFormat,
        mode,
        issueId
      });
      if (result.text) await commitProjectTextChange("preflight repair", result.text, { source: "preflight_repair", mode, issueId: issueId || null });
      const refreshed = await window.ave.finalPreflight({
        text: result.text || projectText,
        projectPath: result.path || projectPath,
        previewVideo: previewPath,
        format: exportFormat
      });
      if (refreshed.data) setFinalPreflightReport(refreshed.data as FinalPreflightReport);
      setStatus(mode === "ignore" ? "Preflight issue accepted by user" : "Approved preflight fix applied");
    });
  }

  async function buildManifest() {
    await productAction("Project manifest", async () => {
      const result = await window.ave.projectManifest({ text: projectText, projectPath });
      if (result.data) setManifestReport(result.data);
      setStatus(result.ok ? "Project manifest generated" : result.stderr || result.stdout || "Manifest failed");
    });
  }

  async function reformatForSocial() {
    await productAction("Social reformat", async () => {
      const result = await window.ave.socialReformat({ text: projectText, projectPath, targets: socialTargets });
      const outputDir = String(result.data?.outputDir || result.path || "");
      setStatus(result.ok ? `Social variants written: ${outputDir}` : result.stderr || result.stdout || "Reformat failed");
    });
  }

  async function repurposeContent(renderBatch: boolean, maxVariants: number, reuseStyle: boolean) {
    await productAction("Content repurpose", async () => {
      const result = await window.ave.repurposeContent({
        text: projectText,
        projectPath,
        targets: socialTargets.length ? socialTargets : ["all"],
        hooks: ["all"],
        ctas: ["all"],
        reuseStyle,
        render: renderBatch,
        package: renderBatch,
        quality: renderBatch ? quality : "preview",
        maxVariants
      });
      if (result.data) setRepurposeReport(result.data);
      setStatus(result.ok ? `Repurposed content written: ${result.path}` : result.stderr || result.stdout || "Repurpose failed");
    });
  }

  async function createPostingPackage() {
    await productAction("Posting package", async () => {
      if (!previewPath) {
        setStatus("Render a preview or final MP4 before creating a posting package");
        return;
      }
      const result = await window.ave.postPackage({ text: projectText, projectPath, videoPath: previewPath, targets: socialTargets });
      if (result.data) setPostingPackageReport(result.data);
      setStatus(result.ok ? `Posting package created: ${result.path}` : result.stderr || result.stdout || "Posting package failed");
    });
  }

  async function reviewPostExport() {
    await productAction("Post-export review", async () => {
      if (!previewPath) {
        setStatus("Render or package a final MP4 before post-export review");
        return;
      }
      const packageDir = typeof postingPackageReport?.outputDir === "string" ? postingPackageReport.outputDir : null;
      const result = await window.ave.postExportReview({ text: projectText, projectPath, videoPath: previewPath, packageDir });
      if (result.data) setPostExportReview(result.data);
      setStatus(result.ok ? "Post-export review complete" : result.stderr || result.stdout || "Post-export review found blocking issues");
    });
  }

  async function quickPostExportReexport(mode: string, presetValue?: string, captions = "keep") {
    await productAction("Quick re-export", async () => {
      const result = await window.ave.postExportReexport({
        text: projectText,
        projectPath,
        mode,
        preset: presetValue || null,
        format: exportFormat,
        captions
      });
      if (result.text) {
        await commitProjectTextChange("quick re-export", result.text, { source: "post_export_reexport", mode, preset: presetValue || null, captions }, result.path || projectPath);
        if (result.path) setProjectPath(result.path);
      }
      setStatus(result.ok ? `Quick re-export JSON ready: ${result.path}` : result.stderr || result.stdout || "Quick re-export failed");
    });
  }

  async function savePostExportTemplate(name: string, note: string) {
    await productAction("Reusable template", async () => {
      const result = await window.ave.postExportTemplate({ text: projectText, projectPath, videoPath: previewPath, name, note });
      if (result.data) setPostExportTemplate(result.data);
      setStatus(result.ok ? `Reusable template saved: ${result.path}` : result.stderr || result.stdout || "Template save failed");
    });
  }

  async function createPostExportVariants() {
    await productAction("Post-export variants", async () => {
      const result = await window.ave.postExportVariants({ text: projectText, projectPath });
      if (result.data) setPostExportVariants(result.data);
      setStatus(result.ok ? `Post-export variants created: ${result.path}` : result.stderr || result.stdout || "Variant creation failed");
    });
  }

  async function savePostExportNote(profile: string, tags: string[], note: string) {
    await productAction("Post-export success note", async () => {
      const result = await window.ave.postExportNote({ text: projectText, projectPath, videoPath: previewPath, profile, tags, note });
      if (result.data) setPostExportNote(result.data);
      setStatus(result.ok ? "Post-export success note saved locally" : result.stderr || result.stdout || "Success note failed");
    });
  }

  async function createBrandKit() {
    await productAction("Brand kit", async () => {
      const result = await window.ave.initBrandKit();
      setStatus(result.ok ? `Brand kit created: ${result.path}` : result.stdout || "Brand kit canceled");
    });
  }

  async function applyBrandKit() {
    await productAction("Brand kit apply", async () => {
      const result = await window.ave.applyBrandKit({ text: projectText, projectPath });
      if (result.ok && result.text) {
        await commitProjectTextChange("brand kit apply", result.text, { source: "brand_kit" });
        setStatus("Brand kit applied");
      } else {
        setStatus(result.stdout || result.stderr || "Brand kit apply canceled");
      }
    });
  }

  async function saveAppSettings(next: AppSettings) {
    await productAction("Settings", async () => {
      const saved = await window.ave.saveSettings(next);
      setSettings(saved);
      setPreviewTimeSeconds(saved.previewTimeSeconds);
      applyWorkspaceLayout(saved);
      applyOnboardingDefaults(saved);
      setStatus("Settings saved");
    });
  }

  function applyWorkspaceLayout(next: AppSettings) {
    setLeftRailOpen(next.leftRailOpen !== false);
    setRightRailOpen(next.rightRailOpen !== false);
  }

  async function applyWorkspacePreset(presetName: WorkspacePreset) {
    const next = workspacePresetSettings(settings, presetName);
    setSettings(next);
    applyWorkspaceLayout(next);
    setUiMode(presetName === "beginner" ? "beginner" : "advanced");
    setActiveTab(tabForWorkspacePreset(presetName));
    await window.ave.saveSettings(next);
    await window.ave.logFriction({ event: "workspace_preset", label: presetName });
    setStatus(`Workspace preset applied: ${friendlyPresetName(presetName)}`);
  }

  async function saveWorkspaceLayout() {
    const next: AppSettings = {
      ...settings,
      leftRailOpen,
      rightRailOpen
    };
    const saved = await window.ave.saveSettings(next);
    setSettings(saved);
    setStatus("Workspace layout saved");
  }

  async function popOutWorkspacePanel(panel: "preview" | "timeline" | "inspector") {
    const result = await window.ave.popOutPanel({
      panel,
      title: `${projectTitle} - ${friendlyPresetName(panel)}`,
      projectPath,
      previewPath
    });
    const current = await window.ave.getSettings();
    setSettings(current);
    setStatus(`${friendlyPresetName(panel)} popped out (${result.bounds.width}x${result.bounds.height})`);
  }

  function applyOnboardingDefaults(next: AppSettings) {
    const nextPreset = presetForOnboardingPlatform(next.defaultPlatform);
    setPreset(nextPreset);
    setContentMode(next.defaultPlatform === "standard" ? "product_showcase" : "youtube_shorts");
    setContentTone(next.defaultStyle);
    setQuickCreate((current) => ({
      ...current,
      platform: next.defaultPlatform === "standard" ? "normal" : next.defaultPlatform,
      style: next.defaultStyle
    }));
    setBeginnerForm((current) => ({
      ...current,
      targetPlatform: next.defaultPlatform === "standard" ? "youtube" : next.defaultPlatform,
      vibe: current.vibe || next.defaultStyle
    }));
  }

  async function completeOnboarding(next: AppSettings) {
    const saved = await window.ave.saveSettings({ ...next, onboardingComplete: true });
    setSettings(saved);
    applyWorkspaceLayout(saved);
    applyOnboardingDefaults(saved);
    setAppModal(null);
    if (saved.defaultWorkflow === "quick") {
      setUiMode("beginner");
      setActiveTab("beginner");
    } else if (saved.defaultWorkflow === "guided") {
      setUiMode("advanced");
      setActiveTab("home");
      setGuidedStep(1);
    } else {
      setUiMode("advanced");
      setActiveTab("editor");
    }
    setStatus("Welcome setup complete");
  }

  async function pickDefaultExportFolder() {
    const folder = await window.ave.pickExportFolder();
    if (!folder) return null;
    setSettings((current) => ({ ...current, defaultExportFolder: folder }));
    return folder;
  }

  async function autosaveNow() {
    await productAction("Autosave", async () => {
      await captureAutosave("manual_autosave", projectText, projectPath);
      setRecoveryPoints(await window.ave.listRecovery({ projectPath }));
      setStatus("Autosave captured");
    });
  }

  async function refreshRecovery() {
    await productAction("Recovery", async () => {
      setRecoveryPoints(await window.ave.listRecovery({ projectPath }));
      setStatus("Recovery points refreshed");
    });
  }

  async function restoreRecoveryPoint(sourcePath: string) {
    await productAction("Recovery restore", async () => {
      const file = await window.ave.restoreRecovery({ sourcePath, targetPath: projectPath });
      setProjectPath(file.path);
      setProjectText(file.text);
      restoreLocalSessionState();
      setStatus(`Recovered ${file.name}`);
    });
  }

  async function runProjectHealthCheck() {
    await productAction("Project health", async () => {
      const report = await window.ave.projectHealth({ text: projectText, projectPath });
      setProjectHealth(report);
      setStatus(report.ready ? `Project health OK (${report.score}/100)` : `Project health needs attention (${report.score}/100)`);
    });
  }

  async function duplicateVersion(versionId: string) {
    if (!projectPath) {
      setStatus("Save the project before duplicating a version.");
      return;
    }
    const file = await window.ave.duplicateHistory({ projectPath, versionId });
    setProjectPath(file.path);
    setProjectText(file.text);
    setStatus(`Duplicated version ${versionId}`);
    setRecent(await window.ave.getRecentProjects());
    setActiveTab("editor");
  }

  async function compareVersion(versionId: string) {
    if (!projectPath) {
      setStatus("Save the project before comparing versions.");
      return;
    }
    const comparison = await window.ave.compareHistory({ projectPath, versionId });
    setVersionComparison(comparison);
    setAppModal("versionCompare");
    setStatus(`Compared version ${versionId}`);
  }

  async function restoreStartupRecovery() {
    const point = startupRecovery?.latestRecovery || recoveryPoints[0];
    if (!point) {
      setStatus("No startup recovery point is available.");
      return;
    }
    const file = await window.ave.restoreRecovery({ sourcePath: point.path, targetPath: projectPath });
    setProjectPath(file.path);
    setProjectText(file.text);
    restoreLocalSessionState();
    setRecoveryPoints(await window.ave.listRecovery({ projectPath: file.path }));
    setAppModal(null);
    setStatus(`Recovered unsaved project from ${point.timestamp || "last autosave"}`);
  }

  async function refreshHardeningStatus() {
    await productAction("Hardening status", async () => {
      const statusReport = await window.ave.getHardeningStatus();
      setHardeningStatus(statusReport);
      setStatus("Local hardening status refreshed");
      if (hardeningStatusHasUpdate(statusReport) && !updateAvailableNotificationRef.current) {
        updateAvailableNotificationRef.current = true;
        addNotification("Update available", "A newer local app/runtime component appears to be available.", "info", "settings", "Open settings or diagnostics before updating.");
      }
    });
  }

  async function refreshWorkflowDashboard() {
    await productAction("Production dashboard", async () => {
      const result = await window.ave.workflowDashboard({ text: projectText, projectPath });
      if (result.data) setWorkflowDashboard(result.data);
      setStatus(result.ok ? "Production dashboard refreshed" : result.stderr || result.stdout || "Production dashboard failed");
    });
  }

  async function runFeedbackAnalysis() {
    await productAction("Feedback analysis", async () => {
      const result = await window.ave.feedbackAnalyze({ text: projectText, projectPath, videoPath: previewPath });
      if (result.data) setFeedbackAnalysis(result.data);
      setStatus(result.ok ? "Feedback self-analysis complete" : result.stderr || result.stdout || "Feedback analysis failed");
    });
  }

  async function saveFeedbackReview(profile: string, ratings: Record<string, number>, note: string) {
    await productAction("Render review", async () => {
      const result = await window.ave.feedbackReview({ text: projectText, projectPath, videoPath: previewPath, profile, ratings, note });
      if (result.data) setFeedbackReview(result.data);
      void recordAdaptiveEvent({
        event: "render_review",
        note,
        profile,
        ratings,
        correction: ratings.overallPolish && ratings.overallPolish >= 4 ? "successful_style" : "needs_refinement"
      });
      setStatus(result.ok ? "Render review saved locally" : result.stderr || result.stdout || "Render review failed");
    });
  }

  async function learnCreatorIdentity(profile: string) {
    await productAction("Creator identity", async () => {
      const result = await window.ave.feedbackLearn({ profile });
      if (result.data) setCreatorIdentity(result.data);
      setStatus(result.ok ? "Creator identity refreshed" : result.stderr || result.stdout || "Creator identity learning failed");
    });
  }

  async function refreshEvolutionReport(profile: string) {
    await productAction("Evolution report", async () => {
      const result = await window.ave.evolutionReport({ text: projectText, projectPath, profile });
      if (result.data) setEvolutionReport(result.data);
      setStatus(result.ok ? "Long-term evolution report refreshed" : result.stderr || result.stdout || "Evolution report failed");
    });
  }

  async function openLocalDocs() {
    await productAction("Local docs", async () => {
      await window.ave.openLocalDocs();
      setStatus("Opened bundled local docs");
    });
  }

  async function duplicateProjectForIteration() {
    setProjectPath(null);
    setStatus("Duplicated current edit in memory");
    await window.ave.logFriction({ event: "fast_iteration", label: "duplicate_project", uiMode, projectPath });
    void recordAdaptiveEvent({ event: "fast_iteration", correction: "duplicate_project" });
  }

  function addFinalReviewNote(text: string, time: number) {
    if (!project || !text.trim()) return;
    const scene = sceneAtTime(project, time) || project.timeline?.[0];
    if (!scene) return;
    updateProject(addPreviewReviewNote(project, { text: text.trim(), time, sceneId: scene.id }), "final_review_note");
    setFinalReviewStatus("needs_changes");
    setStatus(`Added final review note at ${formatTimestamp(time)}`);
  }

  function markFinalReviewIssue(type: PreviewMarkerType, note: string, time: number) {
    if (!project) return;
    const scene = sceneAtTime(project, time) || project.timeline?.[0];
    if (!scene) return;
    updateProject(addPreviewReviewMarker(project, { type, time, sceneId: scene.id, note: note || "Final review issue" }), "final_review_marker");
    setFinalReviewStatus("needs_changes");
    setStatus(`Marked ${type.replace(/_/g, " ")} at ${formatTimestamp(time)}`);
  }

  function approveFinalReview() {
    setFinalReviewStatus("approved");
    setStatus("Final review approved");
    addNotification("Final review approved", "The cut is marked ready for export.", "success", "export");
  }

  function needsFinalReviewChanges() {
    setFinalReviewStatus("needs_changes");
    setStatus("Marked final review as needing changes");
    setActiveTab("editor");
  }

  async function refreshFrictionReport() {
    const report = await window.ave.getFrictionReport();
    setFrictionReport(report);
    setStatus("Local friction report refreshed");
  }

  const preflightBlockingIssues = (finalPreflightReport?.issues || []).filter((issue) => issue.blocking);
  const preflightWarningCount = (finalPreflightReport?.issues || []).filter((issue) => !issue.accepted && issue.severity === "warning").length;
  const projectTitle = project
    ? String(project.metadata?.title || project.metadata?.name || projectPath?.split(/[\\/]/).pop() || "Untitled Project")
    : "Untitled Project";
  const workflowContext = workflowContextFor({
    activeTab,
    project: project || null,
    projectTitle,
    projectPath,
    preset,
    exportFormat,
    generationReview,
    previewSceneId,
    beginnerForm,
    preflightBlockingCount: preflightBlockingIssues.length,
    preflightWarningCount
  });
  const appStyle = {
    "--accent-color": settings.accentColor || "#6db5a5",
    "--left-rail-width": `${leftRailOpen ? Math.max(0, Number(settings.leftRailWidth || 260)) : 0}px`,
    "--right-rail-width": `${rightRailOpen ? Math.max(0, Number(settings.rightRailWidth || 360)) : 0}px`
  } as CSSProperties;
  const visibleSuggestedEdits = suggestedEdits
    .filter((suggestion) => !ignoredSuggestedEditIds.includes(suggestion.id))
    .filter((suggestion) => !disabledSuggestionTypes.includes(suggestion.action));
  const activeTaskCount = managedTasks.filter((task) => ["queued", "running", "paused"].includes(task.status)).length;
  const unreadNotificationCount = notifications.filter((notification) => !notification.read).length;

  function openBeginnerAiPromptBuilder() {
    setUiMode("advanced");
    setActiveTab("aiStudio");
    setAiPromptBuilderOpen(true);
    setAppModal(null);
    setStatus("Opened AI Studio prompt builder");
  }

  function openFirstAiEditGuide() {
    setUiMode("advanced");
    setActiveTab("aiStudio");
    setAiPromptBuilderOpen(true);
    setAppModal(null);
    if (!prompt.trim()) {
      setPrompt("Make this imported video into a polished YouTube Short with captions, clean cuts, and a strong hook.");
    }
    setStatus("First AI Edit: describe the edit, generate a plan, review it, then apply it to the timeline.");
  }

  return (
    <div
      className={`app-shell theme-${settings.theme} scale-${settings.uiScale || "medium"} layout-${settings.panelDock || "standard"} workspace-preset-${settings.workspacePreset || "editing"} mode-${uiMode} ${leftRailOpen ? "" : "left-rail-collapsed"} ${rightRailOpen ? "" : "right-rail-collapsed"}`}
      style={appStyle}
    >
      <header className="topbar">
        <div className="project-chip">
          <strong>{projectTitle}</strong>
          <span>{projectPath || "Unsaved project"}</span>
        </div>
        <div className="toolbar">
          <button title="Save project" onClick={saveProject}><Save size={16} /> Save</button>
          <button title="Undo is available inside the active editor; Version History is in Project." onClick={() => setStatus("Use Ctrl+Z in the active editor, or open Project > Version History for saved AI edits.")}><Undo2 size={16} /> Undo</button>
          <button title="Redo is available inside the active editor." onClick={() => setStatus("Use Ctrl+Y or Ctrl+Shift+Z in the active editor when available.")}><Redo2 size={16} /> Redo</button>
          <button title="Import media" onClick={() => setAppModal("import")}><Import size={16} /> Import</button>
          <button title="Export settings and final render" onClick={() => { setRightRailOpen(true); setAppModal("export"); }}><Download size={16} /> Export</button>
          <button title="Open a beginner-friendly AI prompt builder" onClick={openBeginnerAiPromptBuilder}><CircleHelp size={16} /> Help me make this</button>
          <button title="AI Generate" onClick={() => setAppModal("ai")}><Sparkles size={16} /> AI Generate</button>
          <button title="Workspace layout, panels, themes, and scaling" onClick={() => setAppModal("workspace")}><Maximize2 size={16} /> Workspace</button>
          <button title="Caption style picker" onClick={() => setAppModal("captionStyle")}><Captions size={16} /> Captions</button>
          <button title={leftRailOpen ? "Collapse media sidebar" : "Show media sidebar"} onClick={() => setLeftRailOpen((value) => !value)}><LayoutTemplate size={16} /> {leftRailOpen ? "Hide Left" : "Show Left"}</button>
          <button title={rightRailOpen ? "Collapse inspector" : "Show inspector"} onClick={() => setRightRailOpen((value) => !value)}><Settings size={16} /> {rightRailOpen ? "Hide Right" : "Show Right"}</button>
          <button title="Open Task Manager" onClick={() => { setRightRailOpen(true); setProcessingCollapsed(false); setStatus("Task Manager opened"); }}><Clock size={16} /> Tasks{activeTaskCount ? ` ${activeTaskCount}` : ""}</button>
          <button className="notification-button" title="Notification Center" onClick={() => { setNotificationCenterOpen((value) => !value); markNotificationsRead(); }}>
            <Bell size={16} /> Notifications
            {unreadNotificationCount > 0 && <span className="notification-badge">{unreadNotificationCount}</span>}
          </button>
          {(processing.isActive || renderQueueItems.length > 0) && <button title="Render progress" onClick={() => setAppModal("renderProgress")}><Play size={16} /> Progress</button>}
          {(appError || preflightBlockingIssues.length > 0 || parsed.error) && <button title="Error recovery" onClick={() => setAppModal("errorRecovery")}><Wand2 size={16} /> Recover</button>}
          <button title="Settings" onClick={() => setAppModal("settings")}><Settings size={16} /> Settings</button>
          <button title="Help and local docs" onClick={() => setAppModal("help")}><CircleHelp size={16} /> Help</button>
        </div>
        {notificationCenterOpen && (
          <NotificationCenter
            notifications={notifications}
            onOpenAction={openNotificationAction}
            onDismiss={dismissNotification}
            onClear={clearNotifications}
            onClose={() => setNotificationCenterOpen(false)}
          />
        )}
      </header>
      {appError && (
        <div className="error-toast">
          <span>{appError}</span>
          <button onClick={() => setAppError("")}>Dismiss</button>
        </div>
      )}
      {settings.beginnerTips && (activeTab === "home" || activeTab === "beginner") && (
        <div className="beginner-tip-strip">
          <span><strong>Tip:</strong> Start with Quick Create, preview the edit, then export when it feels right.</span>
          <button title="See beginner guidance and example prompts" onClick={() => setAppModal("help")}>What does this do?</button>
          <button onClick={() => { const next = { ...settings, beginnerTips: false }; setSettings(next); void window.ave.saveSettings(next); }}>Hide tips</button>
        </div>
      )}
      <main className="workspace">
        <div className="processing-slot">
          {(processing.isActive || activityFeed.length > 0 || renderQueueItems.length > 0) && (
            <ProcessingView
              processing={processing}
              activityFeed={activityFeed}
              renderQueueItems={renderQueueItems}
              project={project || null}
              generationReview={generationReview}
              reasoning={generationReview?.reasoning || aiNotes}
              assistantDraft={assistantDraft}
              setAssistantDraft={setAssistantDraft}
              assistantMessages={assistantMessages}
              collapsed={processingCollapsed}
              setCollapsed={setProcessingCollapsed}
              onSceneAction={applyCollaborationSceneAction}
              onCaptionEdit={editCollaborationCaption}
              onAssistantSend={sendCollaborationInstruction}
              onSuggestion={(command) => sendCollaborationInstruction(command)}
              onPause={async () => setRenderQueueItems(await window.ave.pauseRenderQueue())}
              onResume={async () => setRenderQueueItems(await window.ave.resumeRenderQueue())}
              onCancelActive={async (runId) => setRenderQueueItems(await window.ave.cancelRenderJob({ runId }))}
              onPrioritizeActive={async (runId) => setRenderQueueItems(await window.ave.prioritizeRenderJob({ runId, priority: 50 }))}
              onPreviewPartial={(sceneId) => { void (sceneId ? previewCollaborationScene(sceneId) : Promise.resolve(setActiveTab("editor"))); }}
            />
          )}
        </div>
        <aside className="left-rail" aria-hidden={!leftRailOpen}>
          <div className="rail-titlebar">
            <div>
              <span className="eyebrow">Library</span>
              <strong>Media & Tools</strong>
            </div>
            <button title="Collapse media and tools" onClick={() => setLeftRailOpen(false)}><X size={14} /></button>
          </div>
          <EditorSidebar
            activeTab={activeTab}
            onTab={(tab) => { setUiMode("advanced"); setActiveTab(tab); }}
            onModal={setAppModal}
            onImport={importAssets}
            onCaptions={generateCaptionsFromTranscript}
            onHighlights={runAssetIntelligence}
            onRemoveSilence={() => setStatus("Remove silence is available through AI Generate and preview review regeneration.")}
            onTransitions={() => project && updateProject(suggestBetterTransitions(project))}
            onPacing={() => void generateContentMode("scene_plan")}
            onHook={() => void generateContentMode("hook")}
            onThumbnail={() => setActiveTab("product")}
          />
          <details className="rail-section compact-section">
            <summary><Clock size={15} /> Recent / Queue</summary>
            <Dashboard
              recent={recent}
              templates={engine?.templates || []}
              renderJobs={renderJobs}
              renderQueueItems={renderQueueItems}
              onOpenRecent={async (path) => {
                const file = await window.ave.readProject(path);
                setProjectPath(file.path);
                setProjectText(file.text);
                setUiMode("advanced");
                setActiveTab("editor");
              }}
              onTemplate={createFromTemplate}
            />
          </details>
        </aside>

        <nav className="mode-rail" aria-label="Creative workspace modes">
          <button className={activeTab === "home" ? "active" : ""} title="Project Hub" onClick={() => { setUiMode("advanced"); setActiveTab("home"); }}>
            <LayoutTemplate size={18} />
            <span>Home</span>
          </button>
          <button className={["editor", "preview", "timeline", "assets"].includes(activeTab) ? "active" : ""} title="Editor" onClick={() => { setUiMode("advanced"); setActiveTab("editor"); }}>
            <MonitorPlay size={18} />
            <span>Edit</span>
          </button>
          <button className={["aiStudio", "director", "storyboard"].includes(activeTab) ? "active" : ""} title="AI Studio" onClick={() => { setUiMode("advanced"); setActiveTab("aiStudio"); }}>
            <Bot size={18} />
            <span>AI</span>
          </button>
          <button className={activeTab === "captionsMode" ? "active" : ""} title="Captions" onClick={() => { setUiMode("advanced"); setActiveTab("captionsMode"); }}>
            <Captions size={18} />
            <span>Caps</span>
          </button>
          <button className={activeTab === "templatesMode" || activeTab === "beginner" ? "active" : ""} title="Templates" onClick={() => { setUiMode("advanced"); setActiveTab("templatesMode"); }}>
            <LayoutTemplate size={18} />
            <span>Templates</span>
          </button>
          <button className={activeTab === "reviewMode" ? "active" : ""} title="Final Review" onClick={() => { setUiMode("advanced"); setActiveTab("reviewMode"); }}>
            <CheckCircle2 size={18} />
            <span>Review</span>
          </button>
          <button className={activeTab === "exportMode" || activeTab === "product" ? "active" : ""} title="Export" onClick={() => { setUiMode("advanced"); setActiveTab("exportMode"); setRightRailOpen(true); }}>
            <Download size={18} />
            <span>Export</span>
          </button>
          <button className={["diagnostics", "workflow", "json"].includes(activeTab) ? "active" : ""} title="Logs and diagnostics" onClick={() => { setUiMode("advanced"); setActiveTab("diagnostics"); }}>
            <Clock size={18} />
            <span>Logs</span>
          </button>
        </nav>

        <section className="center-stage">
          <div className="workstation-strip">
            <div>
              <span className="eyebrow">Workspace</span>
              <strong>{workflowContext.breadcrumbs.join(" / ")}</strong>
            </div>
            <div className="workstation-strip-actions">
              <span>{friendlyPresetName(settings.workspacePreset || "editing")} layout</span>
              <button title="Open workspace layout manager" onClick={() => setAppModal("workspace")}><Maximize2 size={14} /> Layout</button>
              <button title="Pop out preview window" onClick={() => { void popOutWorkspacePanel("preview"); }}><MonitorPlay size={14} /> Pop Preview</button>
            </div>
          </div>
          <nav className="workflow-tabs">
            <button className={activeTab === "home" ? "active" : ""} onClick={() => { setUiMode("advanced"); setActiveTab("home"); }}><LayoutTemplate size={15} /> Home</button>
            {uiMode === "advanced" && (
              <>
                <button className={["editor", "preview", "timeline", "assets"].includes(activeTab) ? "active" : ""} onClick={() => setActiveTab("editor")}><MonitorPlay size={15} /> Editor</button>
                <button className={["aiStudio", "director", "storyboard"].includes(activeTab) ? "active" : ""} onClick={() => setActiveTab("aiStudio")}><Bot size={15} /> AI Studio</button>
                <button className={activeTab === "captionsMode" ? "active" : ""} onClick={() => setActiveTab("captionsMode")}><Captions size={15} /> Captions</button>
                <button className={activeTab === "templatesMode" || activeTab === "beginner" ? "active" : ""} onClick={() => setActiveTab("templatesMode")}><LayoutTemplate size={15} /> Templates</button>
                <button className={activeTab === "reviewMode" ? "active" : ""} onClick={() => setActiveTab("reviewMode")}><CheckCircle2 size={15} /> Review</button>
                <button className={activeTab === "exportMode" || activeTab === "product" ? "active" : ""} onClick={() => { setActiveTab("exportMode"); setRightRailOpen(true); }}><Download size={15} /> Export</button>
                <button className={["diagnostics", "workflow", "json"].includes(activeTab) ? "active" : ""} onClick={() => setActiveTab("diagnostics")}><Clock size={15} /> Logs / Diagnostics</button>
                {finalPreflightReport && (
                  <button
                    className={preflightBlockingIssues.length ? "preflight-tab warning" : "preflight-tab"}
                    title={preflightBlockingIssues[0]?.message || "Open render controls for the latest preflight report"}
                    onClick={() => setRightRailOpen(true)}
                  >
                    <CheckCircle2 size={15} />
                    {preflightBlockingIssues.length ? `Preflight: ${preflightBlockingIssues.length} block` : `Preflight: ${preflightWarningCount} warn`}
                  </button>
                )}
              </>
            )}
          </nav>

          <WorkflowContextHeader context={workflowContext} />

          {activeTab === "home" && (
            <ProjectHub
              projectTitle={projectTitle}
              recent={recent}
              beginnerTemplates={beginnerTemplates}
              renderQueueItems={renderQueueItems}
              quickCreate={quickCreate}
              setQuickCreate={setQuickCreate}
              guidedStep={guidedStep}
              onNewProject={() => { void newProjectSafely("editor"); }}
              onOpenProject={openProject}
              onImport={importAssets}
              onTemplate={() => setActiveTab("templatesMode")}
              onAI={() => setActiveTab("aiStudio")}
              onBeginner={() => { setUiMode("beginner"); setActiveTab("beginner"); }}
              onQuickPickMedia={pickQuickCreateMedia}
              onQuickGenerate={() => { void generateQuickCreateEdit(); }}
              onGuidedImport={guidedImportMedia}
              onGuidedTemplates={() => { setAppModal("templates"); setGuidedStep(3); }}
              onGuidedInstructions={() => { setAppModal("ai"); setGuidedStep(4); }}
              onGuidedReview={() => { setAppModal("aiReview"); setGuidedStep(5); }}
              onGuidedApply={guidedApplyToTimeline}
              onGuidedExport={() => { setAppModal("export"); setGuidedStep(6); }}
              onAdvancedTimeline={() => { setUiMode("advanced"); setActiveTab("editor"); }}
              onAdvancedJson={() => setAppModal("json")}
              onAdvancedLogs={() => { setUiMode("advanced"); setActiveTab("diagnostics"); }}
              onOpenRecent={async (path) => {
                const file = await window.ave.readProject(path);
                setProjectPath(file.path);
                setProjectText(file.text);
                setUiMode("advanced");
                setActiveTab("editor");
              }}
            />
          )}
          {activeTab === "editor" && (
            <EditorMode
              project={project || null}
              assets={assets}
              assetReport={assetReport}
              previewPath={previewPath}
              realtimePreview={realtimePreview}
              interactivePreview={interactivePreview}
              previewTimeSeconds={previewTimeSeconds}
              setPreviewTimeSeconds={setPreviewTimeSeconds}
              previewQualityMode={previewQualityMode}
              setPreviewQualityMode={setPreviewQualityMode}
              previewScope={previewScope}
              setPreviewScope={setPreviewScope}
              previewSceneId={previewSceneId}
              setPreviewSceneId={setPreviewSceneId}
              preset={preset}
              exportFormat={exportFormat}
              qualityReport={qualityReport}
              onRealtimePreview={generateRealtimePreview}
              onInteractivePreview={generateInteractivePreview}
              onProjectChange={updateProject}
              onProjectPreviewChange={updateProjectAndRefreshPreview}
              onImport={importAssets}
              onAnalyze={runAssetIntelligence}
              onDropAsset={(asset) => project && updateProject(addAssetToFirstScene(project, asset))}
              onReplaceAsset={(assetKey) => { void replaceProjectAsset(assetKey); }}
              onFirstAiEdit={openFirstAiEditGuide}
              onAutosaveNow={() => { void autosaveNow(); }}
              onDuplicateProject={() => { void duplicateProjectForIteration(); }}
              versionCount={history.length}
              recoveryCount={recoveryPoints.length}
            />
          )}
          {activeTab === "aiStudio" && (
            <AiStudioMode
              prompt={prompt}
              setPrompt={setPrompt}
              contentMode={contentMode}
              setContentMode={setContentMode}
              contentTone={contentTone}
              setContentTone={setContentTone}
              generationReview={generationReview}
              pendingAiPlan={pendingAiPlan}
              generationLocks={generationLocks}
              notes={aiNotes}
              directorGoal={directorGoal}
              setDirectorGoal={setDirectorGoal}
              directorReport={directorReport}
              storyboard={storyboard}
              promptBuilderOpen={aiPromptBuilderOpen}
              setPromptBuilderOpen={setAiPromptBuilderOpen}
              onGenerate={generateFromPrompt}
              onYouTubeShort={generateYouTubeShort}
              onContentGenerate={() => generateContentMode("full")}
              onStudioGenerate={(studioPrompt, style, tasks) => {
                setPrompt(studioPrompt);
                setContentTone(style);
                void generateContentMode("full", buildAiStudioPrompt(studioPrompt, tasks), style);
              }}
              onAutonomousPipeline={runAutonomousPipeline}
              onContentRegenerate={(target) => generateContentMode(target)}
              onContentApprove={(section, statusValue) => approveGeneratedPlan(section, statusValue)}
              onContentLock={lockGenerationSection}
              onApplyPendingPlan={applyPendingAiPlan}
              onExplain={() => project && setAiNotes(explainProject(project))}
              onRepair={repair}
              onDirector={runDirector}
              onSuggestTransitions={() => project && updateProject(suggestBetterTransitions(project))}
              onAddScene={() => project && updateProject(addScene(project))}
              onCaptions={generateCaptionsFromTranscript}
              onResolveBroll={resolveBroll}
              onStoryboard={buildStoryboard}
              onAnalyzeAssets={runAssetIntelligence}
            />
          )}
          {activeTab === "captionsMode" && (
            <CaptionsMode
              project={project || null}
              onProjectChange={updateProject}
              onAutoCaption={generateCaptionsFromTranscript}
              onImportCaptions={importCaptionFile}
              onPreview={() => setActiveTab("editor")}
              onStyle={applyCaptionPreset}
              onBurnIn={() => setStatus("Burn-in captions are controlled by caption layers in the JSON timeline.")}
            />
          )}
          {activeTab === "templatesMode" && (
            <TemplatesMode
              beginnerTemplates={beginnerTemplates}
              templates={engine?.templates || []}
              onPreviewTemplate={previewTemplate}
              onApplyTemplate={applyTemplatePlan}
              onCustomizeTemplate={(template) => openTemplateCustomizer(template)}
              onDuplicateTemplate={(template) => openTemplateCustomizer(template, true)}
              onSaveTemplate={saveTemplatePreset}
            />
          )}
          {activeTab === "reviewMode" && (
            <FinalReviewMode
              project={project || null}
              previewPath={previewPath}
              checks={finalReviewChecks}
              finalPreflight={finalPreflightReport}
              finalReviewStatus={finalReviewStatus}
              preset={preset}
              exportFormat={exportFormat}
              onRunPreflight={() => { void runFinalPreflight(true); }}
              onQualityCheck={runQualityCheck}
              onWatch={() => setWatchFinalCutOpen(true)}
              onLooksGood={approveFinalReview}
              onNeedsChanges={needsFinalReviewChanges}
              onExportNow={() => { setFinalReviewStatus("approved"); void render("Final render", "final"); }}
              onRepairPreflight={(mode, issueId) => repairFinalPreflight(mode, issueId)}
              onPreview={() => {
                setPreviewScope("full");
                setPreviewQualityMode("final_sim");
                void generateInteractivePreview();
              }}
            />
          )}
          {activeTab === "exportMode" && (
            <ExportMode
              preset={preset}
              setPreset={setPreset}
              exportFormat={exportFormat}
              setExportFormat={setExportFormat}
              quality={quality}
              setQuality={setQuality}
              cache={useCache}
              setCache={setUseCache}
              resume={resume}
              setResume={setResume}
              gpu={gpu}
              setGpu={setGpu}
              logs={renderLogs}
              renderQueueItems={renderQueueItems}
              project={project || null}
              finalPreflight={finalPreflightReport}
              onPreflight={() => { void runFinalPreflight(true); }}
              onRepairPreflight={(mode, issueId) => repairFinalPreflight(mode, issueId)}
              onPreview={() => render("Preview render", "preview")}
              onFinal={() => render("Final render", "final")}
              onPauseQueue={async () => setRenderQueueItems(await window.ave.pauseRenderQueue())}
              onResumeQueue={async () => setRenderQueueItems(await window.ave.resumeRenderQueue())}
              onCancelJob={async (runId) => setRenderQueueItems(await window.ave.cancelRenderJob({ runId }))}
              onRetryJob={async (runId) => setRenderQueueItems(await window.ave.retryRenderJob({ runId }))}
              onOpenOutput={() => window.ave.openOutputFolder()}
            />
          )}
          {activeTab === "diagnostics" && (
            <DiagnosticsMode
              projectText={projectText}
              projectPath={projectPath}
              engineReady={Boolean(engine)}
              validation={validation}
              onJsonChange={setProjectText}
              onEditorMount={onEditorMount}
              logs={renderLogs}
              activityFeed={activityFeed}
              appError={appError}
              workflow={
                <WorkflowPane
                  projectPath={projectPath}
                  history={history}
                  projectHealth={projectHealth}
                  plugins={plugins}
                  renderQueueItems={renderQueueItems}
                  onExportPackage={async () => {
                    const result = await window.ave.exportPackage({ text: projectText, projectPath });
                    setStatus(result.ok ? `Package exported: ${result.path}` : result.stdout || "Package export canceled");
                  }}
                  onOpenPackage={async () => {
                    const file = await window.ave.openPackage();
                    if (!file) return;
                    setProjectPath(file.path);
                    setProjectText(file.text);
                    setStatus(`Opened package project ${file.name}`);
                  }}
                  onRollback={async (versionId) => {
                    if (!projectPath) return;
                    await captureAutosave("before_version_restore", projectText, projectPath);
                    const file = await window.ave.rollbackHistory({ projectPath, versionId });
                    setProjectText(file.text);
                    setStatus(`Rolled back to ${versionId}`);
                  }}
                  onDuplicateVersion={duplicateVersion}
                  onCompareVersion={compareVersion}
                  onHealthCheck={runProjectHealthCheck}
                  onRefreshHistory={async () => projectPath && setHistory(await window.ave.listHistory({ projectPath }))}
                  onPauseQueue={async () => setRenderQueueItems(await window.ave.pauseRenderQueue())}
                  onResumeQueue={async () => setRenderQueueItems(await window.ave.resumeRenderQueue())}
                  onCancelJob={async (runId) => setRenderQueueItems(await window.ave.cancelRenderJob({ runId }))}
                  onRetryJob={async (runId) => setRenderQueueItems(await window.ave.retryRenderJob({ runId }))}
                  onPrioritizeJob={async (runId, priority) => setRenderQueueItems(await window.ave.prioritizeRenderJob({ runId, priority }))}
                  onInitPlugin={async (name, type) => {
                    await window.ave.initPlugin({ name, type });
                    setPlugins(await window.ave.listPlugins());
                  }}
                />
              }
            />
          )}

          {activeTab === "beginner" && (
            <BeginnerAutoTemplatePane
              form={beginnerForm}
              setForm={setBeginnerForm}
              templates={beginnerTemplates}
              summary={beginnerSummary}
              previewPath={previewPath}
              adaptiveMemory={adaptiveMemory}
              onApplyAdaptiveDefaults={() => { void refreshAdaptiveMemory(true); }}
              onPickMedia={async () => {
                const path = await window.ave.beginnerPickMedia();
                if (path) {
                  setBeginnerForm((form) => ({ ...form, mediaFile: path }));
                  void recordAdaptiveEvent({ event: "media_imported", mediaPath: path, note: "beginner_media" });
                }
              }}
              onPickImageFolder={async () => {
                const path = await window.ave.beginnerPickImageFolder();
                if (path) {
                  setBeginnerForm((form) => ({ ...form, imageFolder: path }));
                  void recordAdaptiveEvent({ event: "media_imported", mediaPath: path, note: "image_folder" });
                }
              }}
              onPickAssetFolder={async () => {
                const path = await window.ave.beginnerPickAssetFolder();
                if (path) {
                  setBeginnerForm((form) => ({ ...form, assetFolder: path }));
                  void recordAdaptiveEvent({ event: "media_imported", mediaPath: path, note: "asset_folder" });
                }
              }}
              onPickMusic={async () => {
                const path = await window.ave.beginnerPickMusic();
                if (path) {
                  setBeginnerForm((form) => ({ ...form, musicPath: path }));
                  void recordAdaptiveEvent({ event: "music_imported", mediaPath: path, note: "beginner_music" });
                }
              }}
              onPickLogo={async () => {
                const path = await window.ave.beginnerPickLogo();
                if (path) {
                  setBeginnerForm((form) => ({ ...form, logoPath: path }));
                  void recordAdaptiveEvent({ event: "logo_imported", mediaPath: path, note: "beginner_logo" });
                }
              }}
              onPreview={() => generateBeginnerAutoVideo("preview")}
              onFinal={() => generateBeginnerAutoVideo("final")}
              onDuplicateProject={() => { void duplicateProjectForIteration(); }}
              onAdvanced={() => { setUiMode("advanced"); setActiveTab("preview"); }}
            />
          )}
          {activeTab === "json" && (
            <JsonEditor text={projectText} schemaReady={Boolean(engine)} onChange={setProjectText} onMount={onEditorMount} validation={validation} />
          )}
          {activeTab === "timeline" && project && (
            <VisualTimeline
              project={project}
              onProjectChange={updateProject}
              interactivePreview={interactivePreview}
              onAutosaveNow={() => { void autosaveNow(); }}
              onDuplicateProject={() => { void duplicateProjectForIteration(); }}
              versionCount={history.length}
              recoveryCount={recoveryPoints.length}
            />
          )}
          {activeTab === "preview" && (
            <div className="editor-workspace">
              <PreviewWindow
                project={project || null}
                previewPath={previewPath}
                realtimePreview={realtimePreview}
                interactivePreview={interactivePreview}
                previewTimeSeconds={previewTimeSeconds}
                setPreviewTimeSeconds={setPreviewTimeSeconds}
                previewQualityMode={previewQualityMode}
                setPreviewQualityMode={setPreviewQualityMode}
                previewScope={previewScope}
                setPreviewScope={setPreviewScope}
                previewSceneId={previewSceneId}
                setPreviewSceneId={setPreviewSceneId}
                preset={preset}
                exportFormat={exportFormat}
                qualityReport={qualityReport}
                duration={project ? totalTimelineDuration(project) : 0}
                onRealtimePreview={generateRealtimePreview}
                onInteractivePreview={generateInteractivePreview}
                onProjectChange={updateProject}
                onProjectPreviewChange={updateProjectAndRefreshPreview}
              />
              {project ? (
                <VisualTimeline
                  project={project}
                  onProjectChange={updateProject}
                  interactivePreview={interactivePreview}
                  onAutosaveNow={() => { void autosaveNow(); }}
                  onDuplicateProject={() => { void duplicateProjectForIteration(); }}
                  versionCount={history.length}
                  recoveryCount={recoveryPoints.length}
                />
              ) : <div className="timeline-pane panel"><span className="muted">Import media or open a project to show the timeline.</span></div>}
            </div>
          )}
          {activeTab === "assets" && project && (
            <AssetLibrary
              project={project}
              assets={assets}
              assetReport={assetReport}
              onImport={importAssets}
              onAnalyze={runAssetIntelligence}
              onDropAsset={(asset) => updateProject(addAssetToFirstScene(project, asset))}
              onProjectChange={updateProject}
              onReplaceAsset={(assetKey) => { void replaceProjectAsset(assetKey); }}
              onFirstAiEdit={openFirstAiEditGuide}
            />
          )}
          {activeTab === "director" && (
            <DirectorWorkspace
              goal={directorGoal}
              setGoal={setDirectorGoal}
              report={directorReport}
              onRun={runDirector}
              onResolveBroll={resolveBroll}
              onStoryboard={buildStoryboard}
              onAnalyzeAssets={runAssetIntelligence}
            />
          )}
          {activeTab === "storyboard" && (
            <StoryboardPane storyboard={storyboard} onGenerate={buildStoryboard} />
          )}
          {activeTab === "workflow" && (
            <WorkflowPane
              projectPath={projectPath}
              history={history}
              projectHealth={projectHealth}
              plugins={plugins}
              renderQueueItems={renderQueueItems}
              onExportPackage={async () => {
                const result = await window.ave.exportPackage({ text: projectText, projectPath });
                setStatus(result.ok ? `Package exported: ${result.path}` : result.stdout || "Package export canceled");
              }}
              onOpenPackage={async () => {
                const file = await window.ave.openPackage();
                if (!file) return;
                setProjectPath(file.path);
                setProjectText(file.text);
                setStatus(`Opened package project ${file.name}`);
              }}
              onRollback={async (versionId) => {
                if (!projectPath) return;
                await captureAutosave("before_version_restore", projectText, projectPath);
                const file = await window.ave.rollbackHistory({ projectPath, versionId });
                setProjectText(file.text);
                setStatus(`Rolled back to ${versionId}`);
              }}
              onDuplicateVersion={duplicateVersion}
              onCompareVersion={compareVersion}
              onHealthCheck={runProjectHealthCheck}
              onRefreshHistory={async () => projectPath && setHistory(await window.ave.listHistory({ projectPath }))}
              onPauseQueue={async () => setRenderQueueItems(await window.ave.pauseRenderQueue())}
              onResumeQueue={async () => setRenderQueueItems(await window.ave.resumeRenderQueue())}
              onCancelJob={async (runId) => setRenderQueueItems(await window.ave.cancelRenderJob({ runId }))}
              onRetryJob={async (runId) => setRenderQueueItems(await window.ave.retryRenderJob({ runId }))}
              onPrioritizeJob={async (runId, priority) => setRenderQueueItems(await window.ave.prioritizeRenderJob({ runId, priority }))}
              onInitPlugin={async (name, type) => {
                await window.ave.initPlugin({ name, type });
                setPlugins(await window.ave.listPlugins());
              }}
            />
          )}
          {activeTab === "product" && (
            <ProductPane
              project={project || null}
              settings={settings}
              realtimePreview={realtimePreview}
              previewTimeSeconds={previewTimeSeconds}
              setPreviewTimeSeconds={setPreviewTimeSeconds}
              previewSceneId={previewSceneId}
              setPreviewSceneId={setPreviewSceneId}
              previewQualityMode={previewQualityMode}
              setPreviewQualityMode={setPreviewQualityMode}
              previewLayerMode={previewLayerMode}
              setPreviewLayerMode={setPreviewLayerMode}
              qualityReport={qualityReport}
              manifestReport={manifestReport}
              repurposeReport={repurposeReport}
              postingPackageReport={postingPackageReport}
              postExportReview={postExportReview}
              postExportTemplate={postExportTemplate}
              postExportVariants={postExportVariants}
              postExportNote={postExportNote}
              templatePacks={templatePacks}
              recoveryPoints={recoveryPoints}
              renderedVideoPath={previewPath}
              socialTargets={socialTargets}
              setSocialTargets={setSocialTargets}
              onRealtimePreview={generateRealtimePreview}
              onQualityCheck={runQualityCheck}
              onManifest={buildManifest}
              onReformat={reformatForSocial}
              onRepurpose={repurposeContent}
              onPostPackage={createPostingPackage}
              onPostExportReview={reviewPostExport}
              onQuickReExport={quickPostExportReexport}
              onSaveReusableTemplate={savePostExportTemplate}
              onCreatePostExportVariants={createPostExportVariants}
              onSavePostExportNote={savePostExportNote}
              onCreateBrandKit={createBrandKit}
              onApplyBrandKit={applyBrandKit}
              onExportTemplate={async (template) => {
                const result = await window.ave.exportTemplatePack({ template });
                setStatus(result.ok ? `Template exported: ${result.path}` : result.stdout || "Template export canceled");
              }}
              onInstallTemplate={async () => {
                await window.ave.installTemplatePack();
                setTemplatePacks(await window.ave.listTemplatePacks());
                setStatus("Template pack installed");
              }}
              onSaveSettings={saveAppSettings}
              onAutosaveNow={autosaveNow}
              onRefreshRecovery={refreshRecovery}
              onRestoreRecovery={restoreRecoveryPoint}
              hardeningStatus={hardeningStatus}
              onRefreshHardening={refreshHardeningStatus}
              workflowDashboard={workflowDashboard}
              onRefreshWorkflowDashboard={refreshWorkflowDashboard}
              frictionReport={frictionReport}
              onRefreshFrictionReport={refreshFrictionReport}
              adaptiveMemory={adaptiveMemory}
              onRefreshAdaptiveMemory={() => { void refreshAdaptiveMemory(false); }}
              onApplyAdaptiveDefaults={() => { void refreshAdaptiveMemory(true); }}
              feedbackAnalysis={feedbackAnalysis}
              feedbackReview={feedbackReview}
              creatorIdentity={creatorIdentity}
              evolutionReport={evolutionReport}
              onFeedbackAnalyze={runFeedbackAnalysis}
              onFeedbackReview={saveFeedbackReview}
              onFeedbackLearn={learnCreatorIdentity}
              onEvolutionReport={refreshEvolutionReport}
              onOpenDocs={openLocalDocs}
            />
          )}
        </section>

        <aside className="right-rail" aria-hidden={!rightRailOpen}>
          <div className="inspector-title">
            <strong>Inspector</strong>
            <button title="Hide inspector" onClick={() => setRightRailOpen(false)}><X size={14} /></button>
          </div>
          <InspectorContextPanel
            activeTab={activeTab}
            project={project || null}
            preset={preset}
            exportFormat={exportFormat}
            previewSceneId={previewSceneId}
            duration={project ? totalTimelineDuration(project) : 0}
            onJson={() => setAppModal("json")}
            onExport={() => setAppModal("export")}
          />
          <SuggestedEditsPanel
            suggestions={visibleSuggestedEdits}
            savedSuggestions={savedSuggestedEdits}
            disabledTypes={disabledSuggestionTypes}
            onApply={applyProactiveSuggestion}
            onIgnore={ignoreSuggestedEdit}
            onSave={saveSuggestedEdit}
            onDisableType={disableSuggestionType}
            onEnableType={(action) => setDisabledSuggestionTypes((types) => types.filter((type) => type !== action))}
          />
          <TaskManagerPanel
            tasks={managedTasks}
            systemMetrics={systemMetrics}
            onPause={(task) => { void pauseManagedTask(task); }}
            onResume={(task) => { void resumeManagedTask(task); }}
            onCancel={(task) => { void cancelManagedTask(task); }}
            onClearCompleted={clearCompletedManagedTasks}
            onOpenRenderProgress={() => setAppModal("renderProgress")}
          />
          <details className="rail-section" open={activeTab === "director"}>
            <summary><Bot size={15} /> AI Assistant</summary>
            <AiPanel
              prompt={prompt}
              setPrompt={setPrompt}
              contentMode={contentMode}
              setContentMode={setContentMode}
              contentTone={contentTone}
              setContentTone={setContentTone}
              generationReview={generationReview}
              generationLocks={generationLocks}
              notes={aiNotes}
              onGenerate={generateFromPrompt}
              onYouTubeShort={generateYouTubeShort}
              onContentGenerate={() => generateContentMode("full")}
              onAutonomousPipeline={runAutonomousPipeline}
              onContentRegenerate={(target) => generateContentMode(target)}
              onContentApprove={(section, statusValue) => approveGeneratedPlan(section, statusValue)}
              onContentLock={lockGenerationSection}
              onExplain={() => project && setAiNotes(explainProject(project))}
              onRepair={repair}
              onDirector={runDirector}
              onSuggestTransitions={() => project && updateProject(suggestBetterTransitions(project))}
              onAddScene={() => project && updateProject(addScene(project))}
              onCaptions={generateCaptionsFromTranscript}
            />
          </details>
          <details className="rail-section">
            <summary><Sparkles size={15} /> Creative Coach</summary>
            <ProactiveAssistantPanel
              analysis={proactiveAnalysis}
              backgroundImprovements={backgroundImprovements}
              muted={proactiveMuted}
              onMute={setProactiveMuted}
              onApplySuggestion={applyProactiveSuggestion}
              onApplyImprovement={applyBackgroundImprovement}
              onDismissImprovement={(id) => setBackgroundImprovements((items) => items.filter((item) => item.id !== id))}
            />
          </details>
          <details className="rail-section" open={activeTab === "product" || activeTab === "preview"}>
            <summary><MonitorPlay size={15} /> Render & Export</summary>
            <RenderPanel
              preset={preset}
              setPreset={setPreset}
              exportFormat={exportFormat}
              setExportFormat={setExportFormat}
              quality={quality}
              setQuality={setQuality}
              cache={useCache}
              setCache={setUseCache}
              resume={resume}
              setResume={setResume}
              gpu={gpu}
              setGpu={setGpu}
              logs={renderLogs}
              renderQueueItems={renderQueueItems}
              project={project || null}
              finalPreflight={finalPreflightReport}
              onPreflight={() => { void runFinalPreflight(true); }}
              onRepairPreflight={(mode, issueId) => repairFinalPreflight(mode, issueId)}
              onPreview={() => render("Preview render", "preview")}
              onFinal={() => render("Final render", "final")}
              onPauseQueue={async () => setRenderQueueItems(await window.ave.pauseRenderQueue())}
              onResumeQueue={async () => setRenderQueueItems(await window.ave.resumeRenderQueue())}
              onCancelJob={async (runId) => setRenderQueueItems(await window.ave.cancelRenderJob({ runId }))}
              onRetryJob={async (runId) => setRenderQueueItems(await window.ave.retryRenderJob({ runId }))}
              onOpenOutput={() => window.ave.openOutputFolder()}
            />
          </details>
        </aside>
      </main>

      <EditorModal
        modal={appModal}
        onClose={() => setAppModal(null)}
        projectText={projectText}
        projectPath={projectPath}
        project={project || null}
        appError={appError}
        jsonParseError={parsed.error}
        processing={processing}
        engineReady={Boolean(engine)}
        validation={validation}
        onJsonChange={setProjectText}
        onEditorMount={onEditorMount}
        prompt={prompt}
        setPrompt={setPrompt}
        contentMode={contentMode}
        setContentMode={setContentMode}
        contentTone={contentTone}
        setContentTone={setContentTone}
        generationReview={generationReview}
        pendingAiPlan={pendingAiPlan}
        generationLocks={generationLocks}
        aiNotes={aiNotes}
        startupRecovery={startupRecovery}
        recoveryPoints={recoveryPoints}
        versionComparison={versionComparison}
        templateCustomizer={templateCustomizer}
        setTemplateCustomizer={setTemplateCustomizer}
        onApplyTemplateCustomization={applyTemplateCustomization}
        onSaveTemplateCustomization={saveTemplateCustomization}
        onImport={importAssets}
        onOpenProject={openProject}
        onNewProject={() => { void newProjectSafely("preview"); }}
        onSave={saveProject}
        onSaveAs={saveAs}
        onGenerate={generateFromPrompt}
        onYouTubeShort={generateYouTubeShort}
        onContentGenerate={() => generateContentMode("full")}
        onAutonomousPipeline={runAutonomousPipeline}
        onContentRegenerate={(target) => generateContentMode(target)}
        onContentApprove={(section, statusValue) => approveGeneratedPlan(section, statusValue)}
        onContentLock={lockGenerationSection}
        onApplyPendingPlan={applyPendingAiPlan}
        onEditPendingPlan={editPendingAiPlan}
        onRegeneratePendingPlan={() => { void regeneratePendingAiPlan(); }}
        onSavePendingPlan={savePendingAiPlanAsTemplate}
        onCancelPendingPlan={() => { setPendingAiPlan(null); setAppModal(null); setStatus("AI plan canceled"); }}
        onRestoreStartupRecovery={restoreStartupRecovery}
        onRestoreRecoveryPoint={restoreRecoveryPoint}
        onDismissStartupRecovery={() => { setStartupRecovery(null); setAppModal(null); setStatus("Recovery dismissed"); }}
        onExplain={() => project && setAiNotes(explainProject(project))}
        onRepair={repair}
        onDirector={runDirector}
        onSuggestTransitions={() => project && updateProject(suggestBetterTransitions(project))}
        onAddScene={() => project && updateProject(addScene(project))}
        onCaptions={generateCaptionsFromTranscript}
        onCaptionStyle={(style) => {
          setStatus(`Caption style selected: ${style}. Use Auto-caption or caption layers to apply it to the JSON timeline.`);
          setAppModal(null);
        }}
        templates={engine?.templates || []}
        beginnerTemplates={beginnerTemplates}
        onTemplate={createFromTemplate}
        onBeginnerTemplate={(template) => { setBeginnerForm((form) => ({ ...form, template })); setUiMode("beginner"); setActiveTab("beginner"); setAppModal(null); }}
        preset={preset}
        setPreset={setPreset}
        exportFormat={exportFormat}
        setExportFormat={setExportFormat}
        quality={quality}
        setQuality={setQuality}
        cache={useCache}
        setCache={setUseCache}
        resume={resume}
        setResume={setResume}
        gpu={gpu}
        setGpu={setGpu}
        logs={renderLogs}
        renderQueueItems={renderQueueItems}
        systemMetrics={systemMetrics}
        finalPreflight={finalPreflightReport}
        onPreflight={() => { void runFinalPreflight(true); }}
        onRepairPreflight={(mode, issueId) => repairFinalPreflight(mode, issueId)}
        onPreview={() => render("Preview render", "preview")}
        onFinal={() => render("Final render", "final")}
        onPauseQueue={async () => setRenderQueueItems(await window.ave.pauseRenderQueue())}
        onResumeQueue={async () => setRenderQueueItems(await window.ave.resumeRenderQueue())}
        onCancelJob={async (runId) => setRenderQueueItems(await window.ave.cancelRenderJob({ runId }))}
        onRetryJob={async (runId) => setRenderQueueItems(await window.ave.retryRenderJob({ runId }))}
        onOpenOutput={() => window.ave.openOutputFolder()}
        settings={settings}
        setSettings={setSettings}
        onSaveSettings={() => saveAppSettings(settings)}
        leftRailOpen={leftRailOpen}
        setLeftRailOpen={setLeftRailOpen}
        rightRailOpen={rightRailOpen}
        setRightRailOpen={setRightRailOpen}
        onApplyWorkspacePreset={applyWorkspacePreset}
        onSaveWorkspaceLayout={saveWorkspaceLayout}
        onPopOutPanel={popOutWorkspacePanel}
        onCompleteOnboarding={completeOnboarding}
        onPickExportFolder={pickDefaultExportFolder}
        onRunSystemCheck={refreshHardeningStatus}
        onShowShortcuts={() => setAppModal("shortcuts")}
        hardeningStatus={hardeningStatus}
        activityFeed={activityFeed}
        onOpenDocs={openLocalDocs}
      />

      <RenderActivityPopup
        processing={processing}
        activityFeed={activityFeed}
        renderQueueItems={renderQueueItems}
        logs={renderLogs}
        systemMetrics={systemMetrics}
        gpuEnabled={gpu}
        minimized={renderActivityMinimized}
        onToggleMinimized={() => setRenderActivityMinimized((value) => !value)}
        onOpenDetails={() => setAppModal("renderProgress")}
        onPause={async () => setRenderQueueItems(await window.ave.pauseRenderQueue())}
        onResume={async () => setRenderQueueItems(await window.ave.resumeRenderQueue())}
        onCancel={async (runId) => setRenderQueueItems(await window.ave.cancelRenderJob({ runId }))}
      />

      {watchFinalCutOpen && (
        <WatchFinalCutOverlay
          previewPath={previewPath}
          project={project || null}
          checks={finalReviewChecks}
          onClose={() => setWatchFinalCutOpen(false)}
          onAddNote={addFinalReviewNote}
          onMarkIssue={markFinalReviewIssue}
          onApprove={approveFinalReview}
          onExportNow={() => { setWatchFinalCutOpen(false); setFinalReviewStatus("approved"); void render("Final render", "final"); }}
        />
      )}

      <footer className="statusbar">
        <span>{status}</span>
        {parsed.error && <span className="error">JSON parse error: {parsed.error}</span>}
        {project && <span>{project.timeline?.length || 0} scenes | {Object.keys(project.assets || {}).length} assets | {totalTimelineDuration(project).toFixed(1)}s</span>}
      </footer>
    </div>
  );
}

function WorkflowContextHeader({ context }: { context: WorkflowContext }) {
  return (
    <header className="context-header">
      <nav className="breadcrumb-row" aria-label="Workflow breadcrumb">
        {context.breadcrumbs.map((crumb, index) => (
          <span key={`${crumb}-${index}`} className={index === context.breadcrumbs.length - 1 ? "current" : undefined}>
            {index > 0 && <span className="breadcrumb-separator">/</span>}
            {crumb}
          </span>
        ))}
      </nav>
      <div className="context-title-row">
        <div>
          <h2>{context.title}</h2>
          <p>{context.description}</p>
        </div>
        {context.meta.length > 0 && (
          <div className="context-meta" aria-label="Current workflow details">
            {context.meta.map((item) => <span key={item}>{item}</span>)}
          </div>
        )}
      </div>
    </header>
  );
}

function NotificationCenter({
  notifications,
  onOpenAction,
  onDismiss,
  onClear,
  onClose
}: {
  notifications: AppNotification[];
  onOpenAction: (action?: NotificationAction) => void;
  onDismiss: (id: string) => void;
  onClear: () => void;
  onClose: () => void;
}) {
  return (
    <aside className="notification-center" role="status" aria-live="polite">
      <div className="notification-head">
        <div>
          <strong>Notification Center</strong>
          <span>{notifications.length ? `${notifications.length} recent update${notifications.length === 1 ? "" : "s"}` : "No notifications"}</span>
        </div>
        <button title="Close notifications" onClick={onClose}><X size={14} /></button>
      </div>
      <div className="notification-list">
        {notifications.length === 0 && (
          <div className="notification-empty">
            <Bell size={18} />
            <span>Finished exports, AI plans, captions, warnings, and failures will show up here quietly.</span>
          </div>
        )}
        {notifications.map((notification) => (
          <article className={`notification-card ${notification.kind} ${notification.read ? "read" : "unread"}`} key={notification.id}>
            <button className="notification-main" onClick={() => onOpenAction(notification.action)}>
              <strong>{notification.title}</strong>
              <span>{notification.message}</span>
              {notification.detail && <small>{notification.detail}</small>}
            </button>
            <div className="notification-meta">
              <span>{notification.time}</span>
              {notification.action && <button onClick={() => onOpenAction(notification.action)}>Open</button>}
              <button title="Dismiss" onClick={() => onDismiss(notification.id)}><X size={12} /></button>
            </div>
          </article>
        ))}
      </div>
      {notifications.length > 0 && (
        <div className="notification-actions">
          <button onClick={onClear}>Clear all</button>
          <button onClick={onClose}>Done</button>
        </div>
      )}
    </aside>
  );
}

function FinalReviewMode({
  project,
  previewPath,
  checks,
  finalPreflight,
  finalReviewStatus,
  preset,
  exportFormat,
  onRunPreflight,
  onQualityCheck,
  onWatch,
  onLooksGood,
  onNeedsChanges,
  onExportNow,
  onRepairPreflight,
  onPreview
}: {
  project: ProjectData | null;
  previewPath: string | null;
  checks: FinalReviewCheck[];
  finalPreflight: FinalPreflightReport | null;
  finalReviewStatus: FinalReviewStatus;
  preset: string;
  exportFormat: string;
  onRunPreflight: () => void;
  onQualityCheck: () => void;
  onWatch: () => void;
  onLooksGood: () => void;
  onNeedsChanges: () => void;
  onExportNow: () => void;
  onRepairPreflight: (mode: string, issueId?: string | null) => void;
  onPreview: () => void;
}) {
  const counts = {
    error: checks.filter((check) => check.severity === "error").length,
    warning: checks.filter((check) => check.severity === "warning").length,
    info: checks.filter((check) => check.severity === "info").length,
    pass: checks.filter((check) => check.severity === "pass").length
  };
  const blockers = counts.error + checks.filter((check) => check.severity === "warning").length;
  const reviewMeta = project?.metadata?.previewReview as Record<string, unknown> | undefined;
  const markers = Array.isArray(reviewMeta?.markers) ? reviewMeta.markers as Array<Record<string, unknown>> : [];
  const notes = Array.isArray(reviewMeta?.notes) ? reviewMeta.notes as Array<Record<string, unknown>> : [];
  return (
    <div className="mode-page final-review-mode">
      <section className="wide-panel review-hero-panel">
        <div>
          <span className="eyebrow">Quality Control</span>
          <h2><CheckCircle2 size={18} /> Final Review Before Export</h2>
          <p className="muted">Run preflight, watch the final cut without editor clutter, and approve the edit before committing render time.</p>
        </div>
        <div className={`review-verdict ${finalReviewStatus}`}>
          <strong>{finalReviewStatus === "approved" ? "Looks good" : finalReviewStatus === "needs_changes" ? "Needs changes" : "Pending review"}</strong>
          <span>{counts.error} errors / {counts.warning} warnings / {counts.pass} passing</span>
        </div>
      </section>

      <section className="wide-panel">
        <div className="review-actions large">
          <button onClick={onPreview}><MonitorPlay size={15} /> Generate Final-Quality Preview</button>
          <button onClick={onRunPreflight}><CheckCircle2 size={15} /> Run Review Checks</button>
          <button onClick={onQualityCheck}><Wand2 size={15} /> Analyze Video Quality</button>
          <button className="primary-create" onClick={onWatch} disabled={!previewPath}><Maximize2 size={15} /> Watch Final Cut</button>
        </div>
        {!previewPath && <p className="muted">Generate a preview first to use Watch Final Cut mode at final review quality.</p>}
      </section>

      <section className="wide-panel">
        <div className="review-header">
          <h2>Review Checks</h2>
          <span className={finalPreflight?.ready ? "status-pill ok" : finalPreflight ? "status-pill warn" : "status-pill"}>{finalPreflight ? (finalPreflight.ready ? "preflight passed" : "preflight needs review") : "preflight not run"}</span>
        </div>
        <div className="review-check-grid">
          {checks.map((check) => (
            <article className={`review-check-card ${check.severity}`} key={check.id}>
              <strong>{check.title}</strong>
              <span>{check.detail}</span>
              {check.suggestion && <small>{check.suggestion}</small>}
              <div>
                <em>{check.category}</em>
                {check.sceneId && <em>{check.sceneId}</em>}
                {typeof check.time === "number" && <em>{formatTimestamp(check.time)}</em>}
              </div>
            </article>
          ))}
        </div>
        {finalPreflight?.issues?.length ? (
          <div className="preflight-issues review-preflight-issues">
            {finalPreflight.issues.map((issue) => (
              <div className={`preflight-issue ${issue.severity}`} key={issue.id}>
                <strong>{issue.category.replace(/_/g, " ")}</strong>
                <span>{issue.message}</span>
                <small>{issue.suggestion || "Review before export."}</small>
                <div className="button-grid compact">
                  {issue.safeAutoFix && !issue.accepted && <button onClick={() => onRepairPreflight("selected", issue.id)}><Wand2 size={14} /> Approve fix</button>}
                  {!issue.accepted && <button onClick={() => onRepairPreflight("ignore", issue.id)}><CheckCircle2 size={14} /> Accept as intentional</button>}
                  {issue.accepted && <span className="status-pill ok">accepted</span>}
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section className="wide-panel final-review-summary">
        <h2>Final Approval</h2>
        <div className="ai-plan-summary-grid">
          <span>platform <strong>{friendlyPresetName(preset)}</strong></span>
          <span>format <strong>{exportFormat.toUpperCase()}</strong></span>
          <span>markers <strong>{markers.length}</strong></span>
          <span>notes <strong>{notes.length}</strong></span>
          <span>readiness <strong>{blockers ? "review needed" : "ready"}</strong></span>
          <span>duration <strong>{project ? `${totalTimelineDuration(project).toFixed(1)}s` : "0.0s"}</strong></span>
        </div>
        <div className="review-actions large">
          <button onClick={onLooksGood}><CheckCircle2 size={15} /> Looks good</button>
          <button onClick={onNeedsChanges}><Pencil size={15} /> Needs changes</button>
          <button className="primary-create" onClick={onExportNow} disabled={counts.error > 0}><Download size={15} /> Export now</button>
        </div>
        {counts.error > 0 && <p className="muted">Export now is blocked until critical review errors are handled or accepted through preflight.</p>}
      </section>
    </div>
  );
}

function WatchFinalCutOverlay({
  previewPath,
  project,
  checks,
  onClose,
  onAddNote,
  onMarkIssue,
  onApprove,
  onExportNow
}: {
  previewPath: string | null;
  project: ProjectData | null;
  checks: FinalReviewCheck[];
  onClose: () => void;
  onAddNote: (text: string, time: number) => void;
  onMarkIssue: (type: PreviewMarkerType, note: string, time: number) => void;
  onApprove: () => void;
  onExportNow: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [note, setNote] = useState("");
  const [markerType, setMarkerType] = useState<PreviewMarkerType>("needs_cut");
  const currentTime = () => Number(videoRef.current?.currentTime || 0);
  const topWarnings = checks.filter((check) => check.severity === "error" || check.severity === "warning").slice(0, 4);
  function addNote() {
    onAddNote(note, currentTime());
    setNote("");
  }
  function markIssue() {
    onMarkIssue(markerType, note || markerType.replace(/_/g, " "), currentTime());
    setNote("");
  }
  return (
    <div className="watch-final-cut">
      <header>
        <div>
          <span className="eyebrow">Watch Final Cut</span>
          <strong>{project ? `${totalTimelineDuration(project).toFixed(1)}s final review` : "Final review"}</strong>
        </div>
        <div className="review-actions">
          <button onClick={onApprove}><CheckCircle2 size={14} /> Looks good</button>
          <button onClick={onExportNow}><Download size={14} /> Export now</button>
          <button onClick={onClose}><X size={14} /> Close</button>
        </div>
      </header>
      <main>
        <section className="watch-player-shell">
          {previewPath ? (
            <video ref={videoRef} src={window.ave.toFileUrl(previewPath)} controls autoPlay className="watch-player" />
          ) : (
            <div className="empty-preview">Generate a final-quality preview before watching the cut.</div>
          )}
        </section>
        <aside className="watch-review-panel">
          <h2>Mark While Watching</h2>
          <label>
            Issue type
            <select value={markerType} onChange={(event) => setMarkerType(event.target.value as PreviewMarkerType)}>
              {["needs_cut", "too_slow", "too_fast", "bad_caption", "bad_zoom", "bad_transition", "audio_issue", "keep"].map((type) => (
                <option key={type} value={type}>{type.replace(/_/g, " ")}</option>
              ))}
            </select>
          </label>
          <label>
            Note
            <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="caption too fast, black frame, audio spike..." />
          </label>
          <div className="review-actions">
            <button onClick={markIssue}><Scissors size={14} /> Mark issue</button>
            <button onClick={addNote}><Plus size={14} /> Add note</button>
          </div>
          <h3>Current Warnings</h3>
          <div className="watch-warning-list">
            {topWarnings.length === 0 && <span className="muted">No blocking review warnings right now.</span>}
            {topWarnings.map((check) => (
              <div className={`review-check-card ${check.severity}`} key={check.id}>
                <strong>{check.title}</strong>
                <span>{check.detail}</span>
              </div>
            ))}
          </div>
        </aside>
      </main>
    </div>
  );
}

function ProjectHub({
  projectTitle,
  recent,
  beginnerTemplates,
  renderQueueItems,
  quickCreate,
  setQuickCreate,
  guidedStep,
  onNewProject,
  onOpenProject,
  onImport,
  onTemplate,
  onAI,
  onBeginner,
  onQuickPickMedia,
  onQuickGenerate,
  onGuidedImport,
  onGuidedTemplates,
  onGuidedInstructions,
  onGuidedReview,
  onGuidedApply,
  onGuidedExport,
  onAdvancedTimeline,
  onAdvancedJson,
  onAdvancedLogs,
  onOpenRecent
}: {
  projectTitle: string;
  recent: RecentProject[];
  beginnerTemplates: BeginnerTemplateCard[];
  renderQueueItems: RenderQueueItem[];
  quickCreate: QuickCreateState;
  setQuickCreate: (value: QuickCreateState | ((value: QuickCreateState) => QuickCreateState)) => void;
  guidedStep: number;
  onNewProject: () => void;
  onOpenProject: () => void;
  onImport: () => void;
  onTemplate: () => void;
  onAI: () => void;
  onBeginner: () => void;
  onQuickPickMedia: () => void;
  onQuickGenerate: () => void;
  onGuidedImport: () => void;
  onGuidedTemplates: () => void;
  onGuidedInstructions: () => void;
  onGuidedReview: () => void;
  onGuidedApply: () => void;
  onGuidedExport: () => void;
  onAdvancedTimeline: () => void;
  onAdvancedJson: () => void;
  onAdvancedLogs: () => void;
  onOpenRecent: (path: string) => void;
}) {
  const quickStyles = ["clean", "gaming", "cinematic", "podcast", "educational", "hype"];
  const quickPlatforms = [
    ["shorts", "YouTube Short"],
    ["tiktok", "TikTok"],
    ["instagram_reels", "Reel"],
    ["youtube", "Normal Video"]
  ] as const;
  const guidedSteps = [
    ["Import media", onGuidedImport],
    ["Choose template", onGuidedTemplates],
    ["AI instructions", onGuidedInstructions],
    ["Preview AI plan", onGuidedReview],
    ["Apply to timeline", onGuidedApply],
    ["Export", onGuidedExport]
  ] as const;
  return (
    <div className="project-hub">
      <section className="hub-hero">
        <div>
          <span className="eyebrow">Local-first editor</span>
          <h1>{projectTitle}</h1>
          <p>Create, review, preview, and export from one structured workspace.</p>
        </div>
        <div className="hub-actions">
          <button onClick={onImport}><Import size={17} /> Import video</button>
          <button onClick={onAI}><Sparkles size={17} /> Ask AI to create video</button>
          <button onClick={onTemplate}><LayoutTemplate size={17} /> Start from template</button>
          <button onClick={onBeginner}><MonitorPlay size={17} /> New Auto Video</button>
          <button onClick={onNewProject}><Plus size={17} /> New project</button>
          <button onClick={onOpenProject}><FolderOpen size={17} /> Open project</button>
        </div>
      </section>
      <section className="creation-paths">
        <div className="creation-card quick-path">
          <span className="eyebrow">Recommended</span>
          <h2><Wand2 size={17} /> Make A Short</h2>
          <p className="muted">Upload a video, say what you want, and the app creates the hidden JSON, preview render, captions, timing, and export settings.</p>
          <button className="large-action upload-action" onClick={onQuickPickMedia}><Video size={16} /> {quickCreate.mediaFile ? "Change uploaded video" : "Upload video"}</button>
          <small className="path-file" title={quickCreate.mediaFile || ""}>{quickCreate.mediaFile || "No video selected yet"}</small>
          <label>
            Tell AI what to make
            <textarea
              value={quickCreate.prompt}
              onChange={(event) => setQuickCreate((current) => ({ ...current, prompt: event.target.value }))}
              placeholder="Make this into a YouTube Short."
            />
          </label>
          <details className="quick-options">
            <summary>Optional details</summary>
            <label>
              Platform
              <select value={quickCreate.platform} onChange={(event) => setQuickCreate((current) => ({ ...current, platform: event.target.value }))}>
                {quickPlatforms.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>
              Style
              <select value={quickCreate.style} onChange={(event) => setQuickCreate((current) => ({ ...current, style: event.target.value }))}>
                {quickStyles.map((style) => <option key={style} value={style}>{style.charAt(0).toUpperCase() + style.slice(1)}</option>)}
              </select>
            </label>
          </details>
          <button className="primary-create" onClick={onQuickGenerate}><Sparkles size={16} /> Generate YouTube Short</button>
        </div>

        <div className="creation-card guided-path">
          <span className="eyebrow">Path 2</span>
          <h2><ListVideo size={17} /> Guided Create</h2>
          <p className="muted">A simple six-step flow: media, template, AI instructions, plan review, timeline, export.</p>
          <div className="guided-step-list">
            {guidedSteps.map(([label, action], index) => (
              <button key={label} className={guidedStep >= index + 1 ? "active" : ""} onClick={action}>
                <strong>{index + 1}</strong>
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="creation-card advanced-path">
          <span className="eyebrow">Path 3</span>
          <h2><FileJson size={17} /> Advanced Create</h2>
          <p className="muted">Manual timeline, JSON editor, full inspector, render/debug logs, and diagnostics stay here.</p>
          <div className="button-grid compact">
            <button onClick={onAdvancedTimeline}><MonitorPlay size={15} /> Manual timeline</button>
            <button onClick={onAdvancedJson}><FileJson size={15} /> JSON editor</button>
            <button onClick={onAdvancedLogs}><Clock size={15} /> Render/debug logs</button>
            <button onClick={onBeginner}><Sparkles size={15} /> Beginner auto form</button>
          </div>
        </div>
      </section>
      <section className="hub-grid">
        <div className="wide-panel">
          <h2><Clock size={16} /> Recent Projects</h2>
          <div className="list">
            {recent.length === 0 && <span className="muted">Recent projects appear here after opening or saving.</span>}
            {recent.slice(0, 8).map((item) => (
              <button className="list-row" key={item.path} onClick={() => onOpenRecent(item.path)}>
                <strong>{item.name}</strong>
                <span>{item.path}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="wide-panel">
          <h2><LayoutTemplate size={16} /> Starter Templates</h2>
          <div className="template-modal-grid compact">
            {beginnerTemplates.slice(0, 6).map((template) => (
              <button key={template.key} onClick={onTemplate}>
                <strong>{template.name}</strong>
                <span>{template.platform} / {template.aspectRatio}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="wide-panel">
          <h2><MonitorPlay size={16} /> Render Queue</h2>
          <div className="list">
            {renderQueueItems.length === 0 && <span className="muted">No active renders.</span>}
            {renderQueueItems.slice(0, 5).map((job) => (
              <div className="queue-row" key={job.runId}>
                <span>{job.label}</span>
                <small className={job.status}>{job.status}</small>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function EditorMode({
  project,
  assets,
  assetReport,
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
  onRealtimePreview,
  onInteractivePreview,
  onProjectChange,
  onProjectPreviewChange,
  onImport,
  onAnalyze,
  onDropAsset,
  onReplaceAsset,
  onFirstAiEdit,
  onAutosaveNow,
  onDuplicateProject,
  versionCount,
  recoveryCount
}: {
  project: ProjectData | null;
  assets: AssetCheck[];
  assetReport: Record<string, unknown> | null;
  previewPath: string | null;
  realtimePreview: Record<string, unknown> | null;
  interactivePreview: InteractivePreviewState | null;
  previewTimeSeconds: number;
  setPreviewTimeSeconds: (value: number) => void;
  previewQualityMode: string;
  setPreviewQualityMode: (value: string) => void;
  previewScope: "full" | "scene";
  setPreviewScope: (value: "full" | "scene") => void;
  previewSceneId: string;
  setPreviewSceneId: (value: string) => void;
  preset: string;
  exportFormat: "mp4" | "mov" | "mkv" | "webm" | "gif";
  qualityReport: Record<string, unknown> | null;
  onRealtimePreview: () => void;
  onInteractivePreview: () => void;
  onProjectChange: (project: ProjectData) => void;
  onProjectPreviewChange: (project: ProjectData) => Promise<void>;
  onImport: () => void;
  onAnalyze: () => void;
  onDropAsset: (asset: ImportedAsset) => void;
  onReplaceAsset: (assetKey: string) => void;
  onFirstAiEdit: () => void;
  onAutosaveNow?: () => void;
  onDuplicateProject?: () => void;
  versionCount?: number;
  recoveryCount?: number;
}) {
  return (
    <div className="professional-editor">
      <div className="editor-preview-stack">
        <PreviewWindow
          project={project}
          previewPath={previewPath}
          realtimePreview={realtimePreview}
          interactivePreview={interactivePreview}
          previewTimeSeconds={previewTimeSeconds}
          setPreviewTimeSeconds={setPreviewTimeSeconds}
          previewQualityMode={previewQualityMode}
          setPreviewQualityMode={setPreviewQualityMode}
          previewScope={previewScope}
          setPreviewScope={setPreviewScope}
          previewSceneId={previewSceneId}
          setPreviewSceneId={setPreviewSceneId}
          preset={preset}
          exportFormat={exportFormat}
          qualityReport={qualityReport}
          duration={project ? totalTimelineDuration(project) : 0}
          onRealtimePreview={onRealtimePreview}
          onInteractivePreview={onInteractivePreview}
          onProjectChange={onProjectChange}
          onProjectPreviewChange={onProjectPreviewChange}
        />
        {project ? (
          <VisualTimeline
            project={project}
            onProjectChange={onProjectChange}
            interactivePreview={interactivePreview}
            onAutosaveNow={onAutosaveNow}
            onDuplicateProject={onDuplicateProject}
            versionCount={versionCount}
            recoveryCount={recoveryCount}
          />
        ) : <div className="timeline-pane panel"><span className="muted">Import media or open a project to show the timeline.</span></div>}
      </div>
      <aside className="media-bin-panel">
        <AssetLibrary
          project={project || blankProject()}
          assets={assets}
          assetReport={assetReport}
          onImport={onImport}
          onAnalyze={onAnalyze}
          onDropAsset={onDropAsset}
          onProjectChange={onProjectChange}
          onReplaceAsset={onReplaceAsset}
          onFirstAiEdit={onFirstAiEdit}
        />
      </aside>
    </div>
  );
}

function AiStudioMode({
  prompt,
  setPrompt,
  contentMode,
  setContentMode,
  contentTone,
  setContentTone,
  generationReview,
  pendingAiPlan,
  generationLocks,
  notes,
  directorGoal,
  setDirectorGoal,
  directorReport,
  storyboard,
  promptBuilderOpen,
  setPromptBuilderOpen,
  onGenerate,
  onYouTubeShort,
  onContentGenerate,
  onStudioGenerate,
  onAutonomousPipeline,
  onContentRegenerate,
  onContentApprove,
  onContentLock,
  onApplyPendingPlan,
  onExplain,
  onRepair,
  onDirector,
  onSuggestTransitions,
  onAddScene,
  onCaptions,
  onResolveBroll,
  onStoryboard,
  onAnalyzeAssets
}: {
  prompt: string;
  setPrompt: (value: string) => void;
  contentMode: string;
  setContentMode: (value: string) => void;
  contentTone: string;
  setContentTone: (value: string) => void;
  generationReview: GenerationReviewState | null;
  pendingAiPlan: PendingAiPlan | null;
  generationLocks: string[];
  notes: string;
  directorGoal: string;
  setDirectorGoal: (value: string) => void;
  directorReport: Record<string, unknown> | null;
  storyboard: Record<string, unknown> | null;
  promptBuilderOpen: boolean;
  setPromptBuilderOpen: (value: boolean) => void;
  onGenerate: () => void;
  onYouTubeShort: () => void;
  onContentGenerate: () => void;
  onStudioGenerate: (prompt: string, style: string, tasks: string[]) => void;
  onAutonomousPipeline: () => void;
  onContentRegenerate: (target: string) => void;
  onContentApprove: (section?: string, statusValue?: string) => void;
  onContentLock: (section: string) => void;
  onApplyPendingPlan: () => void;
  onExplain: () => void;
  onRepair: () => void;
  onDirector: () => void;
  onSuggestTransitions: () => void;
  onAddScene: () => void;
  onCaptions: () => void;
  onResolveBroll: () => void;
  onStoryboard: () => void;
  onAnalyzeAssets: () => void;
}) {
  const promptExamples = [
    "Turn this into a YouTube Short",
    "Find the funniest moments",
    "Make this cinematic",
    "Remove dead air",
    "Add captions and zooms"
  ];
  const stylePresets = ["Clean", "Gaming", "Cinematic", "Educational", "Podcast", "Hype", "Minimal", "Meme"];
  const taskOptions = [
    "Detect highlights",
    "Remove silence",
    "Add captions",
    "Add zooms",
    "Add transitions",
    "Add B-roll",
    "Add music",
    "Generate hook",
    "Generate title ideas",
    "Generate thumbnail ideas"
  ];
  const [selectedTasks, setSelectedTasks] = useState<string[]>(["Detect highlights", "Add captions", "Generate hook"]);
  const [builderTopic, setBuilderTopic] = useState("");
  const [builderGoal, setBuilderGoal] = useState("make this into a polished video people will want to watch");
  const [builderAudience, setBuilderAudience] = useState("");
  const [builderKeyPoints, setBuilderKeyPoints] = useState("");
  const [builderNotes, setBuilderNotes] = useState("");
  const parsedPending = pendingAiPlan ? parseProject(pendingAiPlan.text).data : null;
  const planDetails = pendingAiPlan && parsedPending ? buildAiPlanDisplay(pendingAiPlan, parsedPending) : null;

  function toggleTask(task: string) {
    setSelectedTasks((current) => current.includes(task) ? current.filter((item) => item !== task) : [...current, task]);
  }

  function chooseStyle(style: string) {
    setContentTone(style.toLowerCase());
  }

  function buildBeginnerPromptText() {
    const keyPoints = builderKeyPoints
      .split(/\r?\n|,/)
      .map((item) => item.trim())
      .filter(Boolean);
    return [
      `Create a ${friendlyPresetName(contentMode)} video.`,
      builderTopic.trim() ? `Topic or product: ${builderTopic.trim()}.` : "Use the imported media as the main subject.",
      builderGoal.trim() ? `Goal: ${builderGoal.trim()}.` : "",
      builderAudience.trim() ? `Audience: ${builderAudience.trim()}.` : "",
      keyPoints.length ? `Key points to include: ${keyPoints.join("; ")}.` : "",
      `Style: ${friendlyPresetName(contentTone)}.`,
      builderNotes.trim() ? `Extra direction: ${builderNotes.trim()}.` : "",
      "Generate a simple reviewable edit plan first with scenes, captions, timing, transitions, and export settings. Do not require me to edit JSON."
    ].filter(Boolean).join(" ");
  }

  function applyBeginnerPrompt(generate = false) {
    const promptText = buildBeginnerPromptText();
    setPrompt(promptText);
    setPromptBuilderOpen(false);
    if (generate) onStudioGenerate(promptText, contentTone, selectedTasks);
  }

  return (
    <div className="mode-page ai-studio-mode">
      <section className="wide-panel ai-studio-prompt">
        <div className="panel-head-row">
          <div>
            <span className="eyebrow">Review-first AI workflow</span>
            <h2><Bot size={17} /> AI Studio</h2>
          </div>
          <span className="status-pill">timeline changes only after Apply AI Plan</span>
        </div>
        <div className="prompt-builder-actions">
          <button className="primary-create" onClick={() => setPromptBuilderOpen(!promptBuilderOpen)}>
            <CircleHelp size={15} /> Help me make this
          </button>
          <span className="muted">Answer a few plain-English questions, then AI Studio builds the prompt for you.</span>
        </div>
        {promptBuilderOpen && (
          <div className="beginner-prompt-builder">
            <div className="panel-head-row">
              <div>
                <span className="eyebrow">Beginner prompt builder</span>
                <h3>Tell the AI what you want to make</h3>
              </div>
              <button onClick={() => setPromptBuilderOpen(false)}>Close</button>
            </div>
            <div className="prompt-builder-grid">
              <label>
                What are we making?
                <input type="text" value={builderTopic} onChange={(event) => setBuilderTopic(event.target.value)} placeholder="Automatic troubleshooter, product demo, gaming clip..." />
              </label>
              <label>
                Who is it for?
                <input type="text" value={builderAudience} onChange={(event) => setBuilderAudience(event.target.value)} placeholder="Gamers, customers, SaaS buyers, students..." />
              </label>
              <label>
                Main goal
                <input type="text" value={builderGoal} onChange={(event) => setBuilderGoal(event.target.value)} placeholder="Show the feature, explain the problem, make a short..." />
              </label>
              <label>
                Platform
                <select value={contentMode} onChange={(event) => setContentMode(event.target.value)}>
                  <option value="youtube_shorts">YouTube Short</option>
                  <option value="tiktok">TikTok</option>
                  <option value="product_showcase">Product Showcase</option>
                  <option value="tutorial">Tutorial</option>
                  <option value="promo_ad">Promo/Ad</option>
                </select>
              </label>
              <label className="wide-field">
                Key points to include
                <textarea value={builderKeyPoints} onChange={(event) => setBuilderKeyPoints(event.target.value)} placeholder="Missing runtimes&#10;Anti-cheat conflicts&#10;Windows security settings" />
              </label>
              <label className="wide-field">
                Desired vibe or extra instructions
                <textarea value={builderNotes} onChange={(event) => setBuilderNotes(event.target.value)} placeholder="Premium blue/black, cinematic, smooth zooms, clear captions, keep it under 45 seconds..." />
              </label>
            </div>
            <div className="review-actions">
              <button className="primary-create" onClick={() => applyBeginnerPrompt(false)}><Sparkles size={15} /> Build Prompt</button>
              <button onClick={() => applyBeginnerPrompt(true)}><Bot size={15} /> Build + Generate Plan</button>
            </div>
          </div>
        )}
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Describe the video you want in plain English..." />
        <div className="ai-prompt-examples">
          {promptExamples.map((example) => (
            <button key={example} onClick={() => setPrompt(example)}>{example}</button>
          ))}
        </div>
        <div className="ai-studio-controls">
          <label>
            Output mode
            <select value={contentMode} onChange={(event) => setContentMode(event.target.value)}>
              <option value="youtube_shorts">YouTube Shorts</option>
              <option value="tiktok">TikTok</option>
              <option value="product_showcase">Product Showcase</option>
              <option value="tutorial">Tutorial</option>
              <option value="promo_ad">Promo/Ad</option>
            </select>
          </label>
          <label>
            Style
            <select value={contentTone} onChange={(event) => setContentTone(event.target.value)}>
              {stylePresets.map((style) => <option key={style} value={style.toLowerCase()}>{style}</option>)}
            </select>
          </label>
        </div>
        <div className="review-actions">
          <button className="primary-create" onClick={() => onStudioGenerate(prompt, contentTone, selectedTasks)}><Sparkles size={15} /> Generate Reviewable Plan</button>
          <button onClick={onYouTubeShort}><Video size={15} /> YouTube Short Plan</button>
          <button onClick={onAutonomousPipeline}><ListVideo size={15} /> Autonomous Plan</button>
        </div>
        <details className="mini-details">
          <summary>Advanced generation tools</summary>
          <button onClick={onGenerate}><FileJson size={15} /> Prompt to JSON Plan</button>
        </details>
      </section>

      <section className="wide-panel ai-style-section">
        <h2><Wand2 size={16} /> Style Presets</h2>
        <div className="ai-style-grid">
          {stylePresets.map((style) => (
            <button className={contentTone === style.toLowerCase() ? "active" : ""} key={style} onClick={() => chooseStyle(style)}>
              <strong>{style}</strong>
              <span>{aiStyleDescription(style)}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="wide-panel ai-task-section">
        <h2><CheckCircle2 size={16} /> AI Task Toggles</h2>
        <div className="ai-task-grid">
          {taskOptions.map((task) => (
            <label className={selectedTasks.includes(task) ? "active" : ""} key={task}>
              <input type="checkbox" checked={selectedTasks.includes(task)} onChange={() => toggleTask(task)} />
              {task}
            </label>
          ))}
        </div>
      </section>

      <section className="wide-panel ai-output-panel">
        <div className="panel-head-row">
          <h2><ListVideo size={16} /> AI Output Panel</h2>
          <div className="review-actions">
            <button disabled={!pendingAiPlan} className="primary-create" onClick={onApplyPendingPlan}><CheckCircle2 size={14} /> Apply AI Plan</button>
            <button disabled={!pendingAiPlan} onClick={() => onContentRegenerate("scenes")}><RefreshCw size={14} /> Regenerate Scenes</button>
            <button disabled={!pendingAiPlan} onClick={() => onContentApprove("all", "approved")}>Approve All</button>
          </div>
        </div>
        {!planDetails ? (
          <div className="ai-output-empty">
            <strong>No AI plan generated yet</strong>
            <span>Describe what you want, choose style/tasks, then generate a reviewable plan.</span>
          </div>
        ) : (
          <div className="ai-output-grid">
            <article>
              <strong>Edit summary</strong>
              <p>{planDetails.explanation}</p>
            </article>
            <article>
              <strong>Scene list</strong>
              {planDetails.scenes.slice(0, 6).map((scene) => <span key={scene.id}>{scene.name}: {scene.purpose}</span>)}
            </article>
            <article>
              <strong>Suggested cuts</strong>
              {planDetails.cuts.slice(0, 6).map((cut) => <span key={cut}>{cut}</span>)}
            </article>
            <article>
              <strong>Caption plan</strong>
              <span>{planDetails.summary.find((item) => item.label === "Caption style")?.value || "Readable captions"}</span>
              <span>{selectedTasks.includes("Add captions") ? "Captions requested" : "Captions optional"}</span>
            </article>
            <article>
              <strong>Effects plan</strong>
              <span>{planDetails.summary.find((item) => item.label === "Transitions")?.value || "Clean cuts"}</span>
              <span>{selectedTasks.filter((task) => /zoom|transition|b-roll|music/i.test(task)).join(", ") || "No extra effects toggled"}</span>
            </article>
            <article>
              <strong>Export recommendation</strong>
              <span>{planDetails.summary.find((item) => item.label === "Export settings")?.value || contentMode}</span>
              <span>{generationReview?.readyForFinalRender ? "Approved for export review" : "Review before export"}</span>
            </article>
          </div>
        )}
        {generationLocks.length > 0 && <p className="muted">Locked sections: {generationLocks.join(", ")}</p>}
        {notes && (
          <details className="mini-details ai-advanced-reasoning">
            <summary>Advanced: AI reasoning / logs</summary>
            <pre className="mini-pre">{notes}</pre>
          </details>
        )}
      </section>

      <details className="wide-panel ai-advanced-tools">
        <summary>Advanced AI tools</summary>
        <div className="ai-advanced-grid">
          <button onClick={onExplain}><FileJson size={15} /> Explain current project</button>
          <button onClick={onRepair}><Wand2 size={15} /> Repair JSON</button>
          <button onClick={onDirector}><Bot size={15} /> Run Director</button>
          <button onClick={onSuggestTransitions}><RefreshCw size={15} /> Improve transitions</button>
          <button onClick={onAddScene}><Plus size={15} /> Add scene</button>
          <button onClick={onCaptions}><Captions size={15} /> Generate captions</button>
          <button onClick={onResolveBroll}><Image size={15} /> Resolve B-roll</button>
          <button onClick={onStoryboard}><LayoutTemplate size={15} /> Storyboard</button>
          <button onClick={onAnalyzeAssets}><Search size={15} /> Analyze assets</button>
        </div>
      </details>

      <details className="wide-panel ai-advanced-tools">
        <summary>Director and storyboard details</summary>
        <div className="ai-studio-secondary">
          <DirectorWorkspace
            goal={directorGoal}
            setGoal={setDirectorGoal}
            report={directorReport}
            onRun={onDirector}
            onResolveBroll={onResolveBroll}
            onStoryboard={onStoryboard}
            onAnalyzeAssets={onAnalyzeAssets}
          />
          <StoryboardPane storyboard={storyboard} onGenerate={onStoryboard} />
        </div>
      </details>
    </div>
  );
}

function CaptionsMode({
  project,
  onProjectChange,
  onAutoCaption,
  onImportCaptions,
  onPreview,
  onStyle,
  onBurnIn
}: {
  project: ProjectData | null;
  onProjectChange: (project: ProjectData) => void;
  onAutoCaption: () => void;
  onImportCaptions: () => void;
  onPreview: () => void;
  onStyle: (style: string) => void;
  onBurnIn: () => void;
}) {
  const captionEntries = project ? collectCaptionEntries(project) : [];
  const [selectedCaptionId, setSelectedCaptionId] = useState("");
  const [shiftAmount, setShiftAmount] = useState(0.25);
  const selectedCaption = captionEntries.find((entry) => entry.id === selectedCaptionId) || captionEntries[0] || null;
  const settings = project?.project || {};
  const safeZoneWarning = Boolean(project && selectedCaption && isLayerOutsideSafeZone(selectedCaption.layer, Number(settings.width || 1920), Number(settings.height || 1080)));

  useEffect(() => {
    if (!captionEntries.length) {
      setSelectedCaptionId("");
      return;
    }
    if (!captionEntries.some((entry) => entry.id === selectedCaptionId)) setSelectedCaptionId(captionEntries[0].id);
  }, [captionEntries, selectedCaptionId]);

  function updateSelected(patch: Record<string, unknown>) {
    if (!project || !selectedCaption) return;
    onProjectChange(updateCaptionEntry(project, selectedCaption, patch));
  }

  function shiftAll(delta: number) {
    if (!project) return;
    onProjectChange(shiftAllCaptions(project, delta));
  }

  function autoFixTiming() {
    if (!project) return;
    onProjectChange(autoFixCaptionTiming(project));
  }

  function splitSelected() {
    if (!project || !selectedCaption) return;
    onProjectChange(splitCaptionEntry(project, selectedCaption));
  }

  function mergeSelected() {
    if (!project || !selectedCaption) return;
    onProjectChange(mergeCaptionEntry(project, selectedCaption));
  }

  function exportCaptions(format: "srt" | "vtt") {
    if (!project) return;
    const entries = collectCaptionEntries(project).filter((entry) => entry.text.trim());
    const text = format === "srt" ? captionsToSrt(entries) : captionsToVtt(entries);
    downloadTextFile(`captions.${format}`, text);
  }

  return (
    <div className="mode-page captions-mode">
      <section className="wide-panel caption-workflow-hero">
        <h2><Captions size={16} /> Caption Workflow</h2>
        <p className="muted">Generate, import, style, time, and export captions without editing raw JSON. Captions remain JSON-backed and appear on the dedicated timeline lane.</p>
        <div className="caption-tool-grid">
          <button onClick={onAutoCaption}><Sparkles size={15} /> Auto-generate captions</button>
          <button onClick={onImportCaptions}><Import size={15} /> Import SRT / VTT</button>
          <button onClick={() => exportCaptions("srt")}><Download size={15} /> Export SRT</button>
          <button onClick={() => exportCaptions("vtt")}><Download size={15} /> Export VTT</button>
          <button onClick={onBurnIn}><CheckCircle2 size={15} /> Burn-in captions</button>
          <button onClick={onPreview}><MonitorPlay size={15} /> Preview captions</button>
          <button onClick={splitSelected} disabled={!selectedCaption}><Scissors size={15} /> Split caption</button>
          <button onClick={mergeSelected} disabled={!selectedCaption}>Merge captions</button>
          <button onClick={autoFixTiming} disabled={!project}>Auto-fix timing</button>
        </div>
      </section>
      <section className="wide-panel">
        <h2>Caption Styles</h2>
        <div className="caption-style-grid">
          {["Clean subtitles", "TikTok word highlight", "Gaming bold captions", "Podcast lower-third", "Educational captions", "Minimal cinematic captions"].map((style) => (
            <button key={style} onClick={() => onStyle(style)}>
              <strong>{style}</strong>
              <span>{captionStyleDescription(style)}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="wide-panel caption-timeline-panel">
        <div className="panel-head-row">
          <h2>Caption Timeline Lane</h2>
          <div className="caption-shift-controls">
            <label>
              shift
              <input type="number" step="0.05" value={shiftAmount} onChange={(event) => setShiftAmount(Number(event.target.value) || 0)} />
            </label>
            <button onClick={() => shiftAll(-Math.abs(shiftAmount))}>Backward</button>
            <button onClick={() => shiftAll(Math.abs(shiftAmount))}>Forward</button>
          </div>
        </div>
        <div className="caption-lane-scroll">
          <div className="caption-lane" style={{ width: Math.max(totalTimelineDuration(project || blankProject()), 12) * 90 }}>
            {captionEntries.length === 0 && <span className="muted">No caption/text layers yet. Auto-generate or import captions to populate this lane.</span>}
            {captionEntries.map((entry) => (
              <button
                className={selectedCaption?.id === entry.id ? "selected" : ""}
                key={entry.id}
                style={{ left: entry.absoluteStart * 90, width: Math.max(entry.duration * 90, 72) }}
                onClick={() => setSelectedCaptionId(entry.id)}
                title={entry.text}
              >
                <strong>{entry.sceneId}</strong>
                <span>{entry.text || entry.type}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="wide-panel caption-editor-panel">
        <h2>Edit Caption Timing</h2>
        <div className="caption-list">
          {captionEntries.length === 0 && <span className="muted">No captions available.</span>}
          {captionEntries.slice(0, 32).map((entry) => (
            <button className={selectedCaption?.id === entry.id ? "active" : ""} key={entry.id} onClick={() => setSelectedCaptionId(entry.id)}>
              <strong>{formatTimestamp(entry.absoluteStart)}</strong>
              <span>{entry.text || entry.type}</span>
              <small>{entry.duration.toFixed(2)}s / {entry.sceneId}</small>
            </button>
          ))}
        </div>
      </section>
      <section className="wide-panel caption-inspector-panel">
        <h2>Caption Inspector</h2>
        {!selectedCaption ? (
          <p className="muted">Select a caption from the lane to edit style and timing.</p>
        ) : (
          <div className="caption-inspector-grid">
            <label className="span-2">
              Caption text
              <textarea value={selectedCaption.text} onChange={(event) => updateSelected({ text: event.target.value })} />
            </label>
            <label>
              Start
              <input type="number" step="0.05" value={selectedCaption.localStart} onChange={(event) => updateSelected({ start: Number(event.target.value) || 0 })} />
            </label>
            <label>
              Duration
              <input type="number" step="0.05" value={selectedCaption.duration} onChange={(event) => updateSelected({ duration: Math.max(0.25, Number(event.target.value) || selectedCaption.duration) })} />
            </label>
            <label>
              Font
              <input value={String(selectedCaption.layer.fontFamily || selectedCaption.layer.font || "Arial")} onChange={(event) => updateSelected({ fontFamily: event.target.value })} />
            </label>
            <label>
              Size
              <input type="number" value={Number(selectedCaption.layer.fontSize || 54)} onChange={(event) => updateSelected({ fontSize: Number(event.target.value) || 54 })} />
            </label>
            <label>
              Position
              <select value={String(selectedCaption.layer.y || "bottom")} onChange={(event) => updateSelected({ y: event.target.value })}>
                <option value="bottom">Bottom safe</option>
                <option value="center">Center</option>
                <option value="top">Top safe</option>
                <option value="lower_third">Lower-third</option>
              </select>
            </label>
            <label>
              Color
              <input type="color" value={normalizeColorInput(selectedCaption.layer.color, "#ffffff")} onChange={(event) => updateSelected({ color: event.target.value })} />
            </label>
            <label>
              Stroke / outline
              <input type="number" value={Number(selectedCaption.layer.strokeWidth || 2)} onChange={(event) => updateSelected({ strokeWidth: Number(event.target.value) || 0 })} />
            </label>
            <label>
              Shadow
              <select value={String(selectedCaption.layer.shadow || "soft")} onChange={(event) => updateSelected({ shadow: event.target.value })}>
                <option value="none">None</option>
                <option value="soft">Soft</option>
                <option value="strong">Strong</option>
              </select>
            </label>
            <label>
              Background box
              <select value={String(selectedCaption.layer.box ? "on" : "off")} onChange={(event) => updateSelected({ box: event.target.value === "on" })}>
                <option value="on">On</option>
                <option value="off">Off</option>
              </select>
            </label>
            <label>
              Animation
              <select value={String((selectedCaption.layer.animation as Record<string, unknown> | undefined)?.in || "fade")} onChange={(event) => updateSelected({ animation: { ...((selectedCaption.layer.animation as Record<string, unknown>) || {}), in: event.target.value } })}>
                <option value="fade">Fade</option>
                <option value="slideUp">Slide up</option>
                <option value="pop">Pop</option>
                <option value="typewriter">Typewriter</option>
              </select>
            </label>
            <label className="check-control">
              <input type="checkbox" checked={Boolean(selectedCaption.layer.wordHighlight || selectedCaption.layer.highlightWords)} onChange={(event) => updateSelected({ wordHighlight: event.target.checked, highlightWords: event.target.checked })} />
              Word-by-word highlight
            </label>
            {safeZoneWarning && <p className="warning-line span-2">Safe-zone warning: this caption may sit too close to the frame edge.</p>}
          </div>
        )}
      </section>
      <section className="wide-panel caption-help-panel">
        <h2>Caption Lane Notes</h2>
        <p className="muted">The main timeline already includes a dedicated Captions lane. These controls edit the same JSON-backed caption layers, so preview and final export stay in sync.</p>
      </section>
    </div>
  );
}

function TemplatesMode({
  beginnerTemplates,
  templates,
  onPreviewTemplate,
  onApplyTemplate,
  onCustomizeTemplate,
  onDuplicateTemplate,
  onSaveTemplate
}: {
  beginnerTemplates: BeginnerTemplateCard[];
  templates: string[];
  onPreviewTemplate: (key: string) => void;
  onApplyTemplate: (key: string) => void;
  onCustomizeTemplate: (key: string) => void;
  onDuplicateTemplate: (key: string) => void;
  onSaveTemplate: (key: string) => void;
}) {
  const categories = ["YouTube Shorts", "TikTok", "Instagram Reels", "Gaming Clips", "Podcast Clips", "Educational", "Product Promo", "Cinematic", "Meme / Reaction", "Tutorial"];
  const [activeCategory, setActiveCategory] = useState(categories[0]);
  const beginnerItems = beginnerTemplates.map((template) => {
    const customizer = templateCustomizerFromKey(template.key, templates);
    return {
      key: template.key,
      name: template.name,
      category: categoryForTemplate(template.name),
      platform: templatePlatformLabel(customizer.platform),
      aspectRatio: template.aspectRatio,
      duration: customizer.duration,
      style: template.pacing,
      requiredMedia: requiredMediaForTemplate(template.name),
      usesCaptions: /caption|subtitle|title/i.test(template.captionStyle),
      usesMusic: !/podcast|tutorial/i.test(template.name),
      source: "premium"
    };
  });
  const jsonItems = templates.map((template) => {
    const customizer = templateCustomizerFromKey(template, templates);
    return {
      key: template,
      name: customizer.name,
      category: categoryForTemplate(customizer.name),
      platform: templatePlatformLabel(customizer.platform),
      aspectRatio: customizer.platform === "shorts" || customizer.platform === "tiktok" || customizer.platform === "instagram_reels" ? "9:16" : "16:9",
      duration: customizer.duration,
      style: customizer.pacing,
      requiredMedia: requiredMediaForTemplate(customizer.name),
      usesCaptions: /caption|lyric|tutorial|meme/i.test(customizer.name),
      usesMusic: !/podcast|tutorial/i.test(customizer.name),
      source: "json"
    };
  });
  const items = [...beginnerItems, ...jsonItems];
  const filtered = items.filter((item) => item.category === activeCategory);
  return (
    <div className="mode-page templates-mode">
      <section className="wide-panel">
        <h2><LayoutTemplate size={16} /> Template Library</h2>
        <p className="muted">Templates now create a reviewable edit plan first. Applying one will show scenes, cuts, captions, effects, and export settings before the timeline changes.</p>
        <div className="template-category-grid">
          {categories.map((category) => (
            <button className={activeCategory === category ? "active" : ""} key={category} onClick={() => setActiveCategory(category)}>
              {category}
            </button>
          ))}
        </div>
      </section>

      <section className="wide-panel template-library-panel">
        <div className="panel-head-row">
          <h2>{activeCategory}</h2>
          <span className="muted">{filtered.length} template(s)</span>
        </div>
        <div className="template-library-grid">
          {filtered.map((template) => (
            <article className="template-library-card" key={`${template.source}-${template.key}`}>
              <div className={`template-preview-thumb ${template.category.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                <span>{template.platform}</span>
                <strong>{template.name}</strong>
              </div>
              <div className="template-card-body">
                <div>
                  <strong>{template.name}</strong>
                  <small>{template.source === "json" ? "JSON template" : "Premium auto template"}</small>
                </div>
                <div className="template-card-meta">
                  <span>Platform <strong>{template.platform}</strong></span>
                  <span>Aspect <strong>{template.aspectRatio}</strong></span>
                  <span>Duration <strong>{template.duration}s</strong></span>
                  <span>Style <strong>{template.style}</strong></span>
                  <span>Required media <strong>{template.requiredMedia}</strong></span>
                  <span>Captions <strong>{template.usesCaptions ? "yes" : "no"}</strong></span>
                  <span>Music <strong>{template.usesMusic ? "yes" : "no"}</strong></span>
                </div>
              </div>
              <div className="template-card-actions">
                <button onClick={() => onPreviewTemplate(template.key)}><Eye size={14} /> Preview</button>
                <button onClick={() => onApplyTemplate(template.key)}><CheckCircle2 size={14} /> Apply</button>
                <button onClick={() => onCustomizeTemplate(template.key)}><Wand2 size={14} /> Customize</button>
                <button onClick={() => onDuplicateTemplate(template.key)}><FileJson size={14} /> Duplicate</button>
                <button onClick={() => onSaveTemplate(template.key)}><Save size={14} /> Save Mine</button>
              </div>
            </article>
          ))}
          {!filtered.length && (
            <div className="template-empty-state">
              <strong>No templates in this category yet</strong>
              <span>Use another category or save a customized template into this group later.</span>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function ExportMode({
  project,
  ...renderProps
}: Parameters<typeof RenderPanel>[0] & { project: ProjectData | null }) {
  const settings = project?.project || {};
  return (
    <div className="mode-page export-mode">
      <section className="wide-panel">
        <h2><Download size={16} /> Export Summary</h2>
        <div className="metric-grid">
          <span>resolution <strong>{String(settings.width || "?")}x{String(settings.height || "?")}</strong></span>
          <span>fps <strong>{String(settings.fps || "?")}</strong></span>
          <span>duration <strong>{project ? totalTimelineDuration(project).toFixed(1) : "0.0"}s</strong></span>
          <span>platform <strong>{project?.exportPreset || renderProps.preset}</strong></span>
        </div>
      </section>
      <RenderPanel {...renderProps} project={project} />
    </div>
  );
}

function DiagnosticsMode({
  projectText,
  engineReady,
  validation,
  onJsonChange,
  onEditorMount,
  logs,
  activityFeed,
  appError,
  workflow
}: {
  projectText: string;
  projectPath: string | null;
  engineReady: boolean;
  validation: EngineResult | null;
  onJsonChange: (value: string) => void;
  onEditorMount: OnMount;
  logs: string[];
  activityFeed: ProcessingActivity[];
  appError: string;
  workflow: ReactNode;
}) {
  return (
    <div className="mode-page diagnostics-mode">
      <section className="wide-panel">
        <h2><Clock size={16} /> Logs / Diagnostics</h2>
        {appError && <p className="error">{appError}</p>}
        <div className="logs-modal embedded">
          <pre className="logs">{logs.join("\n") || "No render logs yet."}</pre>
          <div className="activity-feed">
            {activityFeed.length === 0 && <span className="muted">No AI/render activity yet.</span>}
            {activityFeed.map((item) => (
              <div className={`activity-row ${item.kind}`} key={item.id}>
                <strong>{activityGlyph(item.kind)}</strong>
                <span>{item.label}</span>
                <small>{item.detail || item.time}</small>
              </div>
            ))}
          </div>
        </div>
      </section>
      <details className="wide-panel" open>
        <summary>JSON timeline viewer</summary>
        <JsonEditor text={projectText} schemaReady={engineReady} onChange={onJsonChange} onMount={onEditorMount} validation={validation} />
      </details>
      <section>{workflow}</section>
    </div>
  );
}

function EditorSidebar({
  activeTab,
  onTab,
  onModal,
  onImport,
  onCaptions,
  onHighlights,
  onRemoveSilence,
  onTransitions,
  onPacing,
  onHook,
  onThumbnail
}: {
  activeTab: Tab;
  onTab: (tab: Tab) => void;
  onModal: (modal: AppModal) => void;
  onImport: () => void;
  onCaptions: () => void;
  onHighlights: () => void;
  onRemoveSilence: () => void;
  onTransitions: () => void;
  onPacing: () => void;
  onHook: () => void;
  onThumbnail: () => void;
}) {
  return (
    <div className="editor-sidebar">
      <details className="rail-section" open>
        <summary><Image size={15} /> Media</summary>
        <button className={activeTab === "assets" ? "sidebar-action active" : "sidebar-action"} onClick={() => onTab("assets")}>Imported videos</button>
        <button className="sidebar-action" onClick={() => onTab("assets")}>Images</button>
        <button className="sidebar-action" onClick={() => onTab("assets")}>Audio</button>
        <button className="sidebar-action" onClick={() => onModal("import")}>URLs</button>
        <button className="sidebar-action" onClick={() => onTab("storyboard")}>Generated assets</button>
        <button className="primary-sidebar-action" onClick={onImport}><Import size={14} /> Import media</button>
      </details>

      <details className="rail-section" open>
        <summary><LayoutTemplate size={15} /> Templates</summary>
        {["YouTube Shorts", "TikTok", "Instagram Reels", "Gaming clips", "Podcast clips", "Educational videos", "Promo/ad templates"].map((label) => (
          <button className="sidebar-action" key={label} onClick={() => onModal("templates")}>{label}</button>
        ))}
      </details>

      <details className="rail-section" open>
        <summary><Sparkles size={15} /> AI Tools</summary>
        <button className="sidebar-action" onClick={() => onModal("ai")}>Auto edit</button>
        <button className="sidebar-action" onClick={onCaptions}>Generate captions</button>
        <button className="sidebar-action" onClick={onHighlights}>Detect highlights</button>
        <button className="sidebar-action" onClick={onRemoveSilence}>Remove silence</button>
        <button className="sidebar-action" onClick={() => onModal("ai")}>Add B-roll</button>
        <button className="sidebar-action" onClick={onTransitions}>Add transitions</button>
        <button className="sidebar-action" onClick={onPacing}>Improve pacing</button>
        <button className="sidebar-action" onClick={onHook}>Generate title/hook</button>
        <button className="sidebar-action" onClick={onThumbnail}>Generate thumbnail ideas</button>
      </details>

      <details className="rail-section">
        <summary><Scissors size={15} /> Effects</summary>
        {["Text", "Captions", "Transitions", "Filters", "Overlays", "Motion", "Blur", "Zoom/pan", "Sound effects"].map((label) => (
          <button className="sidebar-action" key={label} onClick={() => onTab(label === "Captions" ? "preview" : "timeline")}>{label}</button>
        ))}
      </details>

      <details className="rail-section">
        <summary><FileJson size={15} /> Project</summary>
        <button className="sidebar-action" onClick={() => onModal("json")}>Timeline JSON</button>
        <button className="sidebar-action" onClick={() => onTab("timeline")}>Scene list</button>
        <button className="sidebar-action" onClick={() => onTab("product")}>Export history</button>
        <button className="sidebar-action" onClick={() => onTab("workflow")}>Version history</button>
        <button className="sidebar-action" onClick={() => onModal("logs")}>Logs</button>
      </details>
    </div>
  );
}

function InspectorContextPanel({
  activeTab,
  project,
  preset,
  exportFormat,
  previewSceneId,
  duration,
  onJson,
  onExport
}: {
  activeTab: Tab;
  project: ProjectData | null;
  preset: string;
  exportFormat: string;
  previewSceneId: string;
  duration: number;
  onJson: () => void;
  onExport: () => void;
}) {
  const scene = project?.timeline?.find((item) => item.id === previewSceneId) || project?.timeline?.[0];
  const mediaLayer = scene?.layers?.find((layer) => layer.type === "video" || layer.type === "image");
  const textLayer = scene?.layers?.find((layer) => layer.type === "text" || layer.type === "caption" || layer.type === "captions");
  return (
    <section className="inspector-card">
      <div className="review-header">
        <strong>{activeTab === "product" ? "Export Settings" : activeTab === "beginner" ? "Template Settings" : "Selection Settings"}</strong>
        <span className="muted">{scene?.id || "project"}</span>
      </div>
      <div className="inspector-grid">
        <span>duration <strong>{duration.toFixed(1)}s</strong></span>
        <span>preset <strong>{preset}</strong></span>
        <span>format <strong>{exportFormat}</strong></span>
        <span>scenes <strong>{project?.timeline?.length || 0}</strong></span>
      </div>
      {mediaLayer && (
        <details className="mini-details" open>
          <summary>Clip</summary>
          <div className="inspector-grid">
            <span>asset <strong>{String(mediaLayer.asset || "-")}</strong></span>
            <span>trim <strong>{String(mediaLayer.trimStart ?? 0)}s</strong></span>
            <span>speed <strong>{String(mediaLayer.speed ?? 1)}x</strong></span>
            <span>opacity <strong>{String(mediaLayer.opacity ?? 1)}</strong></span>
          </div>
        </details>
      )}
      {textLayer && (
        <details className="mini-details">
          <summary>Text / Captions</summary>
          <div className="inspector-grid">
            <span>font <strong>{String(textLayer.fontFamily || "default")}</strong></span>
            <span>size <strong>{String(textLayer.fontSize || "-")}</strong></span>
            <span>color <strong>{String(textLayer.color || textLayer.highlightColor || "-")}</strong></span>
            <span>safe zone <strong>{String(textLayer.safeZone || "on")}</strong></span>
          </div>
        </details>
      )}
      <div className="button-grid compact">
        <button onClick={onJson}><FileJson size={14} /> JSON</button>
        <button onClick={onExport}><Download size={14} /> Export</button>
      </div>
    </section>
  );
}

function SuggestedEditsPanel({
  suggestions,
  savedSuggestions,
  disabledTypes,
  onApply,
  onIgnore,
  onSave,
  onDisableType,
  onEnableType
}: {
  suggestions: ProactiveSuggestion[];
  savedSuggestions: ProactiveSuggestion[];
  disabledTypes: string[];
  onApply: (suggestion: ProactiveSuggestion) => void;
  onIgnore: (suggestion: ProactiveSuggestion) => void;
  onSave: (suggestion: ProactiveSuggestion) => void;
  onDisableType: (action: string) => void;
  onEnableType: (action: string) => void;
}) {
  const topSuggestions = suggestions.slice(0, 7);
  return (
    <section className="inspector-card suggested-edits-panel">
      <div className="review-header">
        <strong><Sparkles size={14} /> Suggested Edits</strong>
        <span className="muted">{topSuggestions.length} active</span>
      </div>

      {topSuggestions.length ? (
        <div className="suggested-edit-list">
          {topSuggestions.map((suggestion) => (
            <article className={`suggested-edit-card ${suggestion.severity}`} key={suggestion.id}>
              <div className="suggested-edit-head">
                <strong>{suggestion.title}</strong>
                <span>{friendlyPresetName(suggestion.action)}</span>
              </div>
              <p>{suggestion.detail}</p>
              <div className="suggested-edit-meta">
                {suggestion.sceneId && <span>scene {suggestion.sceneId}</span>}
                {typeof suggestion.time === "number" && <span>{formatTimestamp(suggestion.time)}</span>}
                {typeof suggestion.duration === "number" && suggestion.duration > 0 && <span>{suggestion.duration.toFixed(1)}s</span>}
              </div>
              <div className="suggested-edit-actions">
                <button onClick={() => onApply(suggestion)}><CheckCircle2 size={13} /> Apply</button>
                <button onClick={() => onIgnore(suggestion)}><X size={13} /> Ignore</button>
                <button onClick={() => onSave(suggestion)}><Save size={13} /> Save</button>
                <button onClick={() => onDisableType(suggestion.action)}><Eye size={13} /> Disable type</button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-mini">
          <strong>No active suggestions</strong>
          <span>The assistant will surface cuts, captions, zooms, hooks, and pacing fixes as it analyzes the edit.</span>
        </div>
      )}

      {(savedSuggestions.length > 0 || disabledTypes.length > 0) && (
        <details className="mini-details">
          <summary>Saved / disabled</summary>
          {savedSuggestions.length > 0 && (
            <div className="suggested-edit-saved">
              <span className="muted">Saved</span>
              {savedSuggestions.slice(-4).map((suggestion) => (
                <button key={suggestion.id} onClick={() => onApply(suggestion)}>
                  <CheckCircle2 size={12} /> {suggestion.title}
                </button>
              ))}
            </div>
          )}
          {disabledTypes.length > 0 && (
            <div className="disabled-suggestion-types">
              <span className="muted">Disabled types</span>
              {disabledTypes.map((type) => (
                <button key={type} onClick={() => onEnableType(type)}>
                  <Eye size={12} /> Enable {friendlyPresetName(type)}
                </button>
              ))}
            </div>
          )}
        </details>
      )}
    </section>
  );
}

function TaskManagerPanel({
  tasks,
  systemMetrics,
  onPause,
  onResume,
  onCancel,
  onClearCompleted,
  onOpenRenderProgress
}: {
  tasks: ManagedTask[];
  systemMetrics: SystemMetrics | null;
  onPause: (task: ManagedTask) => void;
  onResume: (task: ManagedTask) => void;
  onCancel: (task: ManagedTask) => void;
  onClearCompleted: () => void;
  onOpenRenderProgress: () => void;
}) {
  const activeTasks = tasks.filter((task) => ["queued", "running", "paused"].includes(task.status));
  const finishedTasks = tasks.filter((task) => !["queued", "running", "paused"].includes(task.status));
  const visibleTasks = [...activeTasks, ...finishedTasks].slice(0, 8);
  const taskKinds = [
    "ai_analysis",
    "caption_generation",
    "audio_transcription",
    "render_export",
    "thumbnail_generation",
    "media_import",
    "proxy_generation",
    "url_download"
  ] as ManagedTaskKind[];
  return (
    <section className="inspector-card task-manager-panel">
      <div className="review-header">
        <strong><Clock size={14} /> Task Manager</strong>
        <span className="muted">{activeTasks.length ? `${activeTasks.length} active` : "idle"}</span>
      </div>
      <div className="task-manager-metrics">
        <span>CPU <strong>{formatPercent(systemMetrics?.cpuPercent)}</strong></span>
        <span>GPU <strong>{systemMetrics?.gpuProcessActive ? formatPercent(systemMetrics.gpuPercent) : "-"}</strong></span>
      </div>
      <div className="task-kind-strip" title="Tracked background operation types">
        {taskKinds.map((kind) => (
          <span key={kind}>{taskKindLabel(kind)}</span>
        ))}
      </div>
      <div className="task-list">
        {visibleTasks.length === 0 && (
          <div className="empty-mini">
            <strong>No background tasks</strong>
            <span>AI, captions, imports, proxies, thumbnails, URL downloads, and renders will appear here while they run.</span>
          </div>
        )}
        {visibleTasks.map((task) => (
          <article className={`task-card ${task.status}`} key={task.id}>
            <div className="task-card-head">
              <div>
                <strong>{task.label}</strong>
                <span>{taskKindLabel(task.kind)} / {taskStatusLabel(task.status)}</span>
              </div>
              <span>{Math.round(safePercent(task.progress))}%</span>
            </div>
            <div className="progressbar task-progress"><span style={{ width: `${safePercent(task.progress)}%` }} /></div>
            <div className="task-detail-grid">
              <span>stage <strong>{task.stage}</strong></span>
              <span>ETA <strong>{formatEta(task.etaSeconds)}</strong></span>
              <span>asset <strong>{task.currentAsset || task.detail || "current project"}</strong></span>
              <span>scene <strong>{task.currentScene || "auto"}</strong></span>
            </div>
            {Boolean((task.errors || []).length || (task.warnings || []).length) && (
              <div className="task-issues">
                {(task.errors || []).slice(0, 2).map((error) => <span className="error" key={error}>{error}</span>)}
                {(task.warnings || []).slice(0, 2).map((warning) => <span className="warning" key={warning}>{warning}</span>)}
              </div>
            )}
            <div className="task-actions">
              <button disabled={!task.canPause} onClick={() => onPause(task)}><Pause size={12} /> Pause</button>
              <button disabled={!task.canResume && !(task.kind === "render_export" && task.status === "queued")} onClick={() => onResume(task)}><Play size={12} /> Resume</button>
              <button disabled={!task.canCancel} onClick={() => onCancel(task)}><X size={12} /> Cancel</button>
            </div>
          </article>
        ))}
      </div>
      <div className="task-footer-actions">
        <button onClick={onOpenRenderProgress}><MonitorPlay size={13} /> Render details</button>
        <button onClick={onClearCompleted}><Trash2 size={13} /> Clear done</button>
      </div>
      <p className="muted">Render/export jobs run through the local background queue, so you can keep editing while FFmpeg works.</p>
    </section>
  );
}

function EditorModal({
  modal,
  onClose,
  projectText,
  projectPath,
  project,
  appError,
  jsonParseError,
  processing,
  engineReady,
  validation,
  onJsonChange,
  onEditorMount,
  prompt,
  setPrompt,
  contentMode,
  setContentMode,
  contentTone,
  setContentTone,
  generationReview,
  pendingAiPlan,
  generationLocks,
  aiNotes,
  startupRecovery,
  recoveryPoints,
  versionComparison,
  templateCustomizer,
  setTemplateCustomizer,
  onApplyTemplateCustomization,
  onSaveTemplateCustomization,
  onImport,
  onOpenProject,
  onNewProject,
  onSave,
  onSaveAs,
  onGenerate,
  onYouTubeShort,
  onContentGenerate,
  onAutonomousPipeline,
  onContentRegenerate,
  onContentApprove,
  onContentLock,
  onApplyPendingPlan,
  onEditPendingPlan,
  onRegeneratePendingPlan,
  onSavePendingPlan,
  onCancelPendingPlan,
  onRestoreStartupRecovery,
  onRestoreRecoveryPoint,
  onDismissStartupRecovery,
  onExplain,
  onRepair,
  onDirector,
  onSuggestTransitions,
  onAddScene,
  onCaptions,
  onCaptionStyle,
  templates,
  beginnerTemplates,
  onTemplate,
  onBeginnerTemplate,
  preset,
  setPreset,
  exportFormat,
  setExportFormat,
  quality,
  setQuality,
  cache,
  setCache,
  resume,
  setResume,
  gpu,
  setGpu,
  logs,
  renderQueueItems,
  systemMetrics,
  finalPreflight,
  onPreflight,
  onRepairPreflight,
  onPreview,
  onFinal,
  onPauseQueue,
  onResumeQueue,
  onCancelJob,
  onRetryJob,
  onOpenOutput,
  settings,
  setSettings,
  onSaveSettings,
  leftRailOpen,
  setLeftRailOpen,
  rightRailOpen,
  setRightRailOpen,
  onApplyWorkspacePreset,
  onSaveWorkspaceLayout,
  onPopOutPanel,
  onCompleteOnboarding,
  onPickExportFolder,
  onRunSystemCheck,
  onShowShortcuts,
  hardeningStatus,
  activityFeed,
  onOpenDocs
}: {
  modal: AppModal;
  onClose: () => void;
  projectText: string;
  projectPath: string | null;
  project: ProjectData | null;
  appError: string;
  jsonParseError?: string;
  processing: ProcessingState;
  engineReady: boolean;
  validation: EngineResult | null;
  onJsonChange: (value: string) => void;
  onEditorMount: OnMount;
  prompt: string;
  setPrompt: (value: string) => void;
  contentMode: string;
  setContentMode: (value: string) => void;
  contentTone: string;
  setContentTone: (value: string) => void;
  generationReview: GenerationReviewState | null;
  pendingAiPlan: PendingAiPlan | null;
  generationLocks: string[];
  aiNotes: string;
  startupRecovery: StartupRecoveryState | null;
  recoveryPoints: RecoveryPoint[];
  versionComparison: VersionComparison | null;
  templateCustomizer: TemplateCustomizerState | null;
  setTemplateCustomizer: (value: TemplateCustomizerState | null | ((value: TemplateCustomizerState | null) => TemplateCustomizerState | null)) => void;
  onApplyTemplateCustomization: () => void;
  onSaveTemplateCustomization: () => void;
  onImport: () => void;
  onOpenProject: () => void;
  onNewProject: () => void;
  onSave: () => void;
  onSaveAs: () => void;
  onGenerate: () => void;
  onYouTubeShort: () => void;
  onContentGenerate: () => void;
  onAutonomousPipeline: () => void;
  onContentRegenerate: (target: string) => void;
  onContentApprove: (section?: string, statusValue?: string) => void;
  onContentLock: (section: string) => void;
  onApplyPendingPlan: () => void;
  onEditPendingPlan: () => void;
  onRegeneratePendingPlan: () => void;
  onSavePendingPlan: () => void;
  onCancelPendingPlan: () => void;
  onRestoreStartupRecovery: () => void;
  onRestoreRecoveryPoint: (sourcePath: string) => void;
  onDismissStartupRecovery: () => void;
  onExplain: () => void;
  onRepair: () => void;
  onDirector: () => void;
  onSuggestTransitions: () => void;
  onAddScene: () => void;
  onCaptions: () => void;
  onCaptionStyle: (style: string) => void;
  templates: string[];
  beginnerTemplates: BeginnerTemplateCard[];
  onTemplate: (key: string) => void;
  onBeginnerTemplate: (key: string) => void;
  preset: string;
  setPreset: (value: string) => void;
  exportFormat: "mp4" | "mov" | "mkv" | "webm" | "gif";
  setExportFormat: (value: "mp4" | "mov" | "mkv" | "webm" | "gif") => void;
  quality: "preview" | "final";
  setQuality: (value: "preview" | "final") => void;
  cache: boolean;
  setCache: (value: boolean) => void;
  resume: boolean;
  setResume: (value: boolean) => void;
  gpu: boolean;
  setGpu: (value: boolean) => void;
  logs: string[];
  renderQueueItems: RenderQueueItem[];
  systemMetrics: SystemMetrics | null;
  finalPreflight: FinalPreflightReport | null;
  onPreflight: () => void;
  onRepairPreflight: (mode: string, issueId?: string | null) => void;
  onPreview: () => void;
  onFinal: () => void;
  onPauseQueue: () => void;
  onResumeQueue: () => void;
  onCancelJob: (runId: string) => void;
  onRetryJob: (runId: string) => void;
  onOpenOutput: () => void;
  settings: AppSettings;
  setSettings: (value: AppSettings | ((value: AppSettings) => AppSettings)) => void;
  onSaveSettings: () => void;
  leftRailOpen: boolean;
  setLeftRailOpen: (value: boolean | ((current: boolean) => boolean)) => void;
  rightRailOpen: boolean;
  setRightRailOpen: (value: boolean | ((current: boolean) => boolean)) => void;
  onApplyWorkspacePreset: (preset: WorkspacePreset) => void;
  onSaveWorkspaceLayout: () => void;
  onPopOutPanel: (panel: "preview" | "timeline" | "inspector") => void;
  onCompleteOnboarding: (settings: AppSettings) => void;
  onPickExportFolder: () => Promise<string | null>;
  onRunSystemCheck: () => void;
  onShowShortcuts: () => void;
  hardeningStatus: HardeningStatus | null;
  activityFeed: ProcessingActivity[];
  onOpenDocs: () => void;
}) {
  const activeJob = activeRenderJob(renderQueueItems);
  const renderProgress = safePercent(activeJob ? Number(activeJob.progressPercent || 0) : processing.progress);
  const latestIssues = latestRenderIssues(logs, activityFeed);
  const [onboardingDraft, setOnboardingDraft] = useState<AppSettings>(settings);
  useEffect(() => {
    if (modal === "onboarding") setOnboardingDraft(settings);
  }, [modal, settings]);
  const updateTemplateCustomizer = (patch: Partial<TemplateCustomizerState>) => {
    setTemplateCustomizer((current) => current ? { ...current, ...patch } : current);
  };
  if (!modal) return null;
  const titles: Record<Exclude<AppModal, null>, string> = {
    import: "Import Media",
    ai: "AI Edit Prompt",
    aiReview: "AI Plan Review",
    templates: "Template Picker",
    templateCustomizer: "Template Customizer",
    captionStyle: "Caption Style Picker",
    export: "Export Presets",
    renderProgress: "Render Progress",
    errorRecovery: "Error Recovery",
    recoveryPrompt: "Recover Unsaved Project?",
    versionCompare: "Compare Versions",
    onboarding: "Welcome",
    shortcuts: "Keyboard Shortcuts",
    workspace: "Workspace Layout",
    settings: "Project Settings",
    help: "Help",
    json: "Timeline JSON",
    logs: "Logs / Debug"
  };
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <section className={`modal-card modal-${modal}`}>
        <header className="modal-header">
          <strong>{titles[modal]}</strong>
          <button onClick={onClose} title="Close"><X size={16} /></button>
        </header>
        <div className="modal-body">
          {modal === "import" && (
            <div className="modal-grid">
              <button onClick={onImport}><Import size={16} /> Import media into current project</button>
              <button onClick={onOpenProject}><FolderOpen size={16} /> Open project.json</button>
              <button onClick={onNewProject}><Plus size={16} /> New project</button>
              <button onClick={onSave}><Save size={16} /> Save</button>
              <button onClick={onSaveAs}><FileJson size={16} /> Save As</button>
              <span className="muted">URL download/import stays local and will be wired through the media import pipeline.</span>
            </div>
          )}
          {modal === "ai" && (
            <AiPanel
              prompt={prompt}
              setPrompt={setPrompt}
              contentMode={contentMode}
              setContentMode={setContentMode}
              contentTone={contentTone}
              setContentTone={setContentTone}
              generationReview={generationReview}
              generationLocks={generationLocks}
              notes={aiNotes}
              onGenerate={onGenerate}
              onYouTubeShort={onYouTubeShort}
              onContentGenerate={onContentGenerate}
              onAutonomousPipeline={onAutonomousPipeline}
              onContentRegenerate={onContentRegenerate}
              onContentApprove={onContentApprove}
              onContentLock={onContentLock}
              onExplain={onExplain}
              onRepair={onRepair}
              onDirector={onDirector}
              onSuggestTransitions={onSuggestTransitions}
              onAddScene={onAddScene}
              onCaptions={onCaptions}
            />
          )}
          {modal === "aiReview" && (
            <AiPlanReviewModal
              pendingAiPlan={pendingAiPlan}
              fallbackReview={generationReview}
              prompt={prompt}
              setPrompt={setPrompt}
              aiNotes={aiNotes}
              onGenerate={onContentGenerate}
              onPromptJson={onGenerate}
              onApply={onApplyPendingPlan}
              onEdit={onEditPendingPlan}
              onRegenerate={onRegeneratePendingPlan}
              onSaveTemplate={onSavePendingPlan}
              onCancel={onCancelPendingPlan}
              onLockScene={onContentLock}
            />
          )}
          {modal === "templates" && (
            <div className="template-modal-grid">
              {beginnerTemplates.map((template) => (
                <button key={template.key} onClick={() => onBeginnerTemplate(template.key)}>
                  <strong>{template.name}</strong>
                  <span>{template.platform} / {template.aspectRatio} / {template.captionStyle}</span>
                </button>
              ))}
              {templates.map((template) => (
                <button key={template} onClick={() => onTemplate(template)}>
                  <strong>{templateLabels[template] || template}</strong>
                  <span>JSON template</span>
                </button>
              ))}
            </div>
          )}
          {modal === "templateCustomizer" && (
            <div className="template-customizer-modal">
              {!templateCustomizer ? (
                <section className="wide-panel">
                  <h2><LayoutTemplate size={16} /> No template selected</h2>
                  <p className="muted">Choose a template from the Template Library first.</p>
                </section>
              ) : (
                <>
                  <section className="wide-panel template-customizer-hero">
                    <div>
                      <span className="eyebrow">Review-first template</span>
                      <h2><LayoutTemplate size={17} /> {templateCustomizer.name}</h2>
                      <p className="muted">Customize the template, then generate a Template Plan Review. The timeline is not changed until you click Apply in the review.</p>
                    </div>
                    <div className="review-actions">
                      <button className="primary-create" onClick={onApplyTemplateCustomization}><CheckCircle2 size={14} /> Generate Plan Review</button>
                      <button onClick={onSaveTemplateCustomization}><Save size={14} /> Save Preset</button>
                      <button onClick={onClose}><X size={14} /> Cancel</button>
                    </div>
                  </section>
                  <section className="wide-panel">
                    <h2><Wand2 size={16} /> Template Customizer</h2>
                    <div className="template-customizer-grid">
                      <label>
                        Platform
                        <select value={templateCustomizer.platform} onChange={(event) => updateTemplateCustomizer({ platform: event.target.value })}>
                          <option value="shorts">YouTube Shorts</option>
                          <option value="tiktok">TikTok</option>
                          <option value="instagram_reels">Instagram Reels</option>
                          <option value="youtube">YouTube normal video</option>
                          <option value="square">Square social</option>
                        </select>
                      </label>
                      <label>
                        Duration
                        <input type="number" min={5} max={180} value={templateCustomizer.duration} onChange={(event) => updateTemplateCustomizer({ duration: Number(event.target.value) || templateCustomizer.duration })} />
                      </label>
                      <label>
                        Caption style
                        <select value={templateCustomizer.captionStyle} onChange={(event) => updateTemplateCustomizer({ captionStyle: event.target.value })}>
                          <option>Large captions</option>
                          <option>Polished lower thirds</option>
                          <option>Quiet UI captions</option>
                          <option>Short hype captions</option>
                          <option>Safe readable captions</option>
                          <option>Cinematic title captions</option>
                        </select>
                      </label>
                      <label>
                        Pacing
                        <select value={templateCustomizer.pacing} onChange={(event) => updateTemplateCustomizer({ pacing: event.target.value })}>
                          <option>Fast hook-body-payoff</option>
                          <option>Smooth feature reveals</option>
                          <option>Step-by-step</option>
                          <option>High-energy highlights</option>
                          <option>Slow build and payoff</option>
                          <option>Restrained problem/solution</option>
                        </select>
                      </label>
                      <label>
                        Transition style
                        <select value={templateCustomizer.transitionStyle} onChange={(event) => updateTemplateCustomizer({ transitionStyle: event.target.value })}>
                          <option>clean cuts</option>
                          <option>crossfade</option>
                          <option>smooth cinematic</option>
                          <option>fast cuts</option>
                          <option>flash cuts</option>
                          <option>slide reveals</option>
                        </select>
                      </label>
                      <label>
                        Music intensity
                        <select value={templateCustomizer.musicIntensity} onChange={(event) => updateTemplateCustomizer({ musicIntensity: event.target.value })}>
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                        </select>
                      </label>
                      <label>
                        Intro/outro style
                        <select value={templateCustomizer.introOutroStyle} onChange={(event) => updateTemplateCustomizer({ introOutroStyle: event.target.value })}>
                          <option>logo reveal + CTA</option>
                          <option>hook title + quick CTA</option>
                          <option>step title + recap</option>
                          <option>cinematic title + fadeout</option>
                          <option>minimal title + soft fade</option>
                        </select>
                      </label>
                      <label className="check-control">
                        <input type="checkbox" checked={templateCustomizer.applyBranding} onChange={(event) => updateTemplateCustomizer({ applyBranding: event.target.checked })} />
                        Apply branding/logo when available
                      </label>
                    </div>
                  </section>
                  <section className="wide-panel">
                    <h2><ListVideo size={16} /> Template Plan Review Will Include</h2>
                    <div className="ai-plan-summary-grid">
                      <span>Scenes <strong>intro, body, payoff, outro</strong></span>
                      <span>Cuts <strong>{templateCustomizer.pacing}</strong></span>
                      <span>Captions <strong>{templateCustomizer.captionStyle}</strong></span>
                      <span>Effects <strong>{templateCustomizer.transitionStyle}</strong></span>
                      <span>Music <strong>{templateCustomizer.musicIntensity}</strong></span>
                      <span>Export <strong>{templatePlatformLabel(templateCustomizer.platform)}</strong></span>
                    </div>
                  </section>
                </>
              )}
            </div>
          )}
          {modal === "captionStyle" && (
            <div className="caption-style-picker">
              {["TikTok Bold", "Clean Lower Third", "Podcast Subtitles", "Educational Clear", "Cinematic Title", "Gaming Hype"].map((style) => (
                <button key={style} onClick={() => onCaptionStyle(style)}>
                  <strong>{style}</strong>
                  <span>{captionStyleDescription(style)}</span>
                </button>
              ))}
              <button className="span-2" onClick={onCaptions}><Sparkles size={15} /> Auto-generate captions from transcript</button>
            </div>
          )}
          {modal === "export" && (
            <RenderPanel
              preset={preset}
              setPreset={setPreset}
              exportFormat={exportFormat}
              setExportFormat={setExportFormat}
              quality={quality}
              setQuality={setQuality}
              cache={cache}
              setCache={setCache}
              resume={resume}
              setResume={setResume}
              gpu={gpu}
              setGpu={setGpu}
              logs={logs}
              renderQueueItems={renderQueueItems}
              project={project}
              finalPreflight={finalPreflight}
              onPreflight={onPreflight}
              onRepairPreflight={onRepairPreflight}
              onPreview={onPreview}
              onFinal={onFinal}
              onPauseQueue={onPauseQueue}
              onResumeQueue={onResumeQueue}
              onCancelJob={onCancelJob}
              onRetryJob={onRetryJob}
              onOpenOutput={onOpenOutput}
            />
          )}
          {modal === "renderProgress" && (
            <div className="render-progress-modal">
              <section className="wide-panel render-activity-hero">
                <h2><Play size={16} /> Render Activity</h2>
                <div className="progress-line">
                  <strong>{activeJob?.currentScene ? `Rendering ${activeJob.currentScene}` : processing.currentStage}</strong>
                  <span>{renderProgress.toFixed(0)}%</span>
                </div>
                <div className="progressbar"><span style={{ width: `${renderProgress}%` }} /></div>
                <div className="render-activity-grid">
                  <span>current task <strong>{activeJob?.label || processing.activeTask}</strong></span>
                  <span>rendering clip <strong>{activeJob?.currentScene || processing.currentScene || "waiting"}</strong></span>
                  <span>AI stage <strong>{processing.currentStage}</strong></span>
                  <span>ETA <strong>{formatEta(activeJob?.estimatedRemainingSeconds ?? processing.etaSeconds)}</strong></span>
                  <span>CPU <strong>{formatPercent(systemMetrics?.cpuPercent)}</strong></span>
                  <span>GPU <strong>{systemMetrics?.gpuProcessActive ? formatPercent(systemMetrics.gpuPercent) : gpu ? "enabled" : "off"}</strong></span>
                  <span>memory <strong>{formatMemory(systemMetrics)}</strong></span>
                  <span>encoder <strong>{gpu ? "GPU preferred" : "CPU"}</strong></span>
                </div>
                <p className="muted">{systemMetrics?.gpuMode || "Local activity updates keep the app responsive while work runs."}</p>
              </section>
              <section className="wide-panel">
                <h2><Clock size={16} /> Render Queue</h2>
                <div className="list">
                  {renderQueueItems.length === 0 && <span className="muted">No active render jobs.</span>}
                  {renderQueueItems.map((job) => (
                    <div className="queue-row" key={job.runId}>
                      <span>{job.label}</span>
                      <small>{job.currentScene || job.outputPath}</small>
                      <small className={job.status}>{job.status} {Number(job.progressPercent || 0).toFixed(0)}% | ETA {formatEta(job.estimatedRemainingSeconds)}</small>
                    </div>
                  ))}
                </div>
                <div className="review-actions">
                  <button onClick={onPauseQueue}><Pause size={14} /> Pause</button>
                  <button onClick={onResumeQueue}><Play size={14} /> Resume</button>
                  <button disabled={!activeJob} onClick={() => activeJob && onCancelJob(activeJob.runId)}>Cancel export</button>
                  <button onClick={onOpenOutput}><FolderOpen size={14} /> Open output folder</button>
                </div>
              </section>
              <section className="wide-panel">
                <h2>Errors / Warnings</h2>
                <div className="activity-feed compact-feed">
                  {latestIssues.length === 0 && <span className="muted">No current errors or warnings.</span>}
                  {latestIssues.map((item) => (
                    <div className={`activity-row ${item.kind}`} key={item.id}>
                      <strong>{activityGlyph(item.kind)}</strong>
                      <span>{item.label}</span>
                      <small>{item.detail || item.time}</small>
                    </div>
                  ))}
                </div>
              </section>
              <section className="wide-panel">
                <h2>Live Activity</h2>
                <div className="activity-feed">
                  {activityFeed.map((item) => (
                    <div className={`activity-row ${item.kind}`} key={item.id}>
                      <strong>{activityGlyph(item.kind)}</strong>
                      <span>{item.label}</span>
                      <small>{item.detail || item.time}</small>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
          {modal === "errorRecovery" && (
            <div className="error-recovery-modal">
              <section className="wide-panel">
                <h2><Wand2 size={16} /> Recovery Summary</h2>
                {!appError && !jsonParseError && !validation?.stderr && !finalPreflight?.issues?.length && <p className="muted">No active blocking issues detected.</p>}
                {appError && <p className="error">{appError}</p>}
                {jsonParseError && <p className="error">JSON parse error: {jsonParseError}</p>}
                {validation && !validation.ok && <p className="error">{validation.stderr || validation.stdout || "Validation failed"}</p>}
              </section>
              {finalPreflight?.issues?.length ? (
                <section className="wide-panel">
                  <h2><CheckCircle2 size={16} /> Preflight Issues</h2>
                  <div className="list">
                    {finalPreflight.issues.slice(0, 8).map((issue) => (
                      <div className="queue-row" key={issue.id}>
                        <span>{issue.message}</span>
                        <small className={issue.blocking ? "failed" : "running"}>{issue.severity}</small>
                        {issue.safeAutoFix && !issue.accepted && <button onClick={() => onRepairPreflight("selected", issue.id)}>Approve fix</button>}
                        {!issue.accepted && <button onClick={() => onRepairPreflight("ignore", issue.id)}>Accept</button>}
                        {issue.accepted && <small className="status-pill ok">accepted</small>}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}
              <section className="wide-panel">
                <h2>Manual Recovery</h2>
                <p className="muted">Preflight fixes require approval on each issue. The app will not apply bulk repairs automatically.</p>
                <div className="review-actions">
                  <button onClick={onRepair}><Wand2 size={14} /> Repair JSON</button>
                  <button onClick={onPreflight}><CheckCircle2 size={14} /> Run preflight</button>
                </div>
              </section>
            </div>
          )}
          {modal === "recoveryPrompt" && (
            <div className="error-recovery-modal">
              <section className="wide-panel recovery-hero">
                <h2><RefreshCw size={16} /> Recover unsaved project?</h2>
                <p className="muted">The previous session may not have closed cleanly. You can restore the latest autosave, choose another recovery point, or continue without changing the current project.</p>
                <div className="ai-plan-summary-grid">
                  <span>Last saved <strong>{startupRecovery?.lastSavedAt || startupRecovery?.latestRecovery?.timestamp || "unknown"}</strong></span>
                  <span>Latest point <strong>{startupRecovery?.latestRecovery?.type || "none"}</strong></span>
                  <span>Size <strong>{formatBytes(Number(startupRecovery?.latestRecovery?.size || 0))}</strong></span>
                  <span>Status <strong>{startupRecovery?.crashed ? "crash recovery available" : "manual recovery"}</strong></span>
                </div>
                <div className="review-actions">
                  <button className="primary-create" disabled={!startupRecovery?.latestRecovery} onClick={onRestoreStartupRecovery}><RefreshCw size={14} /> Restore Latest</button>
                  <button onClick={onDismissStartupRecovery}><X size={14} /> Continue Without Restoring</button>
                </div>
              </section>
              <section className="wide-panel">
                <h2><Clock size={16} /> Recovery Points</h2>
                <div className="list">
                  {recoveryPoints.length === 0 && <span className="muted">No recovery points available.</span>}
                  {recoveryPoints.slice(0, 8).map((point) => (
                    <div className="history-row" key={point.path}>
                      <strong>{point.type}</strong>
                      <span>{point.timestamp || point.path}</span>
                      <button onClick={() => onRestoreRecoveryPoint(point.path)}>Restore</button>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
          {modal === "versionCompare" && (
            <div className="error-recovery-modal">
              <section className="wide-panel">
                <h2><FileJson size={16} /> Version Comparison</h2>
                {!versionComparison ? (
                  <p className="muted">Choose Compare from Version History to inspect a snapshot.</p>
                ) : (
                  <>
                    <div className="ai-plan-summary-grid">
                      <span>Version <strong>{versionComparison.versionId}</strong></span>
                      <span>Scenes <strong>{versionComparison.old.scenes} {"->"} {versionComparison.new.scenes}</strong></span>
                      <span>Assets <strong>{versionComparison.old.assets} {"->"} {versionComparison.new.assets}</strong></span>
                      <span>Duration <strong>{Number(versionComparison.old.duration || 0).toFixed(1)}s {"->"} {Number(versionComparison.new.duration || 0).toFixed(1)}s</strong></span>
                    </div>
                    <div className="list">
                      {versionComparison.changes.map((change) => (
                        <div className="queue-row" key={change}><span>{change}</span><small>diff</small></div>
                      ))}
                    </div>
                    <details className="mini-details ai-advanced-reasoning">
                      <summary>Advanced: JSON snapshots</summary>
                      <div className="version-json-compare">
                        <pre className="mini-pre">{versionComparison.oldText}</pre>
                        <pre className="mini-pre">{versionComparison.newText}</pre>
                      </div>
                    </details>
                  </>
                )}
              </section>
            </div>
          )}
          {modal === "onboarding" && (
            <OnboardingFlow
              draft={onboardingDraft}
              setDraft={setOnboardingDraft}
              hardeningStatus={hardeningStatus}
              onPickExportFolder={async () => {
                const folder = await onPickExportFolder();
                if (folder) setOnboardingDraft((current) => ({ ...current, defaultExportFolder: folder }));
              }}
              onRunSystemCheck={onRunSystemCheck}
              onComplete={() => onCompleteOnboarding(onboardingDraft)}
              onOpenShortcuts={onShowShortcuts}
            />
          )}
          {modal === "shortcuts" && (
            <KeyboardShortcutsPanel />
          )}
          {modal === "workspace" && (
            <WorkspacePersonalizationPanel
              settings={settings}
              setSettings={setSettings}
              leftRailOpen={leftRailOpen}
              setLeftRailOpen={setLeftRailOpen}
              rightRailOpen={rightRailOpen}
              setRightRailOpen={setRightRailOpen}
              onApplyPreset={onApplyWorkspacePreset}
              onSaveLayout={onSaveWorkspaceLayout}
              onPopOutPanel={onPopOutPanel}
            />
          )}
          {modal === "settings" && (
            <div className="settings-modal">
              <label>Theme<select value={settings.theme} onChange={(event) => setSettings((current) => ({ ...current, theme: event.target.value as AppSettings["theme"] }))}><option value="aegis">Aegis dark</option><option value="midnight">Midnight</option><option value="slate">Slate</option><option value="high_contrast">High contrast</option><option value="graphite">Graphite legacy</option><option value="light">Light</option></select></label>
              <label>UI scale<select value={settings.uiScale} onChange={(event) => setSettings((current) => ({ ...current, uiScale: event.target.value as UiScale }))}><option value="small">Small</option><option value="medium">Medium</option><option value="large">Large</option><option value="auto">Auto DPI</option></select></label>
              <label>Accent color<input type="text" value={settings.accentColor} onChange={(event) => setSettings((current) => ({ ...current, accentColor: event.target.value }))} /></label>
              <label>Default workflow<select value={settings.defaultWorkflow} onChange={(event) => setSettings((current) => ({ ...current, defaultWorkflow: event.target.value as AppSettings["defaultWorkflow"] }))}><option value="quick">Quick Create</option><option value="guided">Guided Create</option><option value="advanced">Advanced Editor</option></select></label>
              <label>Default platform<select value={settings.defaultPlatform} onChange={(event) => setSettings((current) => ({ ...current, defaultPlatform: event.target.value }))}><option value="youtube_shorts">YouTube Shorts</option><option value="tiktok">TikTok</option><option value="instagram_reels">Reels</option><option value="standard">Standard video</option></select></label>
              <label>Default style<select value={settings.defaultStyle} onChange={(event) => setSettings((current) => ({ ...current, defaultStyle: event.target.value }))}><option value="clean">Clean</option><option value="gaming">Gaming</option><option value="cinematic">Cinematic</option><option value="podcast">Podcast</option><option value="educational">Educational</option><option value="hype">Hype</option></select></label>
              <label>Default export folder<input value={settings.defaultExportFolder || ""} readOnly placeholder="Use app exports folder" /></label>
              <button onClick={async () => {
                const folder = await onPickExportFolder();
                if (folder) setSettings((current) => ({ ...current, defaultExportFolder: folder }));
              }}><FolderOpen size={15} /> Choose export folder</button>
              <label>Preview start time<input type="number" value={settings.previewTimeSeconds} onChange={(event) => setSettings((current) => ({ ...current, previewTimeSeconds: Number(event.target.value) }))} /></label>
              <label><input type="checkbox" checked={settings.autosave} onChange={(event) => setSettings((current) => ({ ...current, autosave: event.target.checked }))} /> autosave</label>
              <label><input type="checkbox" checked={settings.keyboardShortcuts} onChange={(event) => setSettings((current) => ({ ...current, keyboardShortcuts: event.target.checked }))} /> keyboard shortcuts</label>
              <label><input type="checkbox" checked={settings.beginnerTips} onChange={(event) => setSettings((current) => ({ ...current, beginnerTips: event.target.checked }))} /> beginner tips</label>
              <button onClick={onSaveSettings}><Save size={15} /> Save settings</button>
              <small className="muted">Project: {projectPath || "unsaved"} / {project?.timeline?.length || 0} scenes</small>
            </div>
          )}
          {modal === "help" && (
            <HelpCenter onOpenDocs={onOpenDocs} onOpenShortcuts={onShowShortcuts} />
          )}
          {modal === "json" && (
            <JsonEditor text={projectText} schemaReady={engineReady} onChange={onJsonChange} onMount={onEditorMount} validation={validation} />
          )}
          {modal === "logs" && (
            <div className="logs-modal">
              <pre className="logs">{logs.join("\n") || "No render logs yet."}</pre>
              <div className="activity-feed">
                {activityFeed.map((item) => (
                  <div className={`activity-row ${item.kind}`} key={item.id}>
                    <strong>{activityGlyph(item.kind)}</strong>
                    <span>{item.label}</span>
                    <small>{item.detail || item.time}</small>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function AiPlanReviewModal({
  pendingAiPlan,
  fallbackReview,
  prompt,
  setPrompt,
  aiNotes,
  onGenerate,
  onPromptJson,
  onApply,
  onEdit,
  onRegenerate,
  onSaveTemplate,
  onCancel,
  onLockScene
}: {
  pendingAiPlan: PendingAiPlan | null;
  fallbackReview: GenerationReviewState | null;
  prompt: string;
  setPrompt: (value: string) => void;
  aiNotes: string;
  onGenerate: () => void;
  onPromptJson: () => void;
  onApply: () => void;
  onEdit: () => void;
  onRegenerate: () => void;
  onSaveTemplate: () => void;
  onCancel: () => void;
  onLockScene: (scene: string) => void;
}) {
  const parsedPending = pendingAiPlan ? parseProject(pendingAiPlan.text).data : null;
  const review = pendingAiPlan?.review || fallbackReview;
  const details = pendingAiPlan && parsedPending ? buildAiPlanDisplay(pendingAiPlan, parsedPending) : null;
  const isTemplatePlan = pendingAiPlan?.title.toLowerCase().includes("template");

  if (!pendingAiPlan || !details) {
    return (
      <div className="review-modal">
        <section className="wide-panel">
          <h2><Sparkles size={16} /> No AI plan yet</h2>
          <p className="muted">Ask AI what to make. The generated edit will appear here first as a plain-English plan, before anything changes on the timeline.</p>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          <div className="review-actions">
            <button onClick={onGenerate}><ListVideo size={15} /> Generate AI plan</button>
            <button onClick={onPromptJson}><Sparkles size={15} /> Prompt to plan</button>
            <button onClick={onCancel}><X size={15} /> Cancel</button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="review-modal ai-plan-review">
      <section className="wide-panel ai-plan-hero">
        <div>
          <span className="eyebrow">{pendingAiPlan.title}</span>
          <h2><Sparkles size={17} /> {isTemplatePlan ? "Template Plan Review" : "AI Edit Plan"}</h2>
          <p>{details.explanation}</p>
        </div>
        <div className="review-actions">
          <button className="primary-create" onClick={onApply}><CheckCircle2 size={14} /> {isTemplatePlan ? "Apply" : "Apply Plan"}</button>
          <button onClick={onEdit}><Wand2 size={14} /> {isTemplatePlan ? "Modify" : "Edit Plan"}</button>
          <button onClick={onRegenerate}><RefreshCw size={14} /> Regenerate</button>
          <button onClick={onSaveTemplate}><Save size={14} /> Save as Template</button>
          <button onClick={onCancel}><X size={14} /> Cancel</button>
        </div>
      </section>

      <section className="wide-panel">
        <h2><ListVideo size={16} /> Plan Summary</h2>
        <div className="ai-plan-summary-grid">
          {details.summary.map((item) => (
            <span key={item.label}>
              {item.label}
              <strong>{item.value}</strong>
            </span>
          ))}
        </div>
      </section>

      <section className="wide-panel">
        <h2><Bot size={16} /> Simple Explanation</h2>
        <p className="muted">{details.explanation}</p>
        {review?.warnings.length ? <p className="error">{review.warnings.join(" | ")}</p> : null}
        <details className="mini-details ai-advanced-reasoning">
          <summary>Advanced: AI reasoning / logs</summary>
          <pre className="mini-pre">{review?.reasoning || aiNotes || details.reasoning}</pre>
        </details>
      </section>

      <section className="wide-panel">
        <h2><Scissors size={16} /> Detected Highlights And Suggested Cuts</h2>
        <div className="ai-plan-columns">
          <div>
            <strong>Detected highlights</strong>
            {details.highlights.map((item) => <span key={item}>{item}</span>)}
          </div>
          <div>
            <strong>Suggested cuts</strong>
            {details.cuts.map((item) => <span key={item}>{item}</span>)}
          </div>
        </div>
      </section>

      <section className="wide-panel">
        <h2><MonitorPlay size={16} /> Scene-by-scene Breakdown</h2>
        <div className="scene-breakdown-list">
          {details.scenes.map((scene, index) => (
            <article key={scene.id}>
              <div className="scene-breakdown-header">
                <strong>Scene {index + 1}: {scene.name}</strong>
                <button onClick={() => onLockScene(scene.id)}>Lock</button>
              </div>
              <div className="scene-breakdown-grid">
                <span>Time range <strong>{scene.timeRange}</strong></span>
                <span>Purpose <strong>{scene.purpose}</strong></span>
                <span>Caption text <strong>{scene.caption}</strong></span>
                <span>Effect <strong>{scene.effect}</strong></span>
                <span>Transition <strong>{scene.transition}</strong></span>
                <span>Notes <strong>{scene.notes}</strong></span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function WorkspacePersonalizationPanel({
  settings,
  setSettings,
  leftRailOpen,
  setLeftRailOpen,
  rightRailOpen,
  setRightRailOpen,
  onApplyPreset,
  onSaveLayout,
  onPopOutPanel
}: {
  settings: AppSettings;
  setSettings: (value: AppSettings | ((value: AppSettings) => AppSettings)) => void;
  leftRailOpen: boolean;
  setLeftRailOpen: (value: boolean | ((current: boolean) => boolean)) => void;
  rightRailOpen: boolean;
  setRightRailOpen: (value: boolean | ((current: boolean) => boolean)) => void;
  onApplyPreset: (preset: WorkspacePreset) => void;
  onSaveLayout: () => void;
  onPopOutPanel: (panel: "preview" | "timeline" | "inspector") => void;
}) {
  const presets: Array<{ key: WorkspacePreset; title: string; detail: string }> = [
    { key: "beginner", title: "Beginner workspace", detail: "Preview-first, fewer panels, larger controls." },
    { key: "ai", title: "AI-focused workspace", detail: "AI Studio and inspector visible for plan review." },
    { key: "editing", title: "Editing workspace", detail: "Media, preview, timeline, and inspector balanced." },
    { key: "captions", title: "Caption workspace", detail: "Caption tools and detailed settings stay close." },
    { key: "export", title: "Export workspace", detail: "Final checks, presets, and inspector emphasized." },
    { key: "minimal", title: "Minimal workspace", detail: "Maximum focus with side panels collapsed." }
  ];
  return (
    <div className="workspace-settings-modal">
      <section className="wide-panel workspace-hero">
        <div>
          <span className="eyebrow">Workspace personalization</span>
          <h2><Maximize2 size={17} /> Layout and panels</h2>
          <p className="muted">These controls only rearrange the editor shell. They do not change the project JSON, render engine, timeline logic, or AI workflow.</p>
        </div>
        <div className="review-actions">
          <button className="primary-create" onClick={onSaveLayout}><Save size={15} /> Save Layout</button>
          <button onClick={() => onPopOutPanel("preview")}><MonitorPlay size={15} /> Pop Out Preview</button>
          <button onClick={() => onPopOutPanel("timeline")}><ListVideo size={15} /> Pop Out Timeline</button>
          <button onClick={() => onPopOutPanel("inspector")}><Settings size={15} /> Pop Out Inspector</button>
        </div>
      </section>

      <section className="wide-panel">
        <h2><LayoutTemplate size={16} /> Workspace Presets</h2>
        <div className="workspace-preset-grid">
          {presets.map((preset) => (
            <button className={settings.workspacePreset === preset.key ? "active" : ""} key={preset.key} onClick={() => onApplyPreset(preset.key)}>
              <strong>{preset.title}</strong>
              <span>{preset.detail}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="wide-panel">
        <h2><Scissors size={16} /> Dockable Panels</h2>
        <div className="workspace-control-grid">
          <label>
            Panel arrangement
            <select value={settings.panelDock} onChange={(event) => setSettings((current) => ({ ...current, panelDock: event.target.value as WorkspacePanelDock }))}>
              <option value="standard">Media left / Inspector right</option>
              <option value="inspector_left">Inspector left / Media right</option>
              <option value="media_right">Preview first / Media right</option>
              <option value="preview_focus">Preview focus</option>
            </select>
          </label>
          <label>
            Media panel width
            <input type="range" min={210} max={420} value={settings.leftRailWidth} onChange={(event) => setSettings((current) => ({ ...current, leftRailWidth: Number(event.target.value) }))} />
            <span>{settings.leftRailWidth}px</span>
          </label>
          <label>
            Inspector width
            <input type="range" min={280} max={520} value={settings.rightRailWidth} onChange={(event) => setSettings((current) => ({ ...current, rightRailWidth: Number(event.target.value) }))} />
            <span>{settings.rightRailWidth}px</span>
          </label>
          <label className="check-control">
            <input type="checkbox" checked={leftRailOpen} onChange={(event) => setLeftRailOpen(event.target.checked)} />
            Media sidebar visible
          </label>
          <label className="check-control">
            <input type="checkbox" checked={rightRailOpen} onChange={(event) => setRightRailOpen(event.target.checked)} />
            Inspector visible
          </label>
        </div>
      </section>

      <section className="wide-panel">
        <h2><Wand2 size={16} /> Theme and Scaling</h2>
        <div className="workspace-control-grid">
          <label>
            Theme
            <select value={settings.theme} onChange={(event) => setSettings((current) => ({ ...current, theme: event.target.value as AppTheme }))}>
              <option value="aegis">Aegis dark</option>
              <option value="midnight">Midnight</option>
              <option value="slate">Slate</option>
              <option value="high_contrast">High contrast</option>
              <option value="graphite">Graphite legacy</option>
              <option value="light">Light</option>
            </select>
          </label>
          <label>
            Accent color
            <input type="color" value={settings.accentColor || "#6db5a5"} onChange={(event) => setSettings((current) => ({ ...current, accentColor: event.target.value }))} />
          </label>
          <label>
            UI scale
            <select value={settings.uiScale} onChange={(event) => setSettings((current) => ({ ...current, uiScale: event.target.value as UiScale }))}>
              <option value="small">Small</option>
              <option value="medium">Medium</option>
              <option value="large">Large</option>
              <option value="auto">Auto DPI scaling</option>
            </select>
          </label>
        </div>
      </section>

      <section className="wide-panel">
        <h2><MonitorPlay size={16} /> Multi-Monitor Windows</h2>
        <p className="muted">Pop-out windows remember their last size and monitor position locally. Use them for preview, timeline, or inspector while keeping the main editor intact.</p>
        <div className="workspace-popout-grid">
          {(["preview", "timeline", "inspector"] as const).map((panel) => {
            const bounds = settings.monitorPositions?.[panel];
            return (
              <button key={panel} onClick={() => onPopOutPanel(panel)}>
                <strong>{friendlyPresetName(panel)}</strong>
                <span>{bounds ? `${bounds.width}x${bounds.height}${typeof bounds.x === "number" ? ` @ ${bounds.x},${bounds.y}` : ""}` : "No saved position yet"}</span>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function OnboardingFlow({
  draft,
  setDraft,
  hardeningStatus,
  onPickExportFolder,
  onRunSystemCheck,
  onComplete,
  onOpenShortcuts
}: {
  draft: AppSettings;
  setDraft: (value: AppSettings | ((value: AppSettings) => AppSettings)) => void;
  hardeningStatus: HardeningStatus | null;
  onPickExportFolder: () => void;
  onRunSystemCheck: () => void;
  onComplete: () => void;
  onOpenShortcuts: () => void;
}) {
  const dependency = hardeningStatus?.dependency as Record<string, unknown> | undefined;
  const ffmpeg = dependency?.ffmpeg as Record<string, unknown> | undefined;
  const readiness = dependency?.readiness as Record<string, unknown> | undefined;
  const performance = hardeningStatus?.performance as Record<string, unknown> | undefined;
  const cachePerf = performance?.cache as Record<string, unknown> | undefined;
  const gpuAvailable = Boolean(ffmpeg?.supportsGpuEncoding);
  const checks = [
    { label: "FFmpeg available", value: Boolean(ffmpeg?.installed), detail: String(ffmpeg?.version || "Run system check") },
    { label: "GPU encoding", value: gpuAvailable, detail: gpuAvailable ? "available" : "optional / not detected" },
    { label: "Storage/cache", value: true, detail: cachePerf?.totalBytes ? formatBytes(Number(cachePerf.totalBytes)) : "local cache ready" },
    { label: "Supported formats", value: true, detail: "MP4, MOV, MKV, WebM, PNG, JPG, MP3, WAV, FLAC" },
    { label: "Permissions", value: Boolean(readiness?.ready ?? true), detail: readiness?.ready ? "ready" : "review warnings" }
  ];
  return (
    <div className="onboarding-flow">
      <section className="wide-panel onboarding-hero">
        <span className="eyebrow">First launch setup</span>
        <h2><Sparkles size={18} /> Welcome to Automatic Video Editor</h2>
        <p className="muted">Pick a comfortable workflow now. You can still use every advanced tool later; this only sets friendly defaults.</p>
      </section>

      <section className="wide-panel">
        <h2>1. Choose workflow <button title="Quick Create is for one-click videos. Guided Create walks step-by-step. Advanced Editor opens the full timeline and JSON tools.">What does this do?</button></h2>
        <div className="choice-grid">
          {[
            ["quick", "Quick Create", "Select media, pick a style, generate an edit."],
            ["guided", "Guided Create", "Import, choose template, review AI plan, export."],
            ["advanced", "Advanced Editor", "Full timeline, JSON, inspector, logs, and render controls."]
          ].map(([key, title, body]) => (
            <button key={key} className={draft.defaultWorkflow === key ? "active" : ""} onClick={() => setDraft((current) => ({ ...current, defaultWorkflow: key as AppSettings["defaultWorkflow"] }))}>
              <strong>{title}</strong>
              <span>{body}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="wide-panel">
        <h2>2. Default platform</h2>
        <div className="choice-grid compact">
          {[
            ["youtube_shorts", "YouTube Shorts", "Vertical short-form"],
            ["tiktok", "TikTok", "Fast caption-heavy"],
            ["instagram_reels", "Reels", "Vertical social"],
            ["standard", "Standard video", "Landscape 16:9"]
          ].map(([key, title, body]) => (
            <button key={key} className={draft.defaultPlatform === key ? "active" : ""} onClick={() => setDraft((current) => ({ ...current, defaultPlatform: key }))}>
              <strong>{title}</strong>
              <span>{body}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="wide-panel">
        <h2>3. Editing style</h2>
        <div className="choice-grid compact">
          {["clean", "gaming", "cinematic", "podcast", "educational", "hype"].map((style) => (
            <button key={style} className={draft.defaultStyle === style ? "active" : ""} onClick={() => setDraft((current) => ({ ...current, defaultStyle: style }))}>
              <strong>{friendlyPresetName(style)}</strong>
              <span>{aiStyleDescription(style)}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="wide-panel">
        <h2>4. Default export folder</h2>
        <div className="folder-choice-row">
          <input readOnly value={draft.defaultExportFolder || ""} placeholder="Use the app exports folder" />
          <button onClick={onPickExportFolder}><FolderOpen size={14} /> Choose Folder</button>
        </div>
      </section>

      <section className="wide-panel">
        <h2>5. System check</h2>
        <div className="toolbar">
          <button onClick={onRunSystemCheck}><RefreshCw size={14} /> Run System Check</button>
          <button onClick={onOpenShortcuts}><Keyboard size={14} /> Keyboard Shortcuts</button>
        </div>
        <div className="system-check-grid">
          {checks.map((check) => (
            <span key={check.label} className={check.value ? "ok" : "warn"}>
              {check.value ? "OK" : "!"}
              <strong>{check.label}</strong>
              <small>{check.detail}</small>
            </span>
          ))}
        </div>
      </section>

      <section className="wide-panel onboarding-finish">
        <label className="check-control"><input type="checkbox" checked={draft.beginnerTips} onChange={(event) => setDraft((current) => ({ ...current, beginnerTips: event.target.checked }))} /> Show beginner tips while I learn</label>
        <button className="primary-create" onClick={onComplete}><CheckCircle2 size={15} /> Finish Setup</button>
      </section>
    </div>
  );
}

function KeyboardShortcutsPanel() {
  const shortcuts = [
    ["Ctrl+S", "Save project"],
    ["Ctrl+O", "Open project"],
    ["Ctrl+Enter", "Generate preview render"],
    ["Ctrl+Z", "Undo inside active editor/timeline"],
    ["Ctrl+Y", "Redo inside active editor/timeline"],
    ["Delete", "Ripple delete selected timeline scene"],
    ["Arrow Left / Right", "Nudge selected scene by snap amount"],
    ["Shift+Arrow", "Nudge selected scene faster"]
  ];
  return (
    <div className="shortcut-panel">
      <section className="wide-panel">
        <h2><Keyboard size={16} /> Keyboard Shortcuts</h2>
        <div className="shortcut-grid">
          {shortcuts.map(([keys, label]) => (
            <span key={keys}><kbd>{keys}</kbd><strong>{label}</strong></span>
          ))}
        </div>
      </section>
    </div>
  );
}

function HelpCenter({ onOpenDocs, onOpenShortcuts }: { onOpenDocs: () => void; onOpenShortcuts: () => void }) {
  const prompts = [
    "Make this into a YouTube Short with clean captions.",
    "Create a premium cinematic product showcase from this screen recording.",
    "Find the strongest moments, remove dead air, and add smooth zooms.",
    "Make this tutorial clear, slower paced, and easy to read."
  ];
  return (
    <div className="help-center">
      <section className="wide-panel">
        <h2><CircleHelp size={16} /> What does this app do?</h2>
        <p className="muted">It turns local media into an editable JSON timeline, lets AI propose edits for review, previews the result, then exports through FFmpeg. Advanced users can still open the raw JSON and logs.</p>
        <div className="button-grid compact">
          <button onClick={onOpenDocs}><CircleHelp size={16} /> Open bundled local docs</button>
          <button onClick={onOpenShortcuts}><Keyboard size={16} /> Keyboard shortcuts</button>
        </div>
      </section>
      <section className="wide-panel">
        <h2><Sparkles size={16} /> Example prompts</h2>
        <div className="example-prompt-grid">
          {prompts.map((item) => <span key={item}>{item}</span>)}
        </div>
      </section>
      <section className="wide-panel">
        <h2><Wand2 size={16} /> Beginner tips</h2>
        <div className="tip-card-grid">
          <span><strong>Start simple</strong> Import one video, choose Quick Create, then preview.</span>
          <span><strong>Review before applying</strong> AI plans show scenes and captions before changing the timeline.</span>
          <span><strong>Export last</strong> Use preview first, then run preflight before final render.</span>
          <span><strong>Advanced tools stay available</strong> JSON, logs, and diagnostics live under Advanced/Logs.</span>
        </div>
      </section>
    </div>
  );
}

function RenderActivityPopup({
  processing,
  activityFeed,
  renderQueueItems,
  logs,
  systemMetrics,
  gpuEnabled,
  minimized,
  onToggleMinimized,
  onOpenDetails,
  onPause,
  onResume,
  onCancel
}: {
  processing: ProcessingState;
  activityFeed: ProcessingActivity[];
  renderQueueItems: RenderQueueItem[];
  logs: string[];
  systemMetrics: SystemMetrics | null;
  gpuEnabled: boolean;
  minimized: boolean;
  onToggleMinimized: () => void;
  onOpenDetails: () => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: (runId: string) => void;
}) {
  const activeJob = activeRenderJob(renderQueueItems);
  const active = processing.isActive || Boolean(activeJob);
  if (!active && activityFeed.length === 0) return null;

  const progress = safePercent(activeJob ? Number(activeJob.progressPercent || 0) : processing.progress);
  const stage = activeJob?.currentScene ? `Rendering ${activeJob.currentScene}` : activeJob?.status === "queued" ? "Waiting in render queue" : processing.currentStage;
  const eta = activeJob?.estimatedRemainingSeconds ?? processing.etaSeconds;
  const latestIssues = latestRenderIssues(logs, activityFeed).slice(0, 3);

  return (
    <aside className={`render-activity-popup ${active ? "active" : ""} ${minimized ? "minimized" : ""}`}>
      <div className="render-popup-head">
        <div>
          <strong>{stage}</strong>
          <span>{activeJob?.label || processing.activeTask}</span>
        </div>
        <div className="render-popup-actions">
          <button onClick={onOpenDetails}>Details</button>
          <button onClick={onToggleMinimized}>{minimized ? "Expand" : "Minimize"}</button>
        </div>
      </div>
      <div className="progressbar"><span style={{ width: `${progress}%` }} /></div>
      {!minimized && (
        <>
          <div className="render-activity-grid compact">
            <span>progress <strong>{Math.round(progress)}%</strong></span>
            <span>ETA <strong>{formatEta(eta)}</strong></span>
            <span>clip <strong>{activeJob?.currentScene || processing.currentScene || "auto"}</strong></span>
            <span>CPU <strong>{formatPercent(systemMetrics?.cpuPercent)}</strong></span>
            <span>GPU <strong>{systemMetrics?.gpuProcessActive ? formatPercent(systemMetrics.gpuPercent) : gpuEnabled ? "enabled" : "off"}</strong></span>
            <span>warnings <strong>{latestIssues.length}</strong></span>
          </div>
          <div className="render-popup-controls">
            <button onClick={onPause}><Pause size={13} /> Pause</button>
            <button onClick={onResume}><Play size={13} /> Resume</button>
            <button disabled={!activeJob} onClick={() => activeJob && onCancel(activeJob.runId)}>Cancel</button>
          </div>
          <div className="render-popup-feed">
            {latestIssues.length === 0 ? (
              <span className="muted">No current errors or warnings.</span>
            ) : latestIssues.map((item) => (
              <div className={`activity-row ${item.kind}`} key={item.id}>
                <strong>{activityGlyph(item.kind)}</strong>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </aside>
  );
}

function ProcessingView({
  processing,
  activityFeed,
  renderQueueItems,
  project,
  generationReview,
  reasoning,
  assistantDraft,
  setAssistantDraft,
  assistantMessages,
  collapsed,
  setCollapsed,
  onSceneAction,
  onCaptionEdit,
  onAssistantSend,
  onSuggestion,
  onPause,
  onResume,
  onCancelActive,
  onPrioritizeActive,
  onPreviewPartial
}: {
  processing: ProcessingState;
  activityFeed: ProcessingActivity[];
  renderQueueItems: RenderQueueItem[];
  project: ProjectData | null;
  generationReview: GenerationReviewState | null;
  reasoning?: string;
  assistantDraft: string;
  setAssistantDraft: (value: string) => void;
  assistantMessages: CollaborationMessage[];
  collapsed: boolean;
  setCollapsed: (value: boolean) => void;
  onSceneAction: (sceneId: string, action: CollaborationSceneAction) => void;
  onCaptionEdit: (sceneId: string, text: string) => void;
  onAssistantSend: () => void;
  onSuggestion: (command: string) => void;
  onPause: () => void;
  onResume: () => void;
  onCancelActive: (runId: string) => void;
  onPrioritizeActive: (runId: string) => void;
  onPreviewPartial: (sceneId?: string) => void;
}) {
  const activeJob = renderQueueItems.find((job) => job.status === "running") || renderQueueItems.find((job) => job.status === "queued") || null;
  const progress = safePercent(activeJob ? Number(activeJob.progressPercent || 0) : processing.progress);
  const activeScene = activeJob?.currentScene || processing.currentScene || "";
  const stage = activeJob ? (activeJob.currentScene ? `Rendering ${activeJob.currentScene}` : activeJob.status === "queued" ? "Queued for rendering" : "Rendering") : processing.currentStage;
  const eta = activeJob?.estimatedRemainingSeconds ?? processing.etaSeconds;
  const workerRows = mergeProcessingWorkers(processing.workers, activeJob);
  const scenes = project?.timeline || [];
  const collaborationCards = collaborationSceneCards(project, generationReview);
  const suggestions = collaborationSuggestions(project, generationReview, processing);
  const activeSceneIndex = scenes.findIndex((scene) => scene.id === activeScene);
  const reasoningItems = processing.reasoning.length ? processing.reasoning : splitReasoning(reasoning || "");

  if (collapsed) {
    return (
      <section className={`processing-dock collapsed ${processing.isActive || activeJob ? "active" : ""}`}>
        <div className="processing-compact">
          <span className="ai-pulse" />
          <strong>{stage}</strong>
          <span>{processing.activeTask}</span>
          <div className="processing-progress"><span style={{ width: `${progress}%` }} /></div>
          <button onClick={() => setCollapsed(false)}><ChevronDown size={14} /> Show</button>
        </div>
      </section>
    );
  }

  return (
    <section className={`processing-dock ${processing.isActive || activeJob ? "active" : ""}`}>
      <div className="processing-main">
        <div className="processing-head">
          <div>
            <h2><Sparkles size={16} /> AI Activity</h2>
            <strong>{stage}</strong>
            <span>{processing.activeTask}</span>
          </div>
          <div className="processing-stats">
            <span>{Math.round(progress)}%</span>
            <small>ETA {formatEta(eta)}</small>
          </div>
        </div>
        <div className="processing-progress cinematic"><span style={{ width: `${progress}%` }} /><i style={{ left: `${progress}%` }} /></div>
        <div className="processing-context">
          <span>asset <strong>{processing.currentAsset || activeJob?.outputPath || "current project"}</strong></span>
          <span>scene <strong>{activeScene || "auto"}</strong></span>
          <span>encoder <strong>{activeJob ? "FFmpeg" : "engine"}</strong></span>
          <span>cache <strong>{workerRows.some((worker) => worker.name.toLowerCase().includes("cache")) ? "active" : "ready"}</strong></span>
        </div>
        <div className="processing-waveform" aria-hidden="true">
          {[18, 42, 28, 56, 24, 48, 34, 62, 30, 52, 22, 46, 38, 58].map((height, index) => <i key={index} style={{ height: `${height}%`, animationDelay: `${index * 0.05}s` }} />)}
        </div>
      </div>

      <div className="processing-side">
        <div className="processing-controls">
          <button onClick={onPause}><Pause size={14} /> Pause</button>
          <button onClick={onResume}><Play size={14} /> Resume</button>
          <button disabled={!activeJob} onClick={() => activeJob && onPrioritizeActive(activeJob.runId)}><RefreshCw size={14} /> Prioritize</button>
          <button disabled={!activeJob} onClick={() => activeJob && onCancelActive(activeJob.runId)}>Cancel</button>
          <button onClick={() => onPreviewPartial(activeScene || undefined)}><MonitorPlay size={14} /> Preview</button>
          <button onClick={() => setCollapsed(true)}><ChevronDown size={14} /> Background</button>
        </div>
        <div className="worker-grid">
          {workerRows.map((worker) => (
            <div className={`worker-chip ${worker.status}`} key={worker.name}>
              <span>{worker.name}</span>
              <strong>{worker.status}</strong>
              {typeof worker.progress === "number" && <div><i style={{ width: `${safePercent(worker.progress)}%` }} /></div>}
            </div>
          ))}
        </div>
      </div>

      {scenes.length > 0 && (
        <div className="generation-timeline">
          {scenes.slice(0, 14).map((scene, index) => {
            const hasCaptions = scene.layers?.some((layer) => layer.type === "text");
            const complete = activeSceneIndex >= 0 && index < activeSceneIndex;
            const active = scene.id === activeScene;
            return (
              <div className={`generation-scene ${active ? "active" : ""} ${complete ? "complete" : ""}`} key={scene.id} title={scene.id}>
                <strong>{scene.id}</strong>
                <span>{Number(scene.duration || 0).toFixed(1)}s</span>
                {hasCaptions && <small>captions</small>}
                {scene.transitionOut && <em>{String(scene.transitionOut.type || "transition")}</em>}
              </div>
            );
          })}
        </div>
      )}

      <div className="collaboration-grid">
        <div className="live-scenes">
          <div className="processing-section-title"><ListVideo size={14} /> Live Scene Generation</div>
          {collaborationCards.length === 0 && <span className="muted">Draft scene cards appear as project JSON is generated.</span>}
          {collaborationCards.slice(0, 6).map((card) => (
            <div className={`live-scene-card ${card.status}`} key={card.id}>
              <div className="live-scene-header">
                <strong>{card.label}</strong>
                <span className={card.confidence >= 78 ? "confidence good" : card.confidence >= 58 ? "confidence review" : "confidence low"}>
                  {card.confidence}% {card.confidenceLabel}
                </span>
              </div>
              <textarea
                defaultValue={card.caption}
                onBlur={(event) => event.target.value !== card.caption && onCaptionEdit(card.id, event.target.value)}
                title="Edit caption and click away to apply"
              />
              <div className="live-scene-meta">
                <span>clip <strong>{card.clip || "auto"}</strong></span>
                <span>transition <strong>{card.transition}</strong></span>
                <span>pacing <strong>{card.pacing}</strong></span>
              </div>
              {card.warnings.length > 0 && <small className="scene-warning">{card.warnings.join(" | ")}</small>}
              <div className="scene-action-row">
                <button onClick={() => onSceneAction(card.id, "approve")}>Approve</button>
                <button onClick={() => onSceneAction(card.id, "regenerate")}>Regenerate</button>
                <button onClick={() => onSceneAction(card.id, "lock")}>Lock</button>
                <button onClick={() => onSceneAction(card.id, "skip")}>Skip</button>
                <button onClick={() => onSceneAction(card.id, "faster")}>Faster</button>
                <button onClick={() => onSceneAction(card.id, "slower")}>Slower</button>
                <button onClick={() => onPreviewPartial(card.id)}><MonitorPlay size={13} /> Preview</button>
              </div>
            </div>
          ))}
        </div>

        <aside className="collab-sidebar">
          <div className="processing-section-title"><Bot size={14} /> AI Collaboration</div>
          <div className="live-suggestions">
            {suggestions.map((suggestion) => (
              <button key={suggestion.label} onClick={() => onSuggestion(suggestion.command)}>
                <strong>{suggestion.label}</strong>
                <span>{suggestion.reason}</span>
              </button>
            ))}
          </div>
          <div className="assistant-thread">
            {assistantMessages.length === 0 && <p className="muted">Type a direction like "make this darker" or "slow down the captions".</p>}
            {assistantMessages.slice(-6).map((message, index) => (
              <div className={`assistant-message ${message.role}`} key={`${message.time}-${index}`}>
                <strong>{message.role === "user" ? "You" : "Assistant"}</strong>
                <span>{message.text}</span>
                <small>{message.time}</small>
              </div>
            ))}
          </div>
          <div className="assistant-input">
            <textarea
              value={assistantDraft}
              onChange={(event) => setAssistantDraft(event.target.value)}
              onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                  event.preventDefault();
                  onAssistantSend();
                }
              }}
              placeholder="make this darker, slow captions, zoom more on the dashboard..."
            />
            <button onClick={onAssistantSend}><Wand2 size={14} /> Apply Live Edit</button>
          </div>
        </aside>
      </div>

      <div className="processing-bottom">
        <div className="activity-feed">
          <div className="processing-section-title"><Clock size={14} /> Live Activity</div>
          {activityFeed.length === 0 && <span className="muted">Activity appears here as the engine works.</span>}
          {activityFeed.slice(0, 12).map((item) => (
            <div className={`activity-row ${item.kind}`} key={item.id}>
              <strong>{activityGlyph(item.kind)}</strong>
              <span>{item.label}</span>
              <small>{item.detail || item.time}</small>
            </div>
          ))}
        </div>
        <details className="reasoning-panel ai-advanced-reasoning">
          <summary>Advanced: AI reasoning</summary>
          {reasoningItems.length === 0 ? (
            <p className="muted">Reasoning summaries appear after generated plans or AI Director runs.</p>
          ) : (
            reasoningItems.slice(0, 6).map((item, index) => <p key={`${item}-${index}`}>{item}</p>)
          )}
        </details>
      </div>
    </section>
  );
}

function ProactiveAssistantPanel({
  analysis,
  backgroundImprovements,
  muted,
  onMute,
  onApplySuggestion,
  onApplyImprovement,
  onDismissImprovement
}: {
  analysis: ProactiveAnalysis;
  backgroundImprovements: BackgroundImprovement[];
  muted: boolean;
  onMute: (value: boolean) => void;
  onApplySuggestion: (suggestion: ProactiveSuggestion) => void;
  onApplyImprovement: (improvement: BackgroundImprovement) => void;
  onDismissImprovement: (id: string) => void;
}) {
  const topSuggestions = [...analysis.issues, ...analysis.suggestions, ...analysis.optimizations, ...analysis.opportunities].slice(0, muted ? 2 : 7);
  return (
    <section className="panel proactive-panel">
      <div className="panel-head-row">
        <h2><Bot size={16} /> Proactive Assistant</h2>
        <button onClick={() => onMute(!muted)} title={muted ? "Show more suggestions" : "Quiet proactive suggestions"}>
          {muted ? "Quiet" : "Active"}
        </button>
      </div>
      <p className="muted">Local-only coaching from the current JSON, preview state, render queue, and creator memory.</p>
      <div className="proactive-score-row">
        <span>pacing <strong>{analysis.summary.pacingScore}</strong></span>
        <span>readability <strong>{analysis.summary.readabilityScore}</strong></span>
        <span>warnings <strong>{analysis.summary.warningCount}</strong></span>
      </div>
      <div className="proactive-list">
        {topSuggestions.length === 0 && <p className="muted">No urgent suggestions. The edit looks steady right now.</p>}
        {topSuggestions.map((suggestion) => (
          <div className={`proactive-card ${suggestion.severity}`} key={suggestion.id}>
            <div>
              <strong>{suggestion.title}</strong>
              <span>{suggestion.detail}</span>
              {typeof suggestion.time === "number" && <small>{formatTimestamp(suggestion.time)}</small>}
            </div>
            <button onClick={() => onApplySuggestion(suggestion)}>{suggestion.action === "preview_moment" ? "Open" : "Apply"}</button>
          </div>
        ))}
      </div>
      <details className="background-improvements" open={!muted}>
        <summary>Idle improvement queue ({backgroundImprovements.length})</summary>
        <div className="proactive-list">
          {backgroundImprovements.length === 0 && <p className="muted">When the app is idle, alternate hooks, captions, pacing tweaks, and thumbnail moments will appear here.</p>}
          {backgroundImprovements.slice(0, 5).map((item) => (
            <div className="proactive-card info" key={item.id}>
              <div>
                <strong>{item.title}</strong>
                <span>{item.detail}</span>
                {item.text && <small>{item.text}</small>}
              </div>
              <button onClick={() => onApplyImprovement(item)}>Use</button>
              <button onClick={() => onDismissImprovement(item.id)}>Skip</button>
            </div>
          ))}
        </div>
      </details>
      {analysis.coaching.length > 0 && (
        <div className="coach-note">
          <strong>{analysis.coaching[0].title}</strong>
          <span>{analysis.coaching[0].detail}</span>
        </div>
      )}
    </section>
  );
}

function BeginnerAutoTemplatePane({
  form,
  setForm,
  templates,
  summary,
  previewPath,
  adaptiveMemory,
  onApplyAdaptiveDefaults,
  onPickMedia,
  onPickImageFolder,
  onPickAssetFolder,
  onPickMusic,
  onPickLogo,
  onPreview,
  onFinal,
  onDuplicateProject,
  onAdvanced
}: {
  form: BeginnerFormState;
  setForm: (form: BeginnerFormState | ((form: BeginnerFormState) => BeginnerFormState)) => void;
  templates: BeginnerTemplateCard[];
  summary: Record<string, unknown> | null;
  previewPath: string | null;
  adaptiveMemory: AdaptiveWorkflowMemory | null;
  onApplyAdaptiveDefaults: () => void;
  onPickMedia: () => void;
  onPickImageFolder: () => void;
  onPickAssetFolder: () => void;
  onPickMusic: () => void;
  onPickLogo: () => void;
  onPreview: () => void;
  onFinal: () => void;
  onDuplicateProject: () => void;
  onAdvanced: () => void;
}) {
  const selectedTemplate = templates.find((item) => item.key === form.template) || templates[0];
  const quickRequest = beginnerRequestFromForm(form);
  const smartDefaults = beginnerSmartDefaults(selectedTemplate, quickRequest.targetPlatform);
  const adaptiveDefaults = adaptiveMemory?.smartDefaults || {};
  const adaptiveSuggestions = adaptiveMemory?.contextSuggestions || [];
  const outputs = summary?.outputs as Record<string, unknown> | undefined;
  const userSummary = summary?.userFacingSummary as Record<string, unknown> | undefined;
  const setField = <K extends keyof BeginnerFormState>(key: K, value: BeginnerFormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };
  const updateTemplate = (template: BeginnerTemplateCard) => {
    const defaults = templateQuickDefaults(template.key, template.platform);
    setForm((current) => ({
      ...current,
      template: template.key,
      targetPlatform: template.platform,
      duration: current.duration === defaultBeginnerForm.duration ? defaults.duration : current.duration,
      vibe: current.vibe.trim() ? current.vibe : defaults.vibe
    }));
  };
  const alternateHook = () => {
    setForm((current) => ({
      ...current,
      quickPrompt: `${current.quickPrompt.trim()}\nTry a stronger opening hook and keep the approved footage structure.`
    }));
  };
  return (
    <div className="beginner-pane">
      <section className="wide-panel beginner-intro">
        <div>
          <h2><Sparkles size={17} /> New Auto Video</h2>
          <p className="muted">Pick media, choose a premium template, type the idea, and the app handles the hidden JSON, safe defaults, preview cache, and render settings.</p>
        </div>
        <button onClick={onAdvanced}><FileJson size={15} /> Advanced Mode</button>
      </section>

      <section className="wide-panel quick-create-card">
        <div>
          <h2><Wand2 size={16} /> One-Click Quick Create</h2>
          <p className="muted">Write the request the way you would say it. Details below stay editable, but beginners can ignore them.</p>
        </div>
        <textarea value={form.quickPrompt} onChange={(event) => setField("quickPrompt", event.target.value)} />
        <div className="quick-create-actions">
          <button onClick={onPreview}><MonitorPlay size={15} /> Generate Preview</button>
          <button onClick={onFinal}><Play size={15} /> Render Final</button>
          <button onClick={onApplyAdaptiveDefaults}><RefreshCw size={15} /> Apply Smart Defaults</button>
        </div>
      </section>

      <section className="wide-panel adaptive-card">
        <h2><Bot size={16} /> Adaptive Workflow Intelligence</h2>
        <p className="muted">Local-only defaults learned from successful renders, review actions, and repeated corrections.</p>
        <div className="metric-grid smart-defaults">
          <span>template <strong>{String(adaptiveDefaults.template || form.template)}</strong></span>
          <span>export <strong>{String(adaptiveDefaults.exportPreset || smartDefaults.exportPreset)}</strong></span>
          <span>duration <strong>{String(adaptiveDefaults.duration || form.duration)}s</strong></span>
          <span>pacing <strong>{String(adaptiveDefaults.pacing || smartDefaults.pacing)}</strong></span>
          <span>captions <strong>{String(adaptiveDefaults.captionDensity || "medium")}</strong></span>
          <span>motion <strong>{String(adaptiveMemory?.preferences?.motionIntensity || "medium")}</strong></span>
        </div>
        <div className="adaptive-suggestions">
          {adaptiveSuggestions.slice(0, 3).map((suggestion, index) => (
            <span key={String(suggestion.id || index)}>
              <strong>{String(suggestion.title || "Suggestion")}</strong>
              {String(suggestion.reason || "")}
            </span>
          ))}
          {!adaptiveSuggestions.length && <span><strong>Fresh memory</strong>Generate or review a few edits and the app will start personalizing this panel.</span>}
        </div>
      </section>

      <section className="guidance-steps">
        {["Select media", "Pick template", "Describe goal", "Review preview"].map((step, index) => (
          <span key={step}><strong>{index + 1}</strong>{step}</span>
        ))}
      </section>

      <div className="beginner-grid">
        <section className="wide-panel">
          <h2><Video size={16} /> Media</h2>
          <div className="button-grid">
            <button onClick={onPickMedia}><Video size={15} /> MP4 / Video</button>
            <button onClick={onPickImageFolder}><Image size={15} /> Image Folder</button>
            <button onClick={onPickAssetFolder}><FolderOpen size={15} /> Asset Folder</button>
            <button onClick={onPickMusic}><Captions size={15} /> Music</button>
            <button onClick={onPickLogo}><Image size={15} /> Logo</button>
          </div>
          <div className="file-list">
            <span title={form.mediaFile || ""}>Video: {form.mediaFile || "not selected"}</span>
            <span title={form.imageFolder || ""}>Images: {form.imageFolder || "not selected"}</span>
            <span title={form.assetFolder || ""}>Assets: {form.assetFolder || "not selected"}</span>
            <span title={form.musicPath || ""}>Music: {form.musicPath || "optional"}</span>
            <span title={form.logoPath || ""}>Logo: {form.logoPath || "optional"}</span>
          </div>
        </section>

        <section className="wide-panel">
          <h2><LayoutTemplate size={16} /> Template</h2>
          <div className="beginner-template-grid">
            {templates.map((template) => (
              <button
                key={template.key}
                className={template.key === form.template ? "selected" : ""}
                onClick={() => updateTemplate(template)}
              >
                <strong>{template.name}</strong>
                <span>{template.aspectRatio} | {template.pacing}</span>
              </button>
            ))}
          </div>
          <p className="muted">{selectedTemplate.captionStyle}</p>
          <div className="metric-grid smart-defaults">
            <span>aspect <strong>{smartDefaults.aspectRatio}</strong></span>
            <span>render <strong>{smartDefaults.resolution}</strong></span>
            <span>captions <strong>{smartDefaults.captionSize}px</strong></span>
            <span>export <strong>{smartDefaults.exportPreset}</strong></span>
            <span>audio <strong>{smartDefaults.audioNormalization}</strong></span>
            <span>intensity <strong>{smartDefaults.transitionIntensity.toFixed(2)}</strong></span>
          </div>
        </section>
      </div>

      <section className="wide-panel">
        <h2><Wand2 size={16} /> Simple Info</h2>
        <div className="quick-derived">
          <span>From prompt: <strong>{quickRequest.productName || "product"}</strong></span>
          <span>{quickRequest.duration}s</span>
          <span>{(quickRequest.keyFeatures || []).slice(0, 3).join(" / ") || "features auto-detected"}</span>
        </div>
        <div className="form-grid">
          <label>
            Product name
            <input type="text" value={form.productName} onChange={(event) => setField("productName", event.target.value)} />
          </label>
          <label>
            Target platform
            <select value={form.targetPlatform} onChange={(event) => setField("targetPlatform", event.target.value)}>
              <option value="youtube">YouTube landscape</option>
              <option value="shorts">YouTube Shorts</option>
              <option value="tiktok">TikTok/Reels</option>
              <option value="square">Square</option>
            </select>
          </label>
          <label>
            Duration
            <input type="number" min={8} max={90} value={form.duration} onChange={(event) => setField("duration", Number(event.target.value))} />
          </label>
          <label>
            Desired vibe
            <input type="text" value={form.vibe} onChange={(event) => setField("vibe", event.target.value)} />
          </label>
        </div>
        <label>
          Video goal
          <textarea value={form.goal} onChange={(event) => setField("goal", event.target.value)} />
        </label>
        <label>
          Key features
          <textarea value={form.keyFeatures} onChange={(event) => setField("keyFeatures", event.target.value)} />
        </label>
        <div className="review-actions">
          <button onClick={onPreview}><MonitorPlay size={15} /> Generate Preview</button>
          <button onClick={onFinal}><Play size={15} /> Render Final MP4</button>
        </div>
      </section>

      <section className="wide-panel">
        <h2><RefreshCw size={16} /> Fast Iteration</h2>
        <p className="muted">Try a safer variation without rebuilding the whole project by hand.</p>
        <div className="button-grid compact">
          <button onClick={alternateHook}><Sparkles size={15} /> Alternate Hook</button>
          <button onClick={onPickMusic}><Captions size={15} /> Swap Music</button>
          <button onClick={onDuplicateProject}><FileJson size={15} /> Duplicate Edit</button>
          <button onClick={() => setForm((current) => {
            const next = nextBeginnerTemplate(templates, current.template);
            return { ...current, template: next.key, targetPlatform: next.platform };
          })}><LayoutTemplate size={15} /> Next Template</button>
        </div>
      </section>

      <section className="wide-panel">
        <h2><MonitorPlay size={16} /> Preview</h2>
        {previewPath ? (
          <video className="beginner-video" src={window.ave.toFileUrl(previewPath)} controls />
        ) : (
          <div className="empty-preview">Generated preview video appears here.</div>
        )}
        {summary && (
          <div className="beginner-output">
            <strong>{String(userSummary?.templateName || selectedTemplate.name)}</strong>
            <span>Hook: {String(userSummary?.hook || "generated after preview")}</span>
            <span>Project JSON: {String(outputs?.projectJson || "")}</span>
            {typeof outputs?.renderedVideo === "string" && <span>Rendered MP4: {outputs.renderedVideo}</span>}
          </div>
        )}
      </section>
    </div>
  );
}

function Dashboard({
  recent,
  templates,
  renderJobs,
  renderQueueItems,
  onOpenRecent,
  onTemplate
}: {
  recent: RecentProject[];
  templates: string[];
  renderJobs: RenderJob[];
  renderQueueItems: RenderQueueItem[];
  onOpenRecent: (path: string) => void;
  onTemplate: (template: string) => void;
}) {
  return (
    <div className="panel-stack">
      <details className="rail-section" open>
        <summary><Clock size={15} /> Recent Projects</summary>
        <div className="list">
          {recent.length === 0 && <span className="muted">No recent projects yet</span>}
          {recent.map((item) => (
            <button key={item.path} className="list-row" title={item.path} onClick={() => onOpenRecent(item.path)}>
              <FileJson size={14} />
              <span>{item.name}</span>
            </button>
          ))}
        </div>
      </details>
      <details className="rail-section" open>
        <summary><LayoutTemplate size={15} /> Template Gallery</summary>
        <div className="template-grid">
          {templates.map((template) => (
            <button key={template} onClick={() => onTemplate(template)} title={`Create ${templateLabels[template] || template}`}>
              {templateLabels[template] || template}
            </button>
          ))}
        </div>
      </details>
      <details className="rail-section">
        <summary><Scissors size={15} /> Render Queue</summary>
        <div className="list">
          {renderQueueItems.length === 0 && renderJobs.length === 0 && <span className="muted">No renders queued</span>}
          {renderQueueItems.map((job) => (
            <div className="queue-row" key={job.runId}>
              <span>{job.label}</span>
              <small className={job.status}>{job.status}</small>
            </div>
          ))}
          {renderQueueItems.length === 0 && renderJobs.map((job) => (
            <div className="queue-row" key={job.runId}>
              <span>{job.label}</span>
              <small className={job.status}>{job.status}</small>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}

function JsonEditor({
  text,
  schemaReady,
  onChange,
  onMount,
  validation
}: {
  text: string;
  schemaReady: boolean;
  onChange: (value: string) => void;
  onMount: OnMount;
  validation: EngineResult | null;
}) {
  return (
    <div className="editor-pane">
      <Editor
        height="100%"
        defaultLanguage="json"
        value={text}
        theme="vs-dark"
        loading="Loading Monaco..."
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          wordWrap: "on",
          tabSize: 2,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          formatOnPaste: true,
          formatOnType: true
        }}
        onMount={onMount}
        onChange={(value) => onChange(value || "")}
      />
      <div className="validation-strip">
        <span>{schemaReady ? "Schema validation active" : "Loading schema..."}</span>
        {validation && <span className={validation.ok ? "ok" : "error"}>{validation.ok ? "Valid JSON" : validation.stderr || validation.stdout}</span>}
      </div>
    </div>
  );
}

function VisualTimeline({
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
  interactivePreview?: InteractivePreviewState | null;
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
  const savedTimelineMarkers = Array.isArray(timelineMeta?.markers)
    ? (timelineMeta.markers as Array<Record<string, unknown>>)
    : [];
  const reviewMeta = project.metadata?.previewReview as Record<string, unknown> | undefined;
  const previewMarkers = Array.isArray(reviewMeta?.markers)
    ? (reviewMeta.markers as Array<Record<string, unknown>>).map((marker) => ({
      ...marker,
      label: marker.note || marker.label || marker.type || "review"
    }))
    : [];
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

  const beginResize = (sceneIndex: number, event: React.PointerEvent) => {
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

  const beginMove = (sceneIndex: number, event: React.PointerEvent) => {
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

  const dropAsset = (sceneIndex: number, event: React.DragEvent) => {
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

function PreviewWindow({
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
  interactivePreview: InteractivePreviewState | null;
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

type MediaBinCategory = "all" | "videos" | "images" | "audio" | "voiceovers" | "captions" | "generated" | "url" | "project";
type MediaSortMode = "name" | "date" | "duration";
type MediaContextMenu = { x: number; y: number; assetKey: string } | null;

function AssetLibrary({
  project,
  assets,
  assetReport,
  onImport,
  onAnalyze,
  onDropAsset,
  onProjectChange,
  onReplaceAsset,
  onFirstAiEdit
}: {
  project: ProjectData;
  assets: AssetCheck[];
  assetReport: Record<string, unknown> | null;
  onImport: () => void;
  onAnalyze: () => void;
  onDropAsset: (asset: ImportedAsset) => void;
  onProjectChange: (project: ProjectData) => void;
  onReplaceAsset: (assetKey: string) => void;
  onFirstAiEdit: () => void;
}) {
  const [activeCategory, setActiveCategory] = useState<MediaBinCategory>("all");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<AssetCheck["type"] | "all">("all");
  const [sortMode, setSortMode] = useState<MediaSortMode>("name");
  const [showUnusedOnly, setShowUnusedOnly] = useState(false);
  const [contextMenu, setContextMenu] = useState<MediaContextMenu>(null);
  const [previewAssetKey, setPreviewAssetKey] = useState<string>("");
  const [detailsAssetKey, setDetailsAssetKey] = useState<string>("");
  const analyzedAssets = Array.isArray(assetReport?.assets) ? assetReport.assets as Array<Record<string, unknown>> : [];
  const smartCollections = assetReport?.smartCollections && typeof assetReport.smartCollections === "object"
    ? assetReport.smartCollections as Record<string, Array<Record<string, unknown>>>
    : {};
  const smartRecommendations = Array.isArray(assetReport?.recommendations) ? assetReport.recommendations as Array<Record<string, unknown>> : [];
  const [activeSmartCollection, setActiveSmartCollection] = useState<string>("all");
  const categories: Array<{ key: MediaBinCategory; label: string; icon: ReactNode }> = [
    { key: "all", label: "All media", icon: <FolderOpen size={15} /> },
    { key: "videos", label: "Videos", icon: <Video size={15} /> },
    { key: "images", label: "Images", icon: <Image size={15} /> },
    { key: "audio", label: "Audio", icon: <Music size={15} /> },
    { key: "voiceovers", label: "Voiceovers", icon: <Mic size={15} /> },
    { key: "captions", label: "Captions", icon: <Captions size={15} /> },
    { key: "generated", label: "Generated assets", icon: <Sparkles size={15} /> },
    { key: "url", label: "Downloaded URL media", icon: <Download size={15} /> },
    { key: "project", label: "Project files", icon: <FileJson size={15} /> }
  ];

  useEffect(() => {
    const close = () => setContextMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("keydown", close);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("keydown", close);
    };
  }, []);

  function fileName(filePath: string) {
    return filePath.split(/[\\/]/).pop() || filePath;
  }

  function extension(filePath: string) {
    const name = fileName(filePath).toLowerCase();
    const match = name.match(/\.([a-z0-9]+)$/);
    return match ? match[1] : "";
  }

  function normalizedPath(filePath: string) {
    return filePath.replace(/\\/g, "/").toLowerCase();
  }

  function analyzedFor(asset: AssetCheck) {
    return analyzedAssets.find((item) =>
      String(item.key || "") === asset.key ||
      normalizedPath(String(item.path || item.activePath || item.projectPath || "")) === normalizedPath(asset.path)
    );
  }

  function smartTags(meta?: Record<string, unknown>) {
    return Array.isArray(meta?.smartTags) ? meta.smartTags.map((tag) => String(tag)) : [];
  }

  function recommendationText(meta?: Record<string, unknown>) {
    if (!Array.isArray(meta?.recommendations)) return "";
    return meta.recommendations.map((item) => String((item as Record<string, unknown>).message || "")).join(" ");
  }

  function itemMatchesCollection(asset: { key: string; path: string }, collection: string) {
    if (collection === "all") return true;
    const entries = smartCollections[collection] || [];
    return entries.some((item) =>
      String(item.key || "") === asset.key ||
      normalizedPath(String(item.path || "")) === normalizedPath(asset.path)
    );
  }

  function usageCount(assetKey: string) {
    let count = 0;
    for (const scene of project.timeline || []) {
      for (const layer of scene.layers || []) {
        if (layer.asset === assetKey) count += 1;
      }
    }
    for (const audio of project.audio || []) {
      if (audio.asset === assetKey) count += 1;
    }
    for (const caption of project.captions || []) {
      if (caption.asset === assetKey) count += 1;
    }
    return count;
  }

  function assetCategory(asset: AssetCheck): MediaBinCategory {
    const joined = `${asset.key} ${asset.path}`.toLowerCase();
    const ext = extension(asset.path);
    if (joined.includes("download") || joined.includes("url_media") || joined.includes("http_")) return "url";
    if (joined.includes("generated") || joined.includes(".ave_media") || joined.includes("thumbnail") || joined.includes("preview")) return "generated";
    if (["srt", "vtt", "ass", "ssa", "txt"].includes(ext) || joined.includes("caption") || joined.includes("subtitle")) return "captions";
    if (asset.type === "audio" && /(voice|voiceover|narration|vo_|_vo|dialog)/.test(joined)) return "voiceovers";
    if (asset.type === "video") return "videos";
    if (asset.type === "image") return "images";
    if (asset.type === "audio") return "audio";
    return "project";
  }

  function mediaIcon(asset: AssetCheck, category: MediaBinCategory) {
    if (category === "captions") return <Captions size={30} />;
    if (category === "voiceovers") return <Mic size={30} />;
    if (category === "generated") return <Sparkles size={30} />;
    if (category === "url") return <Download size={30} />;
    if (asset.type === "image") return <Image size={30} />;
    if (asset.type === "audio") return <Music size={30} />;
    if (asset.type === "video") return <Video size={30} />;
    return <FileText size={30} />;
  }

  function durationFor(meta?: Record<string, unknown>) {
    const duration = Number(meta?.duration ?? meta?.durationSeconds ?? 0);
    return Number.isFinite(duration) && duration > 0 ? `${duration.toFixed(duration > 20 ? 0 : 1)}s` : "-";
  }

  function durationValue(meta?: Record<string, unknown>) {
    const duration = Number(meta?.duration ?? meta?.durationSeconds ?? 0);
    return Number.isFinite(duration) ? duration : 0;
  }

  function dateValue(asset: AssetCheck, meta?: Record<string, unknown>) {
    return Number(asset.modifiedMs ?? meta?.modifiedMs ?? meta?.mtimeMs ?? 0) || 0;
  }

  function thumbnailFor(asset: AssetCheck, meta?: Record<string, unknown>) {
    const thumbnail = String(meta?.thumbnail || meta?.thumbnailPath || meta?.previewThumbnail || "");
    if (thumbnail) return thumbnail;
    return asset.type === "image" && asset.exists ? asset.path : "";
  }

  function renameAsset(asset: AssetCheck) {
    const nextKey = window.prompt("Rename asset in project", asset.key)?.trim();
    if (!nextKey || nextKey === asset.key) return;
    if (project.assets?.[nextKey]) {
      window.alert("That asset name already exists.");
      return;
    }
    const next = structuredClone(project);
    next.assets = { ...(next.assets || {}) };
    const existingValue = next.assets[asset.key];
    if (!existingValue) return;
    next.assets[nextKey] = existingValue;
    delete next.assets[asset.key];
    for (const scene of next.timeline || []) {
      for (const layer of scene.layers || []) {
        if (layer.asset === asset.key) layer.asset = nextKey;
      }
    }
    for (const audio of next.audio || []) {
      if (audio.asset === asset.key) audio.asset = nextKey;
    }
    for (const caption of next.captions || []) {
      if (caption.asset === asset.key) caption.asset = nextKey;
    }
    onProjectChange(next);
  }

  function removeFromProject(asset: AssetCheck) {
    const used = usageCount(asset.key);
    const message = used
      ? `${asset.key} is used ${used} time(s). Remove it from the project and timeline references? This will not delete the original file.`
      : `Remove ${asset.key} from the project? This will not delete the original file.`;
    if (!window.confirm(message)) return;
    const next = structuredClone(project);
    next.assets = { ...(next.assets || {}) };
    delete next.assets[asset.key];
    next.timeline = (next.timeline || []).map((scene) => ({
      ...scene,
      layers: (scene.layers || []).filter((layer) => layer.asset !== asset.key)
    }));
    next.audio = (next.audio || []).filter((audio) => audio.asset !== asset.key);
    next.captions = (next.captions || []).filter((caption) => caption.asset !== asset.key);
    onProjectChange(next);
  }

  function contextAction(asset: AssetCheck, action: "add" | "preview" | "rename" | "replace" | "reveal" | "remove" | "details") {
    setContextMenu(null);
    if (action === "add") onDropAsset({ key: asset.key, path: asset.path, type: asset.type });
    if (action === "preview") setPreviewAssetKey(asset.key);
    if (action === "rename") renameAsset(asset);
    if (action === "replace") onReplaceAsset(asset.key);
    if (action === "reveal") void window.ave.revealPath(asset.path);
    if (action === "remove") removeFromProject(asset);
    if (action === "details") setDetailsAssetKey(asset.key);
  }

  const mediaItems = assets.map((asset) => {
    const meta = analyzedFor(asset);
    const category = assetCategory(asset);
    const usedCount = usageCount(asset.key);
    return {
      ...asset,
      category,
      meta,
      usedCount,
      name: fileName(asset.path),
      ext: extension(asset.path),
      duration: durationFor(meta),
      durationValue: durationValue(meta),
      resolution: meta ? formatResolution(meta.resolution) : "-",
      modifiedValue: dateValue(asset, meta),
      thumbnail: thumbnailFor(asset, meta),
      smartTags: smartTags(meta),
      smartRecommendationText: recommendationText(meta),
      searchText: String(meta?.searchText || "")
    };
  });

  const filteredItems = mediaItems
    .filter((asset) => activeCategory === "all" || asset.category === activeCategory)
    .filter((asset) => itemMatchesCollection(asset, activeSmartCollection))
    .filter((asset) => typeFilter === "all" || asset.type === typeFilter)
    .filter((asset) => !showUnusedOnly || asset.usedCount === 0)
    .filter((asset) => {
      const haystack = `${asset.key} ${asset.name} ${asset.ext} ${asset.smartTags.join(" ")} ${asset.smartRecommendationText} ${asset.searchText}`.toLowerCase();
      return haystack.includes(query.trim().toLowerCase());
    })
    .sort((a, b) => {
      if (sortMode === "duration") return b.durationValue - a.durationValue;
      if (sortMode === "date") return b.modifiedValue - a.modifiedValue;
      return a.key.localeCompare(b.key);
    });

  const selectedPreview = mediaItems.find((asset) => asset.key === previewAssetKey);
  const selectedDetails = mediaItems.find((asset) => asset.key === detailsAssetKey);
  const menuAsset = contextMenu ? mediaItems.find((asset) => asset.key === contextMenu.assetKey) : null;

  return (
    <div className="assets-pane">
      <div className="asset-tools">
        <button onClick={onImport}><Plus size={15} /> Import Media</button>
        <button onClick={onAnalyze}><CheckCircle2 size={15} /> Analyze</button>
        <span>{Object.keys(project.assets || {}).length} JSON assets</span>
        <span>{assets.filter((asset) => !asset.exists).length} missing</span>
      </div>
      {assets.length > 0 && (
        <section className="first-ai-edit-card">
          <div>
            <span className="eyebrow">Next step</span>
            <strong>Ready for your first AI edit</strong>
            <p>Use AI Studio to describe the video you want. It will make a reviewable plan first, then you choose when to apply it.</p>
          </div>
          <ol>
            <li>Generate AI plan</li>
            <li>Review scenes and captions</li>
            <li>Apply to timeline</li>
            <li>Preview, then export</li>
          </ol>
          <button className="primary-create" onClick={onFirstAiEdit}><Sparkles size={15} /> Start first AI edit</button>
        </section>
      )}
      <div className="media-bin-layout">
        <aside className="media-bin-categories">
          {categories.map((category) => (
            <button
              key={category.key}
              className={activeCategory === category.key ? "active" : ""}
              onClick={() => setActiveCategory(category.key)}
            >
              {category.icon}
              <span>{category.label}</span>
              <small>{category.key === "all" ? mediaItems.length : mediaItems.filter((asset) => asset.category === category.key).length}</small>
            </button>
          ))}
        </aside>
        <section className="media-bin-main">
          <div className="smart-assets-panel">
            <div className="panel-head-row">
              <div>
                <span className="eyebrow">Smart Assets</span>
                <strong>Collections and suggestions</strong>
              </div>
              <button onClick={onAnalyze}><Sparkles size={14} /> Refresh analysis</button>
            </div>
            <div className="smart-collection-grid">
              <button className={activeSmartCollection === "all" ? "active" : ""} onClick={() => setActiveSmartCollection("all")}>
                <strong>All analyzed</strong>
                <span>{analyzedAssets.length || mediaItems.length}</span>
              </button>
              {Object.entries(smartCollections).map(([name, items]) => (
                <button className={activeSmartCollection === name ? "active" : ""} key={name} onClick={() => setActiveSmartCollection(name)}>
                  <strong>{name}</strong>
                  <span>{items.length}</span>
                </button>
              ))}
            </div>
            <div className="smart-recommendations">
              {smartRecommendations.slice(0, 4).map((item, index) => (
                <button key={`${String(item.asset)}-${index}`} onClick={() => {
                  setQuery(String(item.asset || ""));
                  setDetailsAssetKey(String(item.asset || ""));
                }}>
                  <strong>{String(item.asset || "asset")}</strong>
                  <span>{String(item.message || item.type || "AI suggestion")}</span>
                </button>
              ))}
              {!smartRecommendations.length && <span className="muted">Run Analyze to create smart tags, collections, recommendations, and searchable words.</span>}
            </div>
          </div>
          <div className="media-bin-search">
            <label>
              <Search size={14} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name, spoken words, tags, emotion, or activity..." />
            </label>
            <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as AssetCheck["type"] | "all")}>
              <option value="all">All types</option>
              <option value="video">Video</option>
              <option value="image">Image</option>
              <option value="audio">Audio</option>
              <option value="unknown">Project/other</option>
            </select>
            <select value={sortMode} onChange={(event) => setSortMode(event.target.value as MediaSortMode)}>
              <option value="name">Sort by name</option>
              <option value="date">Sort by date</option>
              <option value="duration">Sort by duration</option>
            </select>
            <label className="media-bin-checkbox"><input type="checkbox" checked={showUnusedOnly} onChange={(event) => setShowUnusedOnly(event.target.checked)} /> unused only</label>
          </div>
          <div className="asset-grid media-bin-grid">
        {filteredItems.map((asset) => (
          <button
            key={asset.key}
            className={`asset-tile ${asset.exists ? "" : "missing"}`}
            title={asset.path}
            draggable
            onDragStart={(event) => event.dataTransfer.setData("text/plain", asset.key)}
            onDoubleClick={() => onDropAsset({ key: asset.key, path: asset.path, type: asset.type })}
            onContextMenu={(event) => {
              event.preventDefault();
              setContextMenu({ x: event.clientX, y: event.clientY, assetKey: asset.key });
            }}
          >
            <span className="asset-thumb">
              {asset.thumbnail ? <img src={window.ave.toFileUrl(asset.thumbnail)} alt="" /> : mediaIcon(asset, asset.category)}
            </span>
            <strong>{asset.key}</strong>
            <span>{asset.name}</span>
            <span>{asset.duration} / {asset.resolution}</span>
            <span>{asset.ext || asset.type} / {asset.usedCount ? "used" : "unused"}</span>
            {asset.smartTags.length > 0 ? (
              <span className="asset-smart-tags">{asset.smartTags.slice(0, 3).map((tag) => <em key={tag}>{tag.replace(/_/g, " ")}</em>)}</span>
            ) : asset.meta && <span>analyzed</span>}
            <i className="asset-menu-hint"><MoreVertical size={14} /></i>
          </button>
        ))}
            {!filteredItems.length && <div className="empty-media-bin">No media matches the current filters.</div>}
          </div>
        </section>
      </div>
      {menuAsset && contextMenu && (
        <div className="media-context-menu" style={{ left: contextMenu.x, top: contextMenu.y }} onClick={(event) => event.stopPropagation()}>
          <button onClick={() => contextAction(menuAsset, "add")}><Plus size={14} /> Add to timeline</button>
          <button onClick={() => contextAction(menuAsset, "preview")}><Eye size={14} /> Preview</button>
          <button onClick={() => contextAction(menuAsset, "rename")}><Pencil size={14} /> Rename</button>
          <button onClick={() => contextAction(menuAsset, "replace")}><RefreshCcw size={14} /> Replace media</button>
          <button onClick={() => contextAction(menuAsset, "reveal")}><FolderOpen size={14} /> Reveal in folder</button>
          <button onClick={() => contextAction(menuAsset, "details")}><CircleHelp size={14} /> View file details</button>
          <button className="danger" onClick={() => contextAction(menuAsset, "remove")}><Trash2 size={14} /> Remove from project</button>
        </div>
      )}
      {selectedPreview && (
        <div className="media-preview-panel">
          <div>
            <strong>Preview: {selectedPreview.key}</strong>
            <button onClick={() => setPreviewAssetKey("")}><X size={14} /></button>
          </div>
          {selectedPreview.type === "video" && selectedPreview.exists && <video src={window.ave.toFileUrl(selectedPreview.path)} controls />}
          {selectedPreview.type === "image" && selectedPreview.exists && <img src={window.ave.toFileUrl(selectedPreview.path)} alt="" />}
          {selectedPreview.type === "audio" && selectedPreview.exists && <audio src={window.ave.toFileUrl(selectedPreview.path)} controls />}
          {(!selectedPreview.exists || selectedPreview.type === "unknown") && <p className="muted">{selectedPreview.path}</p>}
        </div>
      )}
      {selectedDetails && (
        <div className="inspector-list media-details-panel">
          <h3>File Details</h3>
          <div className="inspector-row">
            <strong>{selectedDetails.key}</strong>
            <span>{selectedDetails.name}</span>
            <small>{selectedDetails.path}</small>
            <small>type {selectedDetails.type} / ext {selectedDetails.ext || "-"} / {selectedDetails.exists ? "exists" : "missing"}</small>
            <small>duration {selectedDetails.duration} / resolution {selectedDetails.resolution} / usage {selectedDetails.usedCount ? "used" : "unused"}</small>
            {selectedDetails.smartTags.length > 0 && <small>smart tags: {selectedDetails.smartTags.join(", ")}</small>}
            {selectedDetails.smartRecommendationText && <small>suggestions: {selectedDetails.smartRecommendationText}</small>}
          </div>
          {selectedDetails.meta && <pre className="mini-pre">{JSON.stringify(selectedDetails.meta, null, 2)}</pre>}
          <button onClick={() => setDetailsAssetKey("")}>Close details</button>
        </div>
      )}
      {assetReport && (
        <div className="inspector-list">
          <h3>Asset Intelligence</h3>
          {analyzedAssets.map((item) => (
            <div className="inspector-row" key={String(item.key)}>
              <strong>{String(item.key)}</strong>
              <span>{String(item.type)} | {String(item.duration ?? 0)}s | {formatResolution(item.resolution)}</span>
              <small>motion {String(item.motionIntensity ?? "-")} | codec {String(item.codec ?? "-")}</small>
              {Array.isArray(item.dominantColors) && (
                <div className="swatches">{(item.dominantColors as string[]).map((color) => <i key={color} style={{ background: color }} />)}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DirectorWorkspace({
  goal,
  setGoal,
  report,
  onRun,
  onResolveBroll,
  onStoryboard,
  onAnalyzeAssets
}: {
  goal: string;
  setGoal: (value: string) => void;
  report: Record<string, unknown> | null;
  onRun: () => void;
  onResolveBroll: () => void;
  onStoryboard: () => void;
  onAnalyzeAssets: () => void;
}) {
  const suggestions = Array.isArray(report?.suggestions) ? report.suggestions as string[] : [];
  const changedScenes = Array.isArray(report?.changedScenes) ? report.changedScenes as string[] : [];
  return (
    <div className="workflow-pane">
      <section className="wide-panel">
        <h2><Bot size={16} /> AI Director</h2>
        <textarea value={goal} onChange={(event) => setGoal(event.target.value)} />
        <div className="button-grid compact">
          <button onClick={onRun}><Sparkles size={15} /> Run Director</button>
          <button onClick={onResolveBroll}><Video size={15} /> Resolve B-Roll</button>
          <button onClick={onStoryboard}><LayoutTemplate size={15} /> Storyboard</button>
          <button onClick={onAnalyzeAssets}><CheckCircle2 size={15} /> Assets</button>
        </div>
      </section>
      <section className="wide-panel">
        <h2><FileJson size={16} /> Director Report</h2>
        {report ? (
          <div className="report-grid">
            <div>
              <strong>Summary</strong>
              <p>{String(report.summary || "")}</p>
            </div>
            <div>
              <strong>Changed Scenes</strong>
              <p>{changedScenes.join(", ") || "none"}</p>
            </div>
            <div className="span-2">
              <strong>Suggestions</strong>
              {suggestions.map((item) => <p key={item}>{item}</p>)}
            </div>
          </div>
        ) : (
          <p className="muted">No director pass yet.</p>
        )}
      </section>
    </div>
  );
}

function StoryboardPane({ storyboard, onGenerate }: { storyboard: Record<string, unknown> | null; onGenerate: () => void }) {
  const scenes = Array.isArray(storyboard?.scenes) ? storyboard.scenes as Array<Record<string, unknown>> : [];
  return (
    <div className="storyboard-pane">
      <div className="asset-tools">
        <button onClick={onGenerate}><LayoutTemplate size={15} /> Generate Storyboard</button>
        <span>{scenes.length} scenes</span>
      </div>
      <div className="storyboard-grid">
        {scenes.map((scene) => (
          <article className="story-card" key={String(scene.id)}>
            {Boolean(scene.thumbnail) && <img src={window.ave.toFileUrl(String(scene.thumbnail))} alt="" />}
            <strong>{String(scene.id)}</strong>
            <span>{String(scene.start)}s / {String(scene.duration)}s</span>
            <p>{String(scene.summary || "")}</p>
            <small>{JSON.stringify(scene.transitionOut || {})}</small>
          </article>
        ))}
        {!scenes.length && <span className="muted">No storyboard generated.</span>}
      </div>
    </div>
  );
}

function WorkflowPane({
  projectPath,
  history,
  projectHealth,
  plugins,
  renderQueueItems,
  onExportPackage,
  onOpenPackage,
  onRollback,
  onDuplicateVersion,
  onCompareVersion,
  onHealthCheck,
  onRefreshHistory,
  onPauseQueue,
  onResumeQueue,
  onCancelJob,
  onRetryJob,
  onPrioritizeJob,
  onInitPlugin
}: {
  projectPath: string | null;
  history: HistoryVersion[];
  projectHealth: ProjectHealthReport | null;
  plugins: PluginInfo[];
  renderQueueItems: RenderQueueItem[];
  onExportPackage: () => void;
  onOpenPackage: () => void;
  onRollback: (versionId: string) => void;
  onDuplicateVersion: (versionId: string) => void;
  onCompareVersion: (versionId: string) => void;
  onHealthCheck: () => void;
  onRefreshHistory: () => void;
  onPauseQueue: () => void;
  onResumeQueue: () => void;
  onCancelJob: (runId: string) => void;
  onRetryJob: (runId: string) => void;
  onPrioritizeJob: (runId: string, priority: number) => void;
  onInitPlugin: (name: string, type: string) => void;
}) {
  const [pluginName, setPluginName] = useState("Custom Punch Transition");
  const [pluginType, setPluginType] = useState("transition");
  return (
    <div className="workflow-pane">
      <section className="wide-panel">
        <h2><Scissors size={16} /> Render Queue</h2>
        <div className="toolbar">
          <button onClick={onPauseQueue}><Pause size={15} /> Pause</button>
          <button onClick={onResumeQueue}><Play size={15} /> Resume</button>
        </div>
        <div className="list">
          {renderQueueItems.length === 0 && <span className="muted">No queued renders.</span>}
          {renderQueueItems.map((job) => (
            <div className="queue-row expanded" key={job.runId}>
              <span>{job.label}</span>
              <small className={job.status}>{job.status}</small>
              <button onClick={() => onPrioritizeJob(job.runId, job.priority + 1)}>Priority</button>
              <button onClick={() => onCancelJob(job.runId)}>Cancel</button>
              <button onClick={() => onRetryJob(job.runId)}>Retry</button>
            </div>
          ))}
        </div>
      </section>
      <section className="wide-panel">
        <h2><FileJson size={16} /> Version History</h2>
        <div className="toolbar">
          <button onClick={onRefreshHistory} disabled={!projectPath}><RefreshCw size={15} /> Refresh</button>
          <button onClick={onHealthCheck}><CheckCircle2 size={15} /> Health Check</button>
        </div>
        <div className="list">
          {history.length === 0 && <span className="muted">No saved AI edits.</span>}
          {history.map((item) => (
            <div className="history-row" key={item.id}>
              <strong>{String(item.name || item.summary || item.id)}</strong>
              <span>{item.summary || item.timestamp}</span>
              <button disabled={!projectPath} onClick={() => onCompareVersion(item.id)}>Compare</button>
              <button disabled={!projectPath} onClick={() => onDuplicateVersion(item.id)}>Duplicate</button>
              <button disabled={!projectPath} onClick={() => onRollback(item.id)}>Rollback</button>
            </div>
          ))}
        </div>
      </section>
      <section className="wide-panel">
        <h2><CheckCircle2 size={16} /> Project Health</h2>
        <div className="toolbar">
          <button onClick={onHealthCheck}><RefreshCw size={15} /> Run Check</button>
          {projectHealth && <span className={projectHealth.ready ? "status-pill ok" : "status-pill warn"}>{projectHealth.score}/100</span>}
        </div>
        {!projectHealth ? (
          <p className="muted">Run a health check to catch missing files, corrupt JSON, unsupported formats, empty scenes, and failed renders.</p>
        ) : (
          <div className="list">
            {projectHealth.issues.length === 0 && <span className="muted">No project health issues found.</span>}
            {projectHealth.issues.slice(0, 8).map((issue) => (
              <div className="queue-row expanded" key={issue.id}>
                <span>{issue.message}</span>
                <small className={issue.severity === "error" ? "failed" : issue.severity === "warning" ? "running" : "completed"}>{issue.severity}</small>
                <small>{issue.suggestion}</small>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="wide-panel">
        <h2><FolderOpen size={16} /> Project Package</h2>
        <div className="button-grid compact">
          <button onClick={onExportPackage}><Save size={15} /> Export Zip</button>
          <button onClick={onOpenPackage}><FolderOpen size={15} /> Open Zip</button>
        </div>
      </section>
      <section className="wide-panel">
        <h2><Wand2 size={16} /> Plugins</h2>
        <div className="plugin-create">
          <input value={pluginName} onChange={(event) => setPluginName(event.target.value)} />
          <select value={pluginType} onChange={(event) => setPluginType(event.target.value)}>
            <option value="transition">transition</option>
            <option value="effect">effect</option>
            <option value="template">template</option>
            <option value="export_preset">export_preset</option>
          </select>
          <button onClick={() => onInitPlugin(pluginName, pluginType)}><Plus size={15} /> Create</button>
        </div>
        <div className="list">
          {plugins.map((plugin) => (
            <div className="queue-row" key={plugin.id}>
              <span>{plugin.name}</span>
              <small>{plugin.type}</small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function ProductPane({
  project,
  settings,
  realtimePreview,
  previewTimeSeconds,
  setPreviewTimeSeconds,
  previewSceneId,
  setPreviewSceneId,
  previewQualityMode,
  setPreviewQualityMode,
  previewLayerMode,
  setPreviewLayerMode,
  qualityReport,
  manifestReport,
  repurposeReport,
  postingPackageReport,
  postExportReview,
  postExportTemplate,
  postExportVariants,
  postExportNote,
  templatePacks,
  recoveryPoints,
  renderedVideoPath,
  socialTargets,
  setSocialTargets,
  onRealtimePreview,
  onQualityCheck,
  onManifest,
  onReformat,
  onRepurpose,
  onPostPackage,
  onPostExportReview,
  onQuickReExport,
  onSaveReusableTemplate,
  onCreatePostExportVariants,
  onSavePostExportNote,
  onCreateBrandKit,
  onApplyBrandKit,
  onExportTemplate,
  onInstallTemplate,
  onSaveSettings,
  onAutosaveNow,
  onRefreshRecovery,
  onRestoreRecovery,
  hardeningStatus,
  onRefreshHardening,
  workflowDashboard,
  onRefreshWorkflowDashboard,
  frictionReport,
  onRefreshFrictionReport,
  adaptiveMemory,
  onRefreshAdaptiveMemory,
  onApplyAdaptiveDefaults,
  feedbackAnalysis,
  feedbackReview,
  creatorIdentity,
  evolutionReport,
  onFeedbackAnalyze,
  onFeedbackReview,
  onFeedbackLearn,
  onEvolutionReport,
  onOpenDocs
}: {
  project: ProjectData | null;
  settings: AppSettings;
  realtimePreview: Record<string, unknown> | null;
  previewTimeSeconds: number;
  setPreviewTimeSeconds: (value: number) => void;
  previewSceneId: string;
  setPreviewSceneId: (value: string) => void;
  previewQualityMode: string;
  setPreviewQualityMode: (value: string) => void;
  previewLayerMode: string;
  setPreviewLayerMode: (value: string) => void;
  qualityReport: Record<string, unknown> | null;
  manifestReport: Record<string, unknown> | null;
  repurposeReport: Record<string, unknown> | null;
  postingPackageReport: Record<string, unknown> | null;
  postExportReview: Record<string, unknown> | null;
  postExportTemplate: Record<string, unknown> | null;
  postExportVariants: Record<string, unknown> | null;
  postExportNote: Record<string, unknown> | null;
  templatePacks: TemplatePack[];
  recoveryPoints: RecoveryPoint[];
  renderedVideoPath: string | null;
  socialTargets: string[];
  setSocialTargets: (value: string[]) => void;
  onRealtimePreview: () => void;
  onQualityCheck: () => void;
  onManifest: () => void;
  onReformat: () => void;
  onRepurpose: (renderBatch: boolean, maxVariants: number, reuseStyle: boolean) => void;
  onPostPackage: () => void;
  onPostExportReview: () => void;
  onQuickReExport: (mode: string, preset?: string, captions?: string) => void;
  onSaveReusableTemplate: (name: string, note: string) => void;
  onCreatePostExportVariants: () => void;
  onSavePostExportNote: (profile: string, tags: string[], note: string) => void;
  onCreateBrandKit: () => void;
  onApplyBrandKit: () => void;
  onExportTemplate: (template: string) => void;
  onInstallTemplate: () => void;
  onSaveSettings: (settings: AppSettings) => void;
  onAutosaveNow: () => void;
  onRefreshRecovery: () => void;
  onRestoreRecovery: (sourcePath: string) => void;
  hardeningStatus: HardeningStatus | null;
  onRefreshHardening: () => void;
  workflowDashboard: Record<string, unknown> | null;
  onRefreshWorkflowDashboard: () => void;
  frictionReport: FrictionReport | null;
  onRefreshFrictionReport: () => void;
  adaptiveMemory: AdaptiveWorkflowMemory | null;
  onRefreshAdaptiveMemory: () => void;
  onApplyAdaptiveDefaults: () => void;
  feedbackAnalysis: Record<string, unknown> | null;
  feedbackReview: Record<string, unknown> | null;
  creatorIdentity: Record<string, unknown> | null;
  evolutionReport: Record<string, unknown> | null;
  onFeedbackAnalyze: () => void;
  onFeedbackReview: (profile: string, ratings: Record<string, number>, note: string) => void;
  onFeedbackLearn: (profile: string) => void;
  onEvolutionReport: (profile: string) => void;
  onOpenDocs: () => void;
}) {
  const [draftSettings, setDraftSettings] = useState(settings);
  const [feedbackProfile, setFeedbackProfile] = useState("Aegis Creator");
  const [feedbackNote, setFeedbackNote] = useState("");
  const [reuseTemplateName, setReuseTemplateName] = useState("Reusable Showcase Style");
  const [successTags, setSuccessTags] = useState<string[]>(["reuse_this"]);
  const [repurposeMaxVariants, setRepurposeMaxVariants] = useState(18);
  const [repurposeReuseStyle, setRepurposeReuseStyle] = useState(true);
  const [feedbackRatings, setFeedbackRatings] = useState<Record<string, number>>({
    pacing: 4,
    readability: 4,
    transitions: 4,
    cinematicQuality: 4,
    hookStrength: 4,
    captionQuality: 4,
    overallPolish: 4
  });
  const duration = project ? totalTimelineDuration(project) : 0;
  const qualityIssues = Array.isArray(qualityReport?.issues) ? qualityReport.issues as Array<Record<string, unknown>> : [];
  const manifestAssets = Array.isArray(manifestReport?.assets) ? manifestReport.assets as Array<Record<string, unknown>> : [];
  const postingPackages = Array.isArray(postingPackageReport?.platforms) ? postingPackageReport.platforms as Array<Record<string, unknown>> : [];
  const repurposeOutputs = Array.isArray(repurposeReport?.outputs) ? repurposeReport.outputs as Array<Record<string, unknown>> : [];
  const postExportIssues = Array.isArray(postExportReview?.issues) ? postExportReview.issues as Array<Record<string, unknown>> : [];
  const postExportPlayback = postExportReview?.playbackReview as Record<string, unknown> | undefined;
  const postExportThumbnail = typeof postExportPlayback?.thumbnail === "string" ? postExportPlayback.thumbnail : "";
  const postExportVariantsList = Array.isArray(postExportVariants?.outputs) ? postExportVariants.outputs as Array<Record<string, unknown>> : [];
  const socialOptions = ["youtube_shorts", "tiktok", "instagram_reels", "youtube_landscape", "discord", "x_twitter"];
  const framePath = typeof realtimePreview?.frame === "string" ? realtimePreview.frame : "";
  const dependency = hardeningStatus?.dependency as Record<string, unknown> | undefined;
  const model = hardeningStatus?.model as Record<string, unknown> | undefined;
  const privacy = hardeningStatus?.privacy as Record<string, unknown> | undefined;
  const performance = hardeningStatus?.performance as Record<string, unknown> | undefined;
  const ffmpeg = dependency?.ffmpeg as Record<string, unknown> | undefined;
  const readiness = dependency?.readiness as Record<string, unknown> | undefined;
  const ollama = model?.ollama as Record<string, unknown> | undefined;
  const whisper = model?.whisper as Record<string, unknown> | undefined;
  const renderPerf = performance?.render as Record<string, unknown> | undefined;
  const cachePerf = performance?.cache as Record<string, unknown> | undefined;
  const privacyFlags = privacy?.privacy as Record<string, unknown> | undefined;
  const readinessWarnings = Array.isArray(readiness?.warnings) ? readiness.warnings : [];
  const workflowRecentRenders = Array.isArray(workflowDashboard?.recentRenders) ? workflowDashboard.recentRenders as Array<Record<string, unknown>> : [];
  const workflowStorage = workflowDashboard?.storage as Record<string, unknown> | undefined;
  const workflowAssetDb = workflowDashboard?.assetDatabase as Record<string, unknown> | undefined;
  const workflowProjectHealth = workflowDashboard?.projectHealth as Record<string, unknown> | undefined;
  const workflowMetrics = workflowDashboard?.metrics as Record<string, unknown> | undefined;
  const workflowTransitions = workflowMetrics?.mostUsedTransitions as Record<string, unknown> | undefined;
  const workflowHealth = Array.isArray(workflowDashboard?.workflowHealth) ? workflowDashboard.workflowHealth : [];
  const adaptiveDefaults = adaptiveMemory?.smartDefaults || {};
  const adaptiveFingerprint = adaptiveMemory?.creatorFingerprint || {};
  const adaptiveRecovery = adaptiveMemory?.recoverySignals || {};
  const adaptiveFriction = adaptiveMemory?.friction || {};
  const adaptiveSuggestions = adaptiveMemory?.contextSuggestions || [];
  const feedbackPacing = feedbackAnalysis?.pacing as Record<string, unknown> | undefined;
  const feedbackCaptions = feedbackAnalysis?.captions as Record<string, unknown> | undefined;
  const feedbackWarnings = Array.isArray(feedbackAnalysis?.warnings) ? feedbackAnalysis.warnings : [];
  const feedbackRecommendations = Array.isArray(feedbackAnalysis?.recommendations) ? feedbackAnalysis.recommendations : [];
  const identityModel = creatorIdentity?.preferenceModel as Record<string, unknown> | undefined;
  const evolutionNextActions = Array.isArray(evolutionReport?.nextActions) ? evolutionReport.nextActions : [];
  const evolutionProject = evolutionReport?.projectIntelligence as Record<string, unknown> | undefined;
  const evolutionArchitecture = evolutionReport?.engineArchitecture as Record<string, unknown> | undefined;
  const evolutionAudit = evolutionArchitecture?.auditSummary as Record<string, unknown> | undefined;

  useEffect(() => setDraftSettings(settings), [settings]);

  function toggleTarget(target: string) {
    if (socialTargets.includes(target)) {
      setSocialTargets(socialTargets.filter((item) => item !== target));
    } else {
      setSocialTargets([...socialTargets, target]);
    }
  }

  function toggleSuccessTag(tag: string) {
    setSuccessTags((current) => current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag]);
  }

  return (
    <div className="workflow-pane product-pane">
      <section className="wide-panel">
        <h2><MonitorPlay size={16} /> Real-Time Preview</h2>
        <div className="preview-mini">
          {framePath ? <img src={window.ave.toFileUrl(framePath)} alt="" /> : <span className="muted">No cached frame yet.</span>}
        </div>
        <div className="control-grid">
          <label>
            Time
            <input
              type="number"
              min={0}
              max={duration || 999}
              step={0.05}
              value={previewTimeSeconds}
              onChange={(event) => setPreviewTimeSeconds(Number(event.target.value))}
            />
          </label>
          <label>
            Scene
            <select value={previewSceneId} onChange={(event) => setPreviewSceneId(event.target.value)}>
              <option value="">auto</option>
              {(project?.timeline || []).map((scene) => <option key={scene.id} value={scene.id}>{scene.id}</option>)}
            </select>
          </label>
          <label>
            Quality
            <select value={previewQualityMode} onChange={(event) => setPreviewQualityMode(event.target.value)}>
              <option value="draft">draft</option>
              <option value="proxy">proxy</option>
              <option value="balanced">balanced</option>
              <option value="high">high</option>
              <option value="final_sim">final sim</option>
            </select>
          </label>
          <label>
            Layers
            <select value={previewLayerMode} onChange={(event) => setPreviewLayerMode(event.target.value)}>
              <option value="all">all</option>
              <option value="media">media</option>
              <option value="text">text</option>
            </select>
          </label>
        </div>
        <button onClick={onRealtimePreview}><MonitorPlay size={15} /> Cache Frame</button>
        {realtimePreview && (
          <div className="metric-grid">
            <span>scene <strong>{String(realtimePreview.sceneId || "-")}</strong></span>
            <span>cached <strong>{String(Boolean(realtimePreview.cached))}</strong></span>
            <span>effects <strong>{String(Array.isArray(realtimePreview.effects) ? realtimePreview.effects.length : 0)}</strong></span>
          </div>
        )}
      </section>

      <section className="wide-panel">
        <h2><CheckCircle2 size={16} /> Quality Checker</h2>
        <button onClick={onQualityCheck}><CheckCircle2 size={15} /> Run Check</button>
        {qualityReport ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>passed <strong>{String(Boolean(qualityReport.passed))}</strong></span>
              <span>issues <strong>{String(qualityReport.issueCount ?? qualityIssues.length)}</strong></span>
            </div>
            {qualityIssues.map((issue, index) => (
              <div className="inspector-row" key={`${String(issue.message)}-${index}`}>
                <strong>{String(issue.severity || "warning")}</strong>
                <span>{String(issue.asset || issue.scene || "project")}</span>
                <small>{String(issue.message || "")}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No quality report generated.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><FileJson size={16} /> Collaboration Format</h2>
        <button onClick={onManifest}><FileJson size={15} /> Generate Manifest</button>
        {manifestReport ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>format <strong>{String(manifestReport.formatVersion || "-")}</strong></span>
              <span>assets <strong>{String(manifestReport.assetCount ?? manifestAssets.length)}</strong></span>
              <span>portable <strong>{String(Boolean((manifestReport.checks as Record<string, unknown> | undefined)?.portable))}</strong></span>
            </div>
            {manifestAssets.slice(0, 5).map((asset) => (
              <div className="inspector-row" key={String(asset.key)}>
                <strong>{String(asset.key)}</strong>
                <span>{String(asset.portable ? "portable" : "needs recovery")}</span>
                <small>{String(asset.sha256 || "").slice(0, 18)} | {formatBytes(Number(asset.size || 0))}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No manifest generated.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><Scissors size={16} /> Auto Social Reformat</h2>
        <div className="target-grid">
          {socialOptions.map((target) => (
            <label key={target}>
              <input type="checkbox" checked={socialTargets.includes(target)} onChange={() => toggleTarget(target)} />
              {target}
            </label>
          ))}
        </div>
        <button onClick={onReformat}><RefreshCw size={15} /> Create Variants</button>
      </section>

      <section className="wide-panel">
        <h2><Sparkles size={16} /> Content Repurposing</h2>
        <p className="muted">Turn this edit into platform-ready versions with hook and CTA variants while keeping the successful style intact.</p>
        <div className="control-grid">
          <label>
            Max variants
            <input type="number" min={1} max={66} value={repurposeMaxVariants} onChange={(event) => setRepurposeMaxVariants(Number(event.target.value))} />
          </label>
          <label>
            Reuse style
            <select value={repurposeReuseStyle ? "yes" : "no"} onChange={(event) => setRepurposeReuseStyle(event.target.value === "yes")}>
              <option value="yes">same lighting/pacing/captions</option>
              <option value="no">strip style metadata</option>
            </select>
          </label>
        </div>
        <div className="button-grid compact">
          <button onClick={() => onRepurpose(false, repurposeMaxVariants, repurposeReuseStyle)}><FileJson size={15} /> Generate JSONs</button>
          <button onClick={() => onRepurpose(true, Math.min(repurposeMaxVariants, 6), repurposeReuseStyle)}><MonitorPlay size={15} /> Batch Export</button>
        </div>
        {repurposeReport ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>variants <strong>{String(repurposeReport.count ?? repurposeOutputs.length)}</strong></span>
              <span>rendered <strong>{String(Boolean(repurposeReport.rendered))}</strong></span>
              <span>folder <strong>{String(repurposeReport.outputDir || "-")}</strong></span>
            </div>
            {repurposeOutputs.slice(0, 8).map((item) => (
              <div className="inspector-row" key={`${String(item.platform)}-${String(item.variantType)}-${String(item.variant)}`}>
                <strong>{String(item.platform)}</strong>
                <span>{String(item.variantType)}:{String(item.variant)}</span>
                <small>{String(item.renderedVideo || item.projectPath || "")}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No repurposed versions yet.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><Image size={16} /> Posting Package</h2>
        <p className="muted">{renderedVideoPath ? `Using ${renderedVideoPath}` : "Render an MP4 first, then create an upload-ready folder."}</p>
        <button onClick={onPostPackage}><FolderOpen size={15} /> Create Upload Package</button>
        {postingPackageReport ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>platforms <strong>{String(postingPackages.length)}</strong></span>
              <span>folder <strong>{String(postingPackageReport.outputDir || "-")}</strong></span>
            </div>
            {postingPackages.map((item) => (
              <div className="inspector-row" key={String(item.platform)}>
                <strong>{String(item.platform)}</strong>
                <span>{String(item.ready ? "ready" : "review")}</span>
                <small>{String(item.folder || "")}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No posting package created yet.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><MonitorPlay size={16} /> Post-Export Review + Reuse</h2>
        {renderedVideoPath ? (
          <video className="export-player" src={window.ave.toFileUrl(renderedVideoPath)} controls />
        ) : (
          <p className="muted">Render or package a final video before post-export review.</p>
        )}
        <div className="button-grid compact">
          <button onClick={onPostExportReview}><CheckCircle2 size={15} /> Review Export</button>
          <button onClick={() => onQuickReExport("lower_size", "low_size_preview")}><RefreshCw size={15} /> Lower Size</button>
          <button onClick={() => onQuickReExport("higher_quality", "high_quality_archive")}><RefreshCw size={15} /> Higher Quality</button>
          <button onClick={() => onQuickReExport("captions_off", undefined, "off")}><Captions size={15} /> Captions Off</button>
          <button onClick={onCreatePostExportVariants}><Sparkles size={15} /> Create Variants</button>
        </div>
        {postExportReview ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>playable <strong>{String(Boolean(postExportPlayback?.playable))}</strong></span>
              <span>duration <strong>{String(postExportPlayback?.duration ?? "-")}s</strong></span>
              <span>audio <strong>{String(Boolean(postExportPlayback?.hasAudio))}</strong></span>
              <span>issues <strong>{String(postExportIssues.length)}</strong></span>
            </div>
            {postExportThumbnail && <img className="thumbnail-strip" src={window.ave.toFileUrl(postExportThumbnail)} alt="" />}
            {postExportIssues.slice(0, 6).map((issue) => (
              <div className="inspector-row" key={String(issue.id)}>
                <strong>{String(issue.severity || "info")}</strong>
                <span>{String(issue.id || "export")}</span>
                <small>{String(issue.message || "")} {String(issue.suggestion || "")}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No post-export diagnostics yet.</p>
        )}
        <div className="control-grid">
          <label>
            Template name
            <input value={reuseTemplateName} onChange={(event) => setReuseTemplateName(event.target.value)} />
          </label>
          <label>
            Success note
            <input value={feedbackNote} onChange={(event) => setFeedbackNote(event.target.value)} placeholder="What should be reused later?" />
          </label>
        </div>
        <div className="target-grid">
          {["good_pacing", "good_style", "reuse_this", "too_much_motion", "captions_too_fast"].map((tag) => (
            <label key={tag}>
              <input type="checkbox" checked={successTags.includes(tag)} onChange={() => toggleSuccessTag(tag)} />
              {tag}
            </label>
          ))}
        </div>
        <div className="button-grid compact">
          <button onClick={() => onSaveReusableTemplate(reuseTemplateName, feedbackNote)}><Save size={15} /> Save Template</button>
          <button onClick={() => onSavePostExportNote(feedbackProfile, successTags, feedbackNote)}><Wand2 size={15} /> Save Success Note</button>
        </div>
        {postExportTemplate && (
          <div className="metric-grid">
            <span>template <strong>{String(postExportTemplate.name || "-")}</strong></span>
            <span>path <strong>{String(postExportTemplate.path || "-")}</strong></span>
          </div>
        )}
        {postExportVariants && (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>variants <strong>{String(postExportVariantsList.length)}</strong></span>
              <span>folder <strong>{String(postExportVariants.outputDir || "-")}</strong></span>
            </div>
            {postExportVariantsList.slice(0, 6).map((variant) => (
              <div className="inspector-row" key={String(variant.variant)}>
                <strong>{String(variant.variant)}</strong>
                <span>{String(variant.duration || "-")}s</span>
                <small>{String(variant.path || "")}</small>
              </div>
            ))}
          </div>
        )}
        {postExportNote && <p className="muted">Success note saved locally.</p>}
      </section>

      <section className="wide-panel">
        <h2><ListVideo size={16} /> Production Dashboard</h2>
        <button onClick={onRefreshWorkflowDashboard}><RefreshCw size={15} /> Refresh Dashboard</button>
        {workflowDashboard ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>recent renders <strong>{String(workflowRecentRenders.length)}</strong></span>
              <span>queued <strong>{String(workflowDashboard.queuedRenders ?? 0)}</strong></span>
              <span>running <strong>{String(workflowDashboard.runningRenders ?? 0)}</strong></span>
              <span>success <strong>{Math.round(Number(workflowDashboard.renderSuccessRate || 0) * 100)}%</strong></span>
              <span>cache <strong>{formatBytes(Number(workflowStorage?.cacheBytes || 0))}</strong></span>
              <span>assets <strong>{String(workflowAssetDb?.assetCount ?? 0)}</strong></span>
              <span>duplicates <strong>{String(workflowAssetDb?.duplicateGroupCount ?? 0)}</strong></span>
              <span>project issues <strong>{String(workflowProjectHealth?.issueCount ?? 0)}</strong></span>
            </div>
            <div className="metric-grid">
              <span>metric events <strong>{String(workflowMetrics?.eventCount ?? 0)}</strong></span>
              <span>renders tracked <strong>{String(workflowMetrics?.renderCount ?? 0)}</strong></span>
              <span>avg render <strong>{String(workflowMetrics?.averageRenderSeconds ?? 0)}s</strong></span>
              <span>output <strong>{formatBytes(Number(workflowStorage?.outputBytes || 0))}</strong></span>
            </div>
            {Object.entries(workflowTransitions || {}).slice(0, 3).map(([name, count]) => (
              <div className="inspector-row" key={name}>
                <strong>{name}</strong>
                <span>transition</span>
                <small>{String(count)} uses</small>
              </div>
            ))}
            {workflowRecentRenders.slice(0, 3).map((render) => (
              <div className="inspector-row" key={String(render.path)}>
                <strong>{formatBytes(Number(render.bytes || 0))}</strong>
                <span>{String(render.modifiedAt || "")}</span>
                <small>{String(render.path || "")}</small>
              </div>
            ))}
            {workflowHealth.slice(0, 3).map((warning, index) => (
              <div className="inspector-row" key={`${String(warning)}-${index}`}>
                <strong>workflow</strong>
                <span>review</span>
                <small>{String(warning)}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">Refresh to see recent renders, local queue health, storage/cache usage, project health, and creator workflow metrics.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><Bot size={16} /> Adaptive Workflow Intelligence</h2>
        <p className="muted">Personalized, local-only workflow memory. It learns from successful renders, reviews, rejected scenes, and repeated corrections.</p>
        <div className="review-actions">
          <button onClick={onRefreshAdaptiveMemory}><RefreshCw size={15} /> Refresh Memory</button>
          <button onClick={onApplyAdaptiveDefaults}><Sparkles size={15} /> Apply Smart Defaults</button>
        </div>
        {adaptiveMemory ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>events <strong>{String(adaptiveMemory.events?.length || 0)}</strong></span>
              <span>template <strong>{String(adaptiveDefaults.template || "-")}</strong></span>
              <span>export <strong>{String(adaptiveDefaults.exportPreset || "-")}</strong></span>
              <span>duration <strong>{String(adaptiveDefaults.duration || "-")}s</strong></span>
              <span>pacing <strong>{String(adaptiveFingerprint.pacingIdentity || adaptiveDefaults.pacing || "-")}</strong></span>
              <span>motion <strong>{String(adaptiveFingerprint.motionPhilosophy || "-")}</strong></span>
              <span>friction <strong>{String(adaptiveFriction.failedOperations || 0)} fails</strong></span>
              <span>recovery <strong>{String((adaptiveRecovery.adaptiveRules as string[] | undefined)?.length || 0)} rules</strong></span>
            </div>
            <div className="adaptive-suggestions">
              {adaptiveSuggestions.slice(0, 5).map((suggestion, index) => (
                <span key={String(suggestion.id || index)}>
                  <strong>{String(suggestion.title || "Suggestion")}</strong>
                  {String(suggestion.reason || "")}
                </span>
              ))}
            </div>
            <div className="inspector-row">
              <strong>Creator fingerprint</strong>
              <span>{String(adaptiveFingerprint.cinematicStyle || "clean_cinematic")}</span>
              <small>{String(adaptiveFingerprint.transitionBehavior || "transition behavior pending")} / {String(adaptiveFingerprint.captionBehavior || "caption behavior pending")}</small>
            </div>
            {Array.isArray(adaptiveRecovery.repeatedCorrections) && adaptiveRecovery.repeatedCorrections.slice(0, 4).map((item, index) => {
              const row = item as Record<string, unknown>;
              return (
                <div className="inspector-row" key={`${String(row.label)}-${index}`}>
                  <strong>{String(row.label || "correction")}</strong>
                  <span>adapt future generations</span>
                  <small>{String(row.count || 0)} time(s)</small>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="muted">No adaptive memory loaded yet.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><Clock size={16} /> Friction Log</h2>
        <p className="muted">Local-only signals for slow operations, failed exports, and repeated iteration points. Nothing leaves this machine.</p>
        <button onClick={onRefreshFrictionReport}><RefreshCw size={15} /> Refresh Friction</button>
        {frictionReport ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>events <strong>{String(frictionReport.eventCount)}</strong></span>
              <span>slow ops <strong>{String(frictionReport.slowOperations)}</strong></span>
              <span>failures <strong>{String(frictionReport.failedOperations)}</strong></span>
              <span>settings repeats <strong>{String(frictionReport.repeatedSettings)}</strong></span>
            </div>
            {frictionReport.topLabels.slice(0, 5).map((item) => (
              <div className="inspector-row" key={item.label}>
                <strong>{item.label}</strong>
                <span>repeated</span>
                <small>{item.count} events</small>
              </div>
            ))}
            {frictionReport.recent.slice(0, 4).map((event, index) => (
              <div className="inspector-row" key={`${String(event.createdAt)}-${index}`}>
                <strong>{String(event.event || "event")}</strong>
                <span>{String(event.label || "-")}</span>
                <small>{String(event.createdAt || "")}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No friction report loaded yet.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><Sparkles size={16} /> Quality Feedback Loop</h2>
        <p className="muted">{renderedVideoPath ? `Reviewing ${renderedVideoPath}` : "Render a preview first for video artifact checks; project-only analysis still works."}</p>
        <div className="control-grid">
          <label>
            Profile
            <input value={feedbackProfile} onChange={(event) => setFeedbackProfile(event.target.value)} />
          </label>
          <label>
            Note
            <input value={feedbackNote} onChange={(event) => setFeedbackNote(event.target.value)} placeholder="What worked or failed?" />
          </label>
          {[
            ["pacing", "Pacing"],
            ["readability", "Readability"],
            ["transitions", "Transitions"],
            ["cinematicQuality", "Cinematic"],
            ["hookStrength", "Hook"],
            ["captionQuality", "Captions"],
            ["overallPolish", "Polish"]
          ].map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                type="number"
                min={1}
                max={5}
                value={feedbackRatings[key] || 4}
                onChange={(event) => setFeedbackRatings({ ...feedbackRatings, [key]: Number(event.target.value) })}
              />
            </label>
          ))}
        </div>
        <div className="button-grid compact">
          <button onClick={onFeedbackAnalyze}><CheckCircle2 size={15} /> Self-Analyze</button>
          <button onClick={() => onFeedbackReview(feedbackProfile, feedbackRatings, feedbackNote)}><Save size={15} /> Save Review</button>
          <button onClick={() => onFeedbackLearn(feedbackProfile)}><Wand2 size={15} /> Learn Identity</button>
        </div>
        {feedbackAnalysis ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>pacing <strong>{String(feedbackPacing?.score ?? "-")}</strong></span>
              <span>motion <strong>{String(feedbackAnalysis.motionIntensityScore ?? "-")}</strong></span>
              <span>caption wps <strong>{String(feedbackCaptions?.wordsPerSecond ?? "-")}</strong></span>
              <span>warnings <strong>{String(feedbackWarnings.length)}</strong></span>
            </div>
            {feedbackRecommendations.slice(0, 3).map((item, index) => (
              <div className="inspector-row" key={`${String(item)}-${index}`}>
                <strong>suggestion</strong>
                <span>feedback</span>
                <small>{String(item)}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No feedback analysis yet.</p>
        )}
        {feedbackReview && (
          <div className="metric-grid">
            <span>review <strong>{String(feedbackReview.verdict || "-")}</strong></span>
            <span>average <strong>{String(feedbackReview.averageRating || "-")}</strong></span>
          </div>
        )}
        {creatorIdentity && (
          <div className="metric-grid">
            <span>samples <strong>{String(creatorIdentity.sampleCount ?? 0)}</strong></span>
            <span>pacing <strong>{String(identityModel?.pacingStyle || "-")}</strong></span>
            <span>motion <strong>{String(identityModel?.motionAggressiveness || "-")}</strong></span>
            <span>captions <strong>{String(identityModel?.captionDensity || "-")}</strong></span>
          </div>
        )}
      </section>

      <section className="wide-panel">
        <h2><CheckCircle2 size={16} /> Long-Term Evolution</h2>
        <p className="muted">A local quality gate for architecture, project intelligence, creator identity, workflow speed, and controlled expansion.</p>
        <button onClick={() => onEvolutionReport(feedbackProfile)}><RefreshCw size={15} /> Refresh Evolution Report</button>
        {evolutionReport ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>readiness <strong>{String(evolutionReport.readinessScore ?? "-")}</strong></span>
              <span>local <strong>{String(Boolean(evolutionReport.localFirst))}</strong></span>
              <span>docs <strong>{String(evolutionAudit?.docCount ?? "-")}</strong></span>
              <span>architecture warnings <strong>{String(evolutionAudit?.warningCount ?? 0)}</strong></span>
              <span>project available <strong>{String(Boolean(evolutionProject?.available))}</strong></span>
              <span>next actions <strong>{String(evolutionNextActions.length)}</strong></span>
            </div>
            {evolutionNextActions.slice(0, 4).map((item, index) => (
              <div className="inspector-row" key={`${String(item)}-${index}`}>
                <strong>next</strong>
                <span>evolution</span>
                <small>{String(item)}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">Run the report before large changes to keep the product stable, explainable, and local-first.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><Image size={16} /> Brand Kit</h2>
        <div className="button-grid compact">
          <button onClick={onCreateBrandKit}><Plus size={15} /> New Kit</button>
          <button onClick={onApplyBrandKit}><Wand2 size={15} /> Apply Kit</button>
        </div>
      </section>

      <section className="wide-panel">
        <h2><LayoutTemplate size={16} /> Offline Template Packs</h2>
        <div className="toolbar">
          <button onClick={onInstallTemplate}><FolderOpen size={15} /> Install Pack</button>
        </div>
        <div className="template-pack-list">
          {templatePacks.map((template) => (
            <div className="template-pack-row" key={template.key}>
              <strong>{template.name}</strong>
              <span>{template.author} | {template.version} | {String(template.exportPreset || "")}</span>
              <small>{template.tags.join(", ")} | {Object.keys(template.requiredAssets || {}).length} assets</small>
              <button onClick={() => onExportTemplate(template.key)}>Export</button>
            </div>
          ))}
        </div>
      </section>

      <section className="wide-panel">
        <h2><RefreshCw size={16} /> Crash Recovery</h2>
        <div className="toolbar">
          <button onClick={onAutosaveNow}><Save size={15} /> Autosave</button>
          <button onClick={onRefreshRecovery}><RefreshCw size={15} /> Refresh</button>
        </div>
        <div className="list">
          {recoveryPoints.length === 0 && <span className="muted">No recovery points listed.</span>}
          {recoveryPoints.map((point) => (
            <div className="history-row" key={point.path}>
              <strong>{point.type}</strong>
              <span>{point.timestamp || point.path}</span>
              <button onClick={() => onRestoreRecovery(point.path)}>Restore</button>
            </div>
          ))}
        </div>
      </section>

      <section className="wide-panel">
        <h2><CheckCircle2 size={16} /> Local Hardening</h2>
        <div className="button-grid compact">
          <button onClick={onRefreshHardening}><RefreshCw size={15} /> Refresh Status</button>
          <button onClick={onOpenDocs}><FolderOpen size={15} /> Local Docs</button>
        </div>
        {hardeningStatus ? (
          <div className="inspector-list compact-list">
            <div className="metric-grid">
              <span>FFmpeg <strong>{String(Boolean(ffmpeg?.installed))}</strong></span>
              <span>GPU encode <strong>{String(Boolean(ffmpeg?.supportsGpuEncoding))}</strong></span>
              <span>ready <strong>{String(Boolean(readiness?.ready))}</strong></span>
              <span>Ollama <strong>{String(ollama?.health || "unknown")}</strong></span>
              <span>Whisper <strong>{String(Boolean(whisper?.available))}</strong></span>
              <span>telemetry <strong>{String(Boolean(privacyFlags?.telemetry))}</strong></span>
              <span>renders <strong>{String(renderPerf?.renderCount ?? 0)}</strong></span>
              <span>cache <strong>{formatBytes(Number(cachePerf?.totalBytes || 0))}</strong></span>
            </div>
            <p className="muted">Docs: {hardeningStatus.docsPath || "bundled docs folder"}</p>
            {readinessWarnings.slice(0, 4).map((warning) => (
              <div className="inspector-row" key={String(warning)}>
                <strong>warning</strong>
                <span>dependency</span>
                <small>{String(warning)}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">Run a local status check to verify FFmpeg, models, privacy settings, cache size, and render readiness.</p>
        )}
      </section>

      <section className="wide-panel">
        <h2><Wand2 size={16} /> App Settings</h2>
        <div className="control-grid">
          <label>
            Theme
            <select value={draftSettings.theme} onChange={(event) => setDraftSettings({ ...draftSettings, theme: event.target.value as AppSettings["theme"] })}>
              <option value="graphite">graphite</option>
              <option value="midnight">midnight</option>
              <option value="light">light</option>
            </select>
          </label>
          <label>
            Autosave Seconds
            <input
              type="number"
              min={10}
              value={draftSettings.autosaveIntervalSeconds}
              onChange={(event) => setDraftSettings({ ...draftSettings, autosaveIntervalSeconds: Number(event.target.value) })}
            />
          </label>
        </div>
        <div className="toggles">
          <label><input type="checkbox" checked={draftSettings.autosave} onChange={(event) => setDraftSettings({ ...draftSettings, autosave: event.target.checked })} /> autosave</label>
          <label><input type="checkbox" checked={draftSettings.keyboardShortcuts} onChange={(event) => setDraftSettings({ ...draftSettings, keyboardShortcuts: event.target.checked })} /> shortcuts</label>
        </div>
        <button onClick={() => onSaveSettings(draftSettings)}><Save size={15} /> Save Settings</button>
      </section>
    </div>
  );
}

function formatResolution(value: unknown) {
  if (!value || typeof value !== "object") return "-";
  const item = value as { width?: unknown; height?: unknown };
  return `${String(item.width ?? "?")}x${String(item.height ?? "?")}`;
}

function collaborationSceneCards(project: ProjectData | null, review: GenerationReviewState | null) {
  const reviewScenes = new Map((review?.scenes || []).map((scene) => [scene.key, scene]));
  return (project?.timeline || []).map((scene, index) => {
    const textLayers = scene.layers?.filter((layer) => layer.type === "text" || layer.type === "caption" || layer.type === "captions" || layer.type === "lower_third") || [];
    const mediaLayer = scene.layers?.find((layer) => layer.type === "video" || layer.type === "image");
    const caption = sceneCaptionText(scene) || reviewScenes.get(scene.id)?.caption || "";
    const transition = String(scene.transitionOut?.type || (index === (project?.timeline || []).length - 1 ? "outro" : "cut"));
    const warnings = [];
    if (caption.length > 96) warnings.push("possible readability issue");
    if (scene.duration < 1.2 && caption.length > 36) warnings.push("caption may be too fast");
    if (!mediaLayer && textLayers.length === 0) warnings.push("empty scene");
    if (transition === "cut" && scene.duration > 5) warnings.push("could use smoother transition");
    const confidence = Math.max(35, Math.min(96, 88 - warnings.length * 14 - (scene.reviewStatus === "needs_review" ? 12 : 0) + (scene.reviewStatus === "approved" ? 7 : 0)));
    return {
      id: scene.id,
      label: reviewScenes.get(scene.id)?.label || scene.id,
      caption,
      transition,
      clip: mediaLayer?.asset ? String(mediaLayer.asset) : "",
      pacing: scene.duration < 2 ? "fast" : scene.duration > 5 ? "slow" : "balanced",
      status: scene.reviewStatus || "draft",
      warnings,
      confidence,
      confidenceLabel: confidence >= 78 ? "strong" : confidence >= 58 ? "needs review" : "low confidence"
    };
  });
}

function collaborationSuggestions(project: ProjectData | null, review: GenerationReviewState | null, processing: ProcessingState) {
  const scenes = project?.timeline || [];
  const suggestions: Array<{ label: string; reason: string; command: string }> = [];
  const first = scenes[0];
  const captions = scenes.map(sceneCaptionText).filter(Boolean);
  const transitionCounts = new Map<string, number>();
  for (const scene of scenes) {
    const type = String(scene.transitionOut?.type || "cut");
    transitionCounts.set(type, (transitionCounts.get(type) || 0) + 1);
  }
  const repeatedTransition = [...transitionCounts.entries()].find(([, count]) => scenes.length > 3 && count >= Math.max(3, scenes.length - 1));
  if (first && first.duration > 3.2) suggestions.push({ label: "Shorter hook", reason: "Intro may be too slow.", command: "make the hook shorter and faster" });
  if (captions.some((caption) => caption.length > 96)) suggestions.push({ label: "Readable captions", reason: "Long caption detected.", command: "slow down the captions and improve readability" });
  if (repeatedTransition) suggestions.push({ label: "Smoother transitions", reason: `${repeatedTransition[0]} repeats often.`, command: "add smoother varied transitions" });
  if (!project?.stylePreset && !project?.metadata?.stylePreset) suggestions.push({ label: "Cinematic style", reason: "No strong style metadata yet.", command: "make this feel more cinematic" });
  if (processing.currentStage.toLowerCase().includes("render")) suggestions.push({ label: "Preview current scene", reason: "Render is active.", command: "keep the current scene locked and reduce excessive motion" });
  if (review && !review.readyForFinalRender) suggestions.push({ label: "Needs approval", reason: `${review.unresolved.length} section(s) open.`, command: "mark weak sections for review and keep strong pacing" });
  return suggestions.slice(0, 5);
}

function sceneCaptionText(scene: SceneData) {
  const captionLayer = scene.layers?.find((layer) => layer.type === "caption" || layer.type === "captions");
  const items = Array.isArray(captionLayer?.items) ? captionLayer.items as Array<Record<string, unknown>> : [];
  if (items[0]?.text) return String(items[0].text);
  const textLayer = scene.layers?.find((layer) => layer.type === "text" || layer.type === "lower_third");
  return String(textLayer?.text || "");
}

function beginnerFormFromQuickCreate(current: BeginnerFormState, quickCreate: QuickCreateState): BeginnerFormState {
  const platform = quickCreate.platform || "shorts";
  const style = quickCreate.style || "cinematic";
  const template = quickTemplateFor(platform, style);
  const defaults = templateQuickDefaults(template, platform);
  const styleLabel = style.charAt(0).toUpperCase() + style.slice(1);
  const platformLabel = platform === "youtube" ? "Normal Video" : platform === "instagram_reels" ? "Reel" : platform === "tiktok" ? "TikTok" : "YouTube Short";
  const prompt = quickCreate.prompt.trim() || `Make this into a ${platformLabel}.`;
  return {
    ...current,
    mediaFile: quickCreate.mediaFile || current.mediaFile,
    productName: "Uploaded Video",
    goal: prompt,
    keyFeatures: "",
    template,
    targetPlatform: platform,
    vibe: `${style} ${defaults.vibe}`.trim(),
    duration: parseDurationFromPrompt(prompt) || defaults.duration,
    quickPrompt: `${prompt} Use a ${styleLabel} style, readable captions, clean cuts, title cards, and a polished ending.`
  };
}

function quickTemplateFor(platform: string, style: string) {
  const lowerStyle = style.toLowerCase();
  if (lowerStyle === "gaming") return "gaming_montage";
  if (lowerStyle === "podcast") return "tutorial_walkthrough";
  if (lowerStyle === "educational") return "tutorial_walkthrough";
  if (lowerStyle === "hype") return "youtube_short";
  if (lowerStyle === "clean") return platform === "youtube" ? "minimal_saas_promo" : "youtube_short";
  if (platform === "tiktok" || platform === "instagram_reels") return "tiktok_reels_edit";
  return platform === "youtube" ? "premium_product_showcase" : "youtube_short";
}

function captionStyleDescription(style: string) {
  const descriptions: Record<string, string> = {
    "TikTok Bold": "Large, high-contrast captions for vertical short-form edits.",
    "Clean Lower Third": "Smaller professional captions placed away from important UI.",
    "Podcast Subtitles": "Comfortable multi-line subtitles for spoken content.",
    "Educational Clear": "Readable timing and restrained animation for tutorials.",
    "Cinematic Title": "Premium title-card style captions with slower emphasis.",
    "Gaming Hype": "Fast, punchy captions with stronger emphasis words.",
    "Clean subtitles": "Readable white subtitles with outline and safe lower placement.",
    "TikTok word highlight": "Large vertical captions with word-by-word highlight metadata.",
    "Gaming bold captions": "High-contrast bold captions with stronger outline.",
    "Podcast lower-third": "Lower-third captions designed for spoken clips.",
    "Educational captions": "Clear instructional captions with calmer timing.",
    "Minimal cinematic captions": "Small premium captions with restrained motion."
  };
  return descriptions[style] || "Caption style preset";
}

function buildAiStudioPrompt(prompt: string, tasks: string[]) {
  const cleanPrompt = prompt.trim() || "Create a polished short-form edit from the current project.";
  if (!tasks.length) return cleanPrompt;
  return `${cleanPrompt}\n\nRequested AI tasks: ${tasks.join(", ")}.\nCreate a reviewable edit plan first. Do not directly modify the timeline until the plan is approved.`;
}

function aiStyleDescription(style: string) {
  const descriptions: Record<string, string> = {
    Clean: "Polished edits with restrained motion and readable text.",
    Gaming: "Fast cuts, bold captions, zoom hits, and energetic pacing.",
    Cinematic: "Smooth reveals, premium titles, slower tension, and tasteful motion.",
    Educational: "Clear sequence, slower captions, and minimal distractions.",
    Podcast: "Lower-thirds, stable pacing, and speech-first captions.",
    Hype: "Aggressive hook, quick cuts, music hits, and punchy effects.",
    Minimal: "Quiet composition, subtle transitions, and low visual clutter.",
    Meme: "Reaction timing, punchy captions, and comedic cut emphasis."
  };
  return descriptions[style] || "AI style preset";
}

function collectCaptionEntries(project: ProjectData): CaptionWorkflowEntry[] {
  const entries: CaptionWorkflowEntry[] = [];
  for (const [sceneIndex, scene] of (project.timeline || []).entries()) {
    for (const [layerIndex, layer] of (scene.layers || []).entries()) {
      if (!isTextLikeLayer(layer.type)) continue;
      const layerStart = Number(layer.start || 0);
      const items = Array.isArray(layer.items) ? layer.items as Array<Record<string, unknown>> : [];
      if (items.length && (layer.type === "caption" || layer.type === "captions")) {
        for (const [itemIndex, item] of items.entries()) {
          const localStart = Number(item.start ?? 0);
          const duration = Math.max(0.25, Number(item.duration ?? layer.duration ?? scene.duration ?? 1));
          entries.push({
            id: `${sceneIndex}:${layerIndex}:${itemIndex}`,
            sceneId: scene.id,
            sceneIndex,
            layerIndex,
            itemIndex,
            type: layer.type,
            text: String(item.text || ""),
            localStart,
            absoluteStart: Number(scene.start || 0) + layerStart + localStart,
            duration,
            layer: { ...layer, ...item }
          });
        }
      } else {
        const duration = Math.max(0.25, Number(layer.duration ?? scene.duration ?? 1));
        entries.push({
          id: `${sceneIndex}:${layerIndex}:layer`,
          sceneId: scene.id,
          sceneIndex,
          layerIndex,
          itemIndex: null,
          type: layer.type,
          text: String(layer.text || ""),
          localStart: layerStart,
          absoluteStart: Number(scene.start || 0) + layerStart,
          duration,
          layer
        });
      }
    }
  }
  return entries.sort((a, b) => a.absoluteStart - b.absoluteStart);
}

function updateCaptionEntry(project: ProjectData, entry: CaptionWorkflowEntry, patch: Record<string, unknown>): ProjectData {
  const next = structuredClone(project);
  const scene = next.timeline?.[entry.sceneIndex];
  const layer = scene?.layers?.[entry.layerIndex];
  if (!scene || !layer) return project;
  if (entry.itemIndex !== null && Array.isArray(layer.items)) {
    const item = (layer.items as Array<Record<string, unknown>>)[entry.itemIndex];
    if (!item) return project;
    const itemPatch = { ...patch };
    for (const key of ["fontFamily", "font", "fontSize", "color", "strokeWidth", "shadow", "box", "y", "animation", "wordHighlight", "highlightWords"]) {
      if (key in itemPatch) {
        (layer as Record<string, unknown>)[key] = itemPatch[key];
        delete itemPatch[key];
      }
    }
    Object.assign(item, itemPatch);
  } else {
    Object.assign(layer, patch);
  }
  next.metadata = {
    ...(next.metadata || {}),
    captionsWorkflow: {
      updatedAt: new Date().toISOString(),
      lastAction: "caption_edit"
    }
  };
  return next;
}

function splitCaptionEntry(project: ProjectData, entry: CaptionWorkflowEntry): ProjectData {
  const next = structuredClone(project);
  const scene = next.timeline?.[entry.sceneIndex];
  const layer = scene?.layers?.[entry.layerIndex];
  if (!scene || !layer) return project;
  const words = entry.text.trim().split(/\s+/).filter(Boolean);
  if (words.length < 2) return project;
  const firstText = words.slice(0, Math.ceil(words.length / 2)).join(" ");
  const secondText = words.slice(Math.ceil(words.length / 2)).join(" ");
  const firstDuration = Math.max(0.25, Number((entry.duration / 2).toFixed(3)));
  const secondDuration = Math.max(0.25, Number((entry.duration - firstDuration).toFixed(3)));
  if (entry.itemIndex !== null && Array.isArray(layer.items)) {
    const items = layer.items as Array<Record<string, unknown>>;
    items.splice(entry.itemIndex, 1,
      { ...items[entry.itemIndex], text: firstText, duration: firstDuration },
      { ...items[entry.itemIndex], text: secondText, start: Number((entry.localStart + firstDuration).toFixed(3)), duration: secondDuration }
    );
  } else {
    layer.text = `${firstText}\n${secondText}`;
  }
  return next;
}

function mergeCaptionEntry(project: ProjectData, entry: CaptionWorkflowEntry): ProjectData {
  if (entry.itemIndex === null) return project;
  const next = structuredClone(project);
  const layer = next.timeline?.[entry.sceneIndex]?.layers?.[entry.layerIndex];
  if (!layer || !Array.isArray(layer.items)) return project;
  const items = layer.items as Array<Record<string, unknown>>;
  const current = items[entry.itemIndex];
  const nextItem = items[entry.itemIndex + 1];
  if (!current || !nextItem) return project;
  current.text = `${String(current.text || "")} ${String(nextItem.text || "")}`.trim();
  current.duration = Number(((Number(nextItem.start ?? entry.localStart) - entry.localStart) + Number(nextItem.duration ?? 0)).toFixed(3));
  items.splice(entry.itemIndex + 1, 1);
  return next;
}

function shiftAllCaptions(project: ProjectData, delta: number): ProjectData {
  const next = structuredClone(project);
  for (const caption of next.captions || []) {
    caption.start = Math.max(0, Number((Number(caption.start || 0) + delta).toFixed(3)));
  }
  for (const scene of next.timeline || []) {
    for (const layer of scene.layers || []) {
      if (!isTextLikeLayer(layer.type)) continue;
      if (Array.isArray(layer.items)) {
        for (const item of layer.items as Array<Record<string, unknown>>) {
          item.start = Math.max(0, Number((Number(item.start || 0) + delta).toFixed(3)));
        }
      } else {
        layer.start = Math.max(0, Number((Number(layer.start || 0) + delta).toFixed(3)));
      }
    }
  }
  return next;
}

function autoFixCaptionTiming(project: ProjectData): ProjectData {
  const next = structuredClone(project);
  for (const scene of next.timeline || []) {
    for (const layer of scene.layers || []) {
      if (!isTextLikeLayer(layer.type)) continue;
      layer.fontSize = Math.max(Number(layer.fontSize || 0), Number(next.project?.height || 1080) >= 1600 ? 58 : 42);
      layer.y = layer.y || "bottom";
      layer.strokeWidth = Math.max(Number(layer.strokeWidth || 0), 2);
      layer.box = layer.box ?? true;
      const sceneDuration = Number(scene.duration || 1);
      if (Array.isArray(layer.items)) {
        for (const item of layer.items as Array<Record<string, unknown>>) {
          const start = Math.max(0, Number(item.start || 0));
          item.start = Number(start.toFixed(3));
          item.duration = Math.min(Math.max(Number(item.duration || 1.4), 1.2), Math.max(0.25, sceneDuration - start));
        }
      } else {
        const start = Math.max(0, Number(layer.start || 0));
        layer.start = Number(start.toFixed(3));
        layer.duration = Math.min(Math.max(Number(layer.duration || Math.min(sceneDuration, 2.4)), 1.2), Math.max(0.25, sceneDuration - start));
      }
    }
  }
  return next;
}

function applyCaptionStylePreset(project: ProjectData, style: string): ProjectData {
  const next = structuredClone(project);
  const lower = style.toLowerCase();
  for (const scene of next.timeline || []) {
    for (const layer of scene.layers || []) {
      if (!isTextLikeLayer(layer.type)) continue;
      layer.type = layer.type === "text" ? layer.type : "caption";
      layer.color = "#ffffff";
      layer.strokeColor = "#000000";
      layer.strokeWidth = /minimal/.test(lower) ? 1 : /gaming|tiktok/.test(lower) ? 4 : 2;
      layer.shadow = /minimal/.test(lower) ? "none" : "soft";
      layer.box = /podcast|educational|clean|minimal/.test(lower);
      layer.boxColor = /minimal/.test(lower) ? "#00000066" : "#00000099";
      layer.fontSize = /tiktok|gaming/.test(lower) ? 68 : /podcast|educational/.test(lower) ? 48 : /minimal/.test(lower) ? 40 : 54;
      layer.y = /podcast/.test(lower) ? "lower_third" : /minimal/.test(lower) ? "bottom" : layer.y || "bottom";
      layer.animation = { ...((layer.animation as Record<string, unknown>) || {}), in: /tiktok|gaming/.test(lower) ? "pop" : /minimal/.test(lower) ? "fade" : "slideUp" };
      layer.wordHighlight = /word|tiktok|gaming/.test(lower);
      layer.highlightWords = /word|tiktok|gaming/.test(lower);
      layer.captionStyle = style;
    }
  }
  next.metadata = { ...(next.metadata || {}), captionStylePreset: style };
  return next;
}

function captionsToSrt(entries: CaptionWorkflowEntry[]) {
  return entries.map((entry, index) => [
    String(index + 1),
    `${srtTime(entry.absoluteStart)} --> ${srtTime(entry.absoluteStart + entry.duration)}`,
    entry.text,
    ""
  ].join("\n")).join("\n");
}

function captionsToVtt(entries: CaptionWorkflowEntry[]) {
  return `WEBVTT\n\n${entries.map((entry) => [
    `${vttTime(entry.absoluteStart)} --> ${vttTime(entry.absoluteStart + entry.duration)}`,
    entry.text,
    ""
  ].join("\n")).join("\n")}`;
}

function srtTime(seconds: number) {
  const value = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const wholeSeconds = Math.floor(value % 60);
  const ms = Math.floor((value - Math.floor(value)) * 1000);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(wholeSeconds).padStart(2, "0")},${String(ms).padStart(3, "0")}`;
}

function vttTime(seconds: number) {
  return srtTime(seconds).replace(",", ".");
}

function downloadTextFile(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function normalizeColorInput(value: unknown, fallback: string) {
  const text = String(value || "").trim();
  return /^#[0-9a-f]{6}$/i.test(text) ? text : fallback;
}

function applyAssistantInstruction(project: ProjectData, instruction: string): { project: ProjectData; summary: string } {
  const lower = instruction.toLowerCase();
  let next = structuredClone(project);
  const summaries: string[] = [];
  next.metadata = {
    ...(next.metadata || {}),
    interactiveCollaboration: {
      lastInstruction: instruction,
      updatedAt: new Date().toISOString(),
      localOnly: true
    }
  };
  if (lower.includes("darker") || lower.includes("dark") || lower.includes("cyber") || lower.includes("cinematic")) {
    next.stylePreset = lower.includes("cyber") ? "red_black_aegis" : "clean_cinematic";
    next.timeline = (next.timeline || []).map((scene) => ({
      ...scene,
      postProcessing: {
        ...((scene.postProcessing as Record<string, unknown>) || {}),
        vignette: lower.includes("minimal") ? 0.18 : 0.38,
        glow: lower.includes("cyber") ? 0.42 : 0.24,
        contrast: 1.08,
        brightness: -0.035
      }
    }));
    summaries.push("Applied darker cinematic grading metadata.");
  }
  if (lower.includes("slow") && lower.includes("caption")) {
    next.timeline = (next.timeline || []).map((scene) => sceneCaptionText(scene)
      ? { ...scene, duration: Number((Number(scene.duration || 0) * 1.12).toFixed(3)) }
      : scene);
    next.project = { ...next.project, duration: totalTimelineDuration(next) };
    summaries.push("Extended caption scenes for readability.");
  }
  if (lower.includes("zoom")) {
    next.timeline = (next.timeline || []).map((scene) => ({
      ...scene,
      layers: (scene.layers || []).map((layer) => (layer.type === "video" || layer.type === "image")
        ? { ...layer, scale: Math.min(1.35, Number(layer.scale || 1) + 0.08), animation: { ...((layer.animation as Record<string, unknown>) || {}), in: "zoomIn", duration: 0.5 } }
        : layer)
    }));
    summaries.push("Increased media zoom and added zoom-in animation metadata.");
  }
  if (lower.includes("remove excessive motion") || lower.includes("less motion") || lower.includes("reduce motion")) {
    next.timeline = (next.timeline || []).map((scene) => ({
      ...scene,
      transitionOut: { ...(scene.transitionOut || {}), type: "crossfade", duration: 0.35 },
      layers: (scene.layers || []).map((layer) => (layer.type === "video" || layer.type === "image")
        ? { ...layer, scale: Math.max(1, Number(layer.scale || 1) - 0.08), animation: { ...((layer.animation as Record<string, unknown>) || {}), in: "fade", duration: 0.35 } }
        : layer)
    }));
    summaries.push("Reduced motion intensity and normalized transitions.");
  }
  if (lower.includes("faster") || lower.includes("shorter hook")) {
    const first = next.timeline?.[0];
    if (first) {
      first.duration = Math.max(1.2, Number((Number(first.duration || 0) * 0.72).toFixed(3)));
      for (let index = 1; index < (next.timeline || []).length; index += 1) {
        next.timeline![index].start = Number((Number(next.timeline![index - 1].start || 0) + Number(next.timeline![index - 1].duration || 0)).toFixed(3));
      }
      next.project = { ...next.project, duration: totalTimelineDuration(next) };
      summaries.push("Shortened the hook and rippled following scene starts.");
    }
  }
  if (lower.includes("transition")) {
    next.timeline = (next.timeline || []).map((scene, index) => index < (next.timeline || []).length - 1
      ? { ...scene, transitionOut: { type: index % 2 === 0 ? "crossfade" : "slide", duration: 0.35 } }
      : scene);
    summaries.push("Varied transition choices for smoother flow.");
  }
  if (!summaries.length) {
    next = setSceneReviewStatus(next, next.timeline?.[0]?.id || "", "needs_review");
    summaries.push("Marked the opening scene for review so you can steer the next edit safely.");
  }
  return { project: next, summary: summaries.join(" ") };
}

function safePercent(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

function updateTaskRecord(task: ManagedTask, patch: Partial<ManagedTask>): ManagedTask {
  const cleanPatch = Object.fromEntries(Object.entries(patch).filter(([, value]) => value !== undefined)) as Partial<ManagedTask>;
  return {
    ...task,
    ...cleanPatch,
    progress: Math.max(task.progress, Number(patch.progress ?? task.progress)),
    updatedAt: Date.now()
  };
}

function inferTaskKind(label: string, stage = ""): ManagedTaskKind {
  const lower = `${label} ${stage}`.toLowerCase();
  if (/render|export|package|re-export/.test(lower)) return "render_export";
  if (/caption/.test(lower)) return "caption_generation";
  if (/transcript|transcription|voice/.test(lower)) return "audio_transcription";
  if (/thumbnail|storyboard/.test(lower)) return "thumbnail_generation";
  if (/import|replace media|asset/.test(lower)) return "media_import";
  if (/proxy|cache|preview/.test(lower)) return "proxy_generation";
  if (/url|download/.test(lower)) return "url_download";
  if (/preflight|quality|diagnostic|health|system check/.test(lower)) return "diagnostics";
  if (/save|open|project|autosave|version|recovery/.test(lower)) return "project_io";
  return "ai_analysis";
}

function taskKindLabel(kind: ManagedTaskKind) {
  const labels: Record<ManagedTaskKind, string> = {
    ai_analysis: "AI analysis",
    caption_generation: "Captions",
    audio_transcription: "Transcription",
    render_export: "Render/export",
    thumbnail_generation: "Thumbnails",
    media_import: "Media import",
    proxy_generation: "Proxy/preview",
    url_download: "URL download",
    project_io: "Project I/O",
    diagnostics: "Diagnostics"
  };
  return labels[kind];
}

function taskStatusLabel(status: ManagedTaskStatus) {
  if (status === "warning") return "needs attention";
  return status;
}

function hardeningStatusHasUpdate(statusReport: HardeningStatus | null | undefined) {
  if (!statusReport) return false;
  const direct = [
    statusReport.dependency,
    statusReport.model,
    statusReport.privacy,
    statusReport.performance,
    statusReport
  ].some((section) => Boolean(section && typeof section === "object" && (
    (section as Record<string, unknown>).updateAvailable === true ||
    (section as Record<string, unknown>).updatesAvailable === true ||
    (section as Record<string, unknown>).newVersionAvailable === true
  )));
  if (direct) return true;
  const text = JSON.stringify(statusReport).toLowerCase();
  return /update available|new version available|upgrade available/.test(text);
}

function buildManagedTasks(
  localTasks: ManagedTask[],
  renderQueueItems: RenderQueueItem[],
  processing: ProcessingState,
  systemMetrics: SystemMetrics | null
): ManagedTask[] {
  const now = Date.now();
  const renderTasks: ManagedTask[] = renderQueueItems.map((job) => {
    const status = job.status === "running"
      ? "running"
      : job.status === "queued"
        ? "queued"
        : job.status === "completed"
          ? "completed"
          : job.status === "canceled"
            ? "canceled"
            : "failed";
    return {
      id: `render-${job.runId}`,
      runId: job.runId,
      kind: "render_export",
      label: job.label,
      stage: job.status === "queued" ? "Waiting in render queue" : job.currentScene ? `Rendering ${job.currentScene}` : job.status === "completed" ? "Complete" : job.status === "failed" ? "Failed" : "Rendering",
      status,
      progress: safePercent(Number(job.progressPercent || 0)),
      etaSeconds: job.estimatedRemainingSeconds,
      currentAsset: job.outputPath,
      currentScene: job.currentScene,
      cpuPercent: systemMetrics?.cpuPercent,
      gpuPercent: systemMetrics?.gpuPercent,
      warnings: job.packageError ? [job.packageError] : [],
      errors: job.status === "failed" ? [`Render exited with code ${job.exitCode ?? "unknown"}`] : [],
      canPause: job.status === "running" || job.status === "queued",
      canResume: job.status === "queued",
      canCancel: job.status === "running" || job.status === "queued",
      detail: job.packagePath || job.outputPath,
      startedAt: now - 1,
      updatedAt: now,
      completedAt: job.status === "completed" || job.status === "failed" || job.status === "canceled" ? now : undefined
    };
  });
  const activeLocalIds = new Set(renderTasks.map((task) => task.id));
  const local = localTasks
    .filter((task) => !activeLocalIds.has(task.id))
    .map((task) => ({
      ...task,
      cpuPercent: task.status === "running" ? systemMetrics?.cpuPercent : task.cpuPercent,
      gpuPercent: task.status === "running" ? systemMetrics?.gpuPercent : task.gpuPercent
    }));
  if (!renderTasks.length && processing.isActive && !local.some((task) => task.status === "running")) {
    local.unshift({
      id: "processing-current",
      kind: inferTaskKind(processing.activeTask, processing.currentStage),
      label: processing.activeTask,
      stage: processing.currentStage,
      status: "running",
      progress: processing.progress,
      etaSeconds: processing.etaSeconds,
      currentAsset: processing.currentAsset,
      currentScene: processing.currentScene,
      cpuPercent: systemMetrics?.cpuPercent,
      gpuPercent: systemMetrics?.gpuPercent,
      canPause: false,
      canResume: false,
      canCancel: false,
      startedAt: processing.startedAt || now,
      updatedAt: now
    });
  }
  return [...renderTasks, ...local]
    .sort((a, b) => taskSortRank(a.status) - taskSortRank(b.status) || b.updatedAt - a.updatedAt)
    .slice(0, 80);
}

function taskSortRank(status: ManagedTaskStatus) {
  const rank: Record<ManagedTaskStatus, number> = {
    running: 0,
    queued: 1,
    paused: 2,
    warning: 3,
    failed: 4,
    canceled: 5,
    completed: 6
  };
  return rank[status];
}

function activeRenderJob(renderQueueItems: RenderQueueItem[]) {
  return renderQueueItems.find((job) => job.status === "running") ||
    renderQueueItems.find((job) => job.status === "queued") ||
    renderQueueItems.find((job) => job.status === "failed") ||
    null;
}

function formatPercent(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `${Math.max(0, value).toFixed(value >= 10 ? 0 : 1)}%`;
}

function formatMemory(metrics: SystemMetrics | null) {
  if (!metrics || !metrics.memoryTotalMb) return "-";
  return `${Math.round(metrics.memoryUsedMb)} / ${Math.round(metrics.memoryTotalMb)} MB`;
}

function latestRenderIssues(logs: string[], activityFeed: ProcessingActivity[]): ProcessingActivity[] {
  const logIssues = logs
    .slice(-80)
    .filter((line) => /error|warning|failed|traceback|exception/i.test(line))
    .slice(-8)
    .reverse()
    .map((line, index) => ({
      id: `log-${index}-${line.slice(0, 18)}`,
      time: "",
      label: line.length > 160 ? `${line.slice(0, 157)}...` : line,
      detail: "render log",
      kind: /error|failed|traceback|exception/i.test(line) ? "error" as ActivityKind : "warning" as ActivityKind
    }));
  const activityIssues = activityFeed.filter((item) => item.kind === "error" || item.kind === "warning").slice(0, 8);
  return [...activityIssues, ...logIssues].slice(0, 10);
}

function mergeProcessingWorkers(workers: ProcessingWorker[], activeJob: RenderQueueItem | null): ProcessingWorker[] {
  const rows = [...workers];
  if (activeJob) {
    rows.unshift({
      name: "Render worker",
      status: activeJob.status === "running" ? "running" : activeJob.status === "queued" ? "queued" : activeJob.status === "completed" ? "complete" : "blocked",
      progress: Number(activeJob.progressPercent || 0)
    });
    rows.push({
      name: "Encoder",
      status: activeJob.currentScene === "export" ? "running" : activeJob.status === "completed" ? "complete" : "queued",
      progress: activeJob.currentScene === "export" ? Number(activeJob.progressPercent || 0) : undefined
    });
    if (activeJob.packageStatus) {
      rows.push({
        name: "Upload package",
        status: activeJob.packageStatus === "completed" ? "complete" : activeJob.packageStatus === "running" ? "running" : activeJob.packageStatus === "failed" ? "blocked" : "queued"
      });
    }
  }
  const unique = new Map<string, ProcessingWorker>();
  for (const worker of rows) unique.set(worker.name, worker);
  return [...unique.values()].slice(0, 8);
}

function splitReasoning(value: string) {
  return value
    .split(/\r?\n|(?<=\.)\s+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 12)
    .slice(0, 8);
}

function activityGlyph(kind: ActivityKind) {
  if (kind === "success") return "OK";
  if (kind === "warning") return "!";
  if (kind === "error") return "ERR";
  return "AI";
}

function stageForAction(label: string) {
  const lower = label.toLowerCase();
  if (lower.includes("preview")) return "Rendering preview frames";
  if (lower.includes("preflight") || lower.includes("quality")) return "Checking export readiness";
  if (lower.includes("repurpose") || lower.includes("reformat")) return "Building platform variants";
  if (lower.includes("package")) return "Preparing upload package";
  if (lower.includes("feedback")) return "Analyzing finished edit";
  if (lower.includes("dashboard")) return "Reading local workflow metrics";
  if (lower.includes("beginner")) return "Creating automatic video plan";
  return "Processing";
}

function stageForRegeneration(regenerate: string) {
  if (regenerate === "hook") return "Regenerating hook";
  if (regenerate === "captions") return "Regenerating captions";
  if (regenerate === "scenes") return "Regenerating scene plan";
  if (regenerate === "style") return "Regenerating style direction";
  return "Building content plan";
}

function workersForAction(label: string): ProcessingWorker[] {
  const lower = label.toLowerCase();
  if (lower.includes("render")) {
    return [
      { name: "Render worker", status: "queued", progress: 0 },
      { name: "Preview cache", status: "queued" },
      { name: "Encoder", status: "queued" }
    ];
  }
  if (lower.includes("beginner") || lower.includes("content") || lower.includes("short") || lower.includes("prompt")) {
    return [
      { name: "Script generator", status: "running", progress: 20 },
      { name: "Scene planner", status: "queued" },
      { name: "Caption builder", status: "queued" },
      { name: "Preview renderer", status: "queued" }
    ];
  }
  if (lower.includes("asset")) {
    return [
      { name: "Indexer", status: "running", progress: 15 },
      { name: "Thumbnail worker", status: "queued" },
      { name: "Metadata probe", status: "queued" }
    ];
  }
  return [
    { name: "Analysis worker", status: "running", progress: 20 },
    { name: "Cache worker", status: "queued" }
  ];
}

function reasoningForAction(label: string) {
  const lower = label.toLowerCase();
  if (lower.includes("beginner")) {
    return [
      "Template and platform decide the default aspect ratio, caption size, pacing, and export preset.",
      "The prompt is converted into product goal, key features, title cards, captions, and scene timing.",
      "The generated project JSON remains editable in Advanced Mode."
    ];
  }
  if (lower.includes("render")) {
    return [
      "Scenes render independently so progress can survive longer jobs.",
      "Transitions, audio mix, and final encoding happen after scene frames are cached.",
      "Final renders can create a delivery package after the encoder completes."
    ];
  }
  if (lower.includes("content") || lower.includes("short")) {
    return [
      "Short-form edits prioritize hook clarity, readable captions, and a clean payoff.",
      "Locked sections stay protected during targeted regeneration.",
      "The review plan must be approved before final export."
    ];
  }
  return [
    "The engine is working locally and will stream concrete progress when the current worker reports it.",
    "Background jobs can be paused, resumed, or left running while you continue editing."
  ];
}

function renderLogSignal(line: string): { patch: Partial<ProcessingState>; activity: string; kind: ActivityKind; detail?: string } | null {
  const clean = line.replace(/^\[[^\]]+\]\s*/, "").trim();
  const lower = clean.toLowerCase();
  const cachedSceneMatch = clean.match(/Using cached scene '([^']+)'/i);
  if (cachedSceneMatch) {
    return {
      patch: { currentStage: `Using cached scene ${cachedSceneMatch[1]}`, currentScene: cachedSceneMatch[1], progress: 18 },
      activity: `Reused cached scene ${cachedSceneMatch[1]}`,
      kind: "success",
      detail: "cache hit"
    };
  }
  const sceneMatch = clean.match(/Rendering scene '([^']+)'(?:\s+\(([^)]+)\))?/i);
  if (sceneMatch) {
    return {
      patch: { currentStage: `Rendering scene ${sceneMatch[1]}`, currentScene: sceneMatch[1], progress: 18 },
      activity: `Rendering scene ${sceneMatch[1]}`,
      kind: "info",
      detail: sceneMatch[2]
    };
  }
  if (lower.includes("loading assets")) return { patch: { currentStage: "Loading assets", progress: 8 }, activity: clean, kind: "info" };
  if (lower.includes("validating json")) return { patch: { currentStage: "Validating JSON", progress: 5 }, activity: "Validated project JSON", kind: "success" };
  if (lower.includes("building timeline")) return { patch: { currentStage: "Building timeline", progress: 10 }, activity: clean, kind: "info" };
  if (lower.includes("rendering scenes")) return { patch: { currentStage: "Rendering scenes", progress: 12 }, activity: "Rendering preview frames", kind: "info" };
  if (lower.includes("applying transitions")) return { patch: { currentStage: "Applying transitions", currentScene: "transitions", progress: 72 }, activity: "Inserted transitions", kind: "success" };
  if (lower.includes("rendering audio")) return { patch: { currentStage: "Synchronizing audio", currentScene: "audio mix", progress: 82 }, activity: "Rendering audio mix", kind: "info" };
  if (lower.includes("exporting")) return { patch: { currentStage: "Encoding final video", currentScene: "export", progress: 92 }, activity: clean, kind: "info" };
  if (lower.includes("export complete")) return { patch: { currentStage: "Export complete", currentScene: "complete", progress: 100, isActive: false }, activity: "Export complete", kind: "success" };
  return null;
}

function stringDefault(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function numberDefault(value: unknown) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) && numberValue > 0 ? numberValue : 0;
}

function selectedPacingForTemplate(templateKey: string) {
  return beginnerTemplates.find((template) => template.key === templateKey)?.pacing || "";
}

function classifyWorkflowInstruction(instruction: string) {
  const lower = instruction.toLowerCase();
  if (lower.includes("caption")) return lower.includes("slow") ? "caption_timing_slower" : "caption_change";
  if (lower.includes("zoom")) return "zoom_intensity";
  if (lower.includes("transition")) return "transition_behavior";
  if (lower.includes("darker") || lower.includes("lighting") || lower.includes("glow")) return "lighting_profile";
  if (lower.includes("faster") || lower.includes("slower") || lower.includes("pacing")) return "pacing_adjustment";
  if (lower.includes("motion")) return "motion_intensity";
  return "assistant_instruction";
}

function buildSuggestedEdits(
  project: ProjectData,
  proactiveAnalysis: ProactiveAnalysis,
  assetReport: Record<string, unknown> | null,
  finalPreflightReport: FinalPreflightReport | null
): ProactiveSuggestion[] {
  const items: ProactiveSuggestion[] = [];
  const add = (item: ProactiveSuggestion | null | undefined) => {
    if (!item || items.some((existing) => existing.id === item.id)) return;
    items.push(item);
  };
  const scenes = [...(project.timeline || [])].sort((a, b) => Number(a.start || 0) - Number(b.start || 0));
  const first = scenes[0];
  if (first && Number(first.duration || 0) > 3.2) {
    add(proactiveItem(
      `suggest_shorten_intro_${first.id}`,
      "workflow",
      "info",
      "Shorten intro",
      `${first.id} runs ${Number(first.duration || 0).toFixed(1)}s. A tighter opening will reach the main edit faster.`,
      "shorten_intro",
      first.id,
      first.start
    ));
  }
  const firstCaption = first ? sceneCaptionText(first).trim() : "";
  if (first && (!firstCaption || Number(first.duration || 0) > 3.2)) {
    add(proactiveItem(
      `suggest_add_hook_${first.id}`,
      "opportunity",
      "info",
      "Add hook in first 3 seconds",
      "Add a sharper opening title so viewers know the payoff immediately.",
      "add_hook",
      first.id,
      first.start
    ));
  }
  const captionCandidate = scenes.find((scene) => !sceneCaptionText(scene).trim() && Number(scene.duration || 0) >= 2);
  if (captionCandidate) {
    add(proactiveItem(
      `suggest_caption_${captionCandidate.id}`,
      "workflow",
      "info",
      "Add captions here",
      `${captionCandidate.id} has enough screen time for a readable caption or lower-third.`,
      "add_caption_here",
      captionCandidate.id,
      captionCandidate.start
    ));
  }
  const transitionCandidate = scenes.slice(0, -1).find((scene) => !scene.transitionOut?.type || String(scene.transitionOut.type) === "cut");
  if (transitionCandidate) {
    add(proactiveItem(
      `suggest_transition_${transitionCandidate.id}`,
      "workflow",
      "info",
      "Add transition here",
      `${transitionCandidate.id} currently exits with a cut. A subtle transition can smooth the beat.`,
      "add_transition_here",
      transitionCandidate.id,
      Number(transitionCandidate.start || 0) + Number(transitionCandidate.duration || 0)
    ));
  }

  const smartAssets = reportRecords(assetReport?.assets);
  const libraryRecommendations = reportRecords(assetReport?.recommendations);
  const highlightSource = smartAssets.find((asset) => {
    const tags = stringList(asset.smartTags);
    const score = Number(((asset.smartDetections as Record<string, unknown> | undefined)?.scores as Record<string, unknown> | undefined)?.highlight || 0);
    return tags.includes("meme_reaction_potential") || tags.includes("action_high_motion") || score >= 0.45;
  }) || collectionFirst(assetReport, "Highlights") || collectionFirst(assetReport, "Funny moments");
  if (highlightSource) {
    const assetKey = String(highlightSource.key || highlightSource.asset || "");
    const moment = firstMoment(highlightSource);
    const timelineTime = timelineTimeForAssetMoment(project, assetKey, Number(moment?.start || moment?.time || 0));
    const scene = (typeof timelineTime === "number" ? sceneAtTime(project, timelineTime) : undefined) || sceneForAsset(project, assetKey) || first;
    add(proactiveItem(
      `suggest_zoom_${assetKey || scene?.id || "highlight"}_${hashTiny(JSON.stringify(moment || highlightSource))}`,
      "opportunity",
      "info",
      "Add zoom on reaction",
      "Smart Assets found a high-energy or reaction-style moment that could use a controlled focus zoom.",
      "add_zoom",
      scene?.id,
      typeof timelineTime === "number" ? timelineTime : scene?.start
    ));
  }

  const silenceSource = libraryRecommendations.find((item) => /silence|dead_space/i.test(String(item.type || item.message || "")))
    || smartAssets.find((asset) => stringList(asset.smartTags).includes("silent_moments"))
    || collectionFirst(assetReport, "Silent/dead sections");
  if (silenceSource) {
    const assetKey = String(silenceSource.asset || silenceSource.key || "");
    const silenceMoment = firstSilentMoment(silenceSource) || firstMoment(silenceSource);
    const silenceStart = Number(silenceMoment?.start || silenceMoment?.time || 0);
    const silenceDuration = Math.max(0, Number(silenceMoment?.duration || (Number(silenceMoment?.end || 0) - silenceStart) || 0));
    const timelineTime = timelineTimeForAssetMoment(project, assetKey, silenceStart);
    const scene = (typeof timelineTime === "number" ? sceneAtTime(project, timelineTime) : undefined) || sceneForAsset(project, assetKey) || first;
    const labelDuration = silenceDuration > 0 ? Math.round(silenceDuration) : 3;
    add({
      ...proactiveItem(
        `suggest_remove_silence_${assetKey || scene?.id || "asset"}_${Math.round(silenceStart * 10)}`,
        "issue",
        "warning",
        `Remove ${labelDuration}s silence`,
        "Smart Assets detected a quiet/dead section. Applying will trim the matching scene non-destructively and add a review marker.",
        "remove_silence",
        scene?.id,
        typeof timelineTime === "number" ? timelineTime : scene?.start
      ),
      duration: labelDuration
    });
  }

  for (const issue of finalPreflightReport?.issues || []) {
    const text = `${issue.category} ${issue.message} ${issue.suggestion || ""}`.toLowerCase();
    if (/caption|safe|text/.test(text)) {
      add(proactiveItem(`suggest_preflight_caption_${issue.id}`, "issue", issue.blocking ? "critical" : "warning", "Fix caption readability", issue.suggestion || issue.message, "improve_captions", issue.scene || undefined));
    } else if (/gap|transition|overlap/.test(text)) {
      add(proactiveItem(`suggest_preflight_transition_${issue.id}`, "issue", issue.blocking ? "critical" : "warning", "Review transition or gap", issue.suggestion || issue.message, "add_transition_here", issue.scene || undefined));
    } else if (/missing|asset|file|media/.test(text)) {
      add(proactiveItem(`suggest_preflight_media_${issue.id}`, "issue", issue.blocking ? "critical" : "warning", "Review missing media", issue.suggestion || issue.message, "review_scene", issue.scene || undefined));
    }
  }

  for (const group of [proactiveAnalysis.issues, proactiveAnalysis.suggestions, proactiveAnalysis.opportunities, proactiveAnalysis.optimizations]) {
    for (const item of group) add(item);
  }
  return items.slice(0, 16);
}

function buildFinalReviewChecks(
  project: ProjectData,
  checkedAssets: AssetCheck[],
  assetReport: Record<string, unknown> | null,
  finalPreflightReport: FinalPreflightReport | null,
  preset: string,
  exportFormat: string,
  qualityReport: Record<string, unknown> | null
): FinalReviewCheck[] {
  const checks: FinalReviewCheck[] = [];
  const add = (check: FinalReviewCheck) => {
    if (!checks.some((item) => item.id === check.id)) checks.push(check);
  };
  const settings = project.project || {};
  const width = Number(settings.width || 0);
  const height = Number(settings.height || 0);
  const fps = Number(settings.fps || 0);
  const scenes = [...(project.timeline || [])].sort((a, b) => Number(a.start || 0) - Number(b.start || 0));
  const reportAssets = reportRecords(assetReport?.assets);
  const preflightIssues = finalPreflightReport?.issues || [];
  const qualityIssues = reportRecords(qualityReport?.issues);
  const projectAssets = project.assets || {};

  const missingMessages: string[] = [];
  for (const asset of checkedAssets) {
    if (!asset.exists) missingMessages.push(`${asset.key} is missing`);
  }
  for (const asset of reportAssets) {
    if (asset.exists === false) missingMessages.push(`${String(asset.key || asset.asset || "asset")} is missing`);
  }
  for (const scene of scenes) {
    for (const layer of scene.layers || []) {
      if (layer.asset && !projectAssets[String(layer.asset)]) missingMessages.push(`${scene.id} references undefined asset ${String(layer.asset)}`);
    }
  }
  for (const track of project.audio || []) {
    const key = String(track.asset || "");
    if (key && !projectAssets[key]) missingMessages.push(`audio references undefined asset ${key}`);
  }
  if (preflightIssues.some((issue) => /missing|asset|media|file/i.test(`${issue.category} ${issue.message}`))) {
    missingMessages.push("preflight found missing or broken media");
  }
  add(missingMessages.length ? {
    id: "missing_media",
    title: "Missing media",
    detail: uniqueStrings(missingMessages).slice(0, 3).join(" / "),
    severity: "error",
    category: "assets",
    suggestion: "Relink missing files in the Media Bin or remove the affected layers before export."
  } : {
    id: "missing_media_pass",
    title: "Missing media",
    detail: "All currently referenced project assets are defined and no missing-media preflight issue is active.",
    severity: "pass",
    category: "assets"
  });

  let gapIssue: FinalReviewCheck | null = null;
  let cursor = 0;
  for (const scene of scenes) {
    const start = Number(scene.start || 0);
    const duration = Math.max(0, Number(scene.duration || 0));
    if (start - cursor > 0.1) {
      gapIssue = {
        id: `timeline_gap_${scene.id}`,
        title: "Timeline gap",
        detail: `There is a ${(start - cursor).toFixed(1)}s gap before ${scene.id}.`,
        severity: "warning",
        category: "timeline",
        sceneId: scene.id,
        time: cursor,
        suggestion: "Close the gap, add a purposeful title card, or mark the pause as intentional."
      };
      break;
    }
    if (cursor - start > 0.1) {
      gapIssue = {
        id: `timeline_overlap_${scene.id}`,
        title: "Timeline overlap",
        detail: `${scene.id} overlaps the previous beat by ${(cursor - start).toFixed(1)}s.`,
        severity: "warning",
        category: "timeline",
        sceneId: scene.id,
        time: start,
        suggestion: "Check scene timing and transition overlap before final export."
      };
      break;
    }
    cursor = Math.max(cursor, start + duration);
  }
  add(gapIssue || {
    id: "timeline_gaps_pass",
    title: "Timeline gaps",
    detail: "Scene timing is continuous with no obvious empty timeline gaps.",
    severity: "pass",
    category: "timeline"
  });

  const safeZoneIssues: FinalReviewCheck[] = [];
  const smallTextIssues: FinalReviewCheck[] = [];
  const minReadableText = Math.max(height > width ? 40 : 30, Math.round(Math.min(width || 1080, height || 1080) * 0.028));
  for (const scene of scenes) {
    for (const layer of scene.layers || []) {
      if (!isTextLikeLayer(layer.type)) continue;
      if (width && height && isLayerOutsideSafeZone(layer, width, height)) {
        safeZoneIssues.push({
          id: `safe_zone_${scene.id}_${hashTiny(JSON.stringify(layer))}`,
          title: "Captions/text outside safe zones",
          detail: `${scene.id} has a text or caption layer close to the frame edge.`,
          severity: "warning",
          category: "readability",
          sceneId: scene.id,
          time: Number(scene.start || 0),
          suggestion: "Move the layer inward or turn on safe-zone overlays in Preview."
        });
      }
      const fontSize = Number(layer.fontSize || layer.size || 0);
      if (fontSize > 0 && fontSize < minReadableText) {
        smallTextIssues.push({
          id: `small_text_${scene.id}_${hashTiny(JSON.stringify(layer))}`,
          title: "Text too small",
          detail: `${scene.id} uses ${Math.round(fontSize)}px text; ${minReadableText}px+ is safer for this canvas.`,
          severity: "warning",
          category: "readability",
          sceneId: scene.id,
          time: Number(scene.start || 0),
          suggestion: "Increase text size or switch to a caption preset designed for the target platform."
        });
      }
    }
  }
  const preflightSafeZone = preflightIssues.find((issue) => /safe|caption|text|contrast/i.test(`${issue.category} ${issue.message}`));
  if (safeZoneIssues.length) {
    add(safeZoneIssues[0]);
  } else if (preflightSafeZone && /safe/i.test(`${preflightSafeZone.category} ${preflightSafeZone.message}`)) {
    add({
      id: `safe_zone_preflight_${preflightSafeZone.id}`,
      title: "Captions/text outside safe zones",
      detail: preflightSafeZone.message,
      severity: preflightSafeZone.blocking ? "error" : "warning",
      category: "readability",
      sceneId: preflightSafeZone.scene || undefined,
      suggestion: preflightSafeZone.suggestion || "Move captions/text into the safe title area."
    });
  } else {
    add({
      id: "safe_zone_pass",
      title: "Captions/text safe zones",
      detail: "No text layer is currently flagged outside the safe-zone bounds.",
      severity: "pass",
      category: "readability"
    });
  }
  add(smallTextIssues[0] || {
    id: "small_text_pass",
    title: "Text size",
    detail: "Text and caption layers with explicit font sizes meet the minimum readability target.",
    severity: "pass",
    category: "readability"
  });

  const audioWarnings = audioReviewWarnings(project, reportAssets);
  if (audioWarnings.length) {
    add(audioWarnings[0]);
  } else {
    add({
      id: "audio_level_pass",
      title: "Audio loudness",
      detail: "Configured audio track volumes are within a safe range.",
      severity: "pass",
      category: "audio"
    });
  }

  const blackFrameIssue = firstMatchingIssue([...preflightIssues, ...qualityIssues], /black frame|black_frames|black_start/i);
  const frozenFrameIssue = firstMatchingIssue([...preflightIssues, ...qualityIssues], /frozen frame|frozen_frames|freeze_start/i);
  if (blackFrameIssue) {
    add({
      id: "black_frames",
      title: "Black frames",
      detail: issueMessage(blackFrameIssue, "Black frames were detected in the preview or quality report."),
      severity: "warning",
      category: "visual quality",
      suggestion: "Trim the section, soften the transition, or regenerate the affected scene."
    });
  } else {
    add({
      id: "black_frames_pass",
      title: "Black frames",
      detail: finalPreflightReport || qualityReport ? "No black frames were reported by the current checks." : "Run preflight or video quality analysis to inspect the rendered preview for black frames.",
      severity: finalPreflightReport || qualityReport ? "pass" : "info",
      category: "visual quality"
    });
  }
  if (frozenFrameIssue) {
    add({
      id: "frozen_frames",
      title: "Frozen frames",
      detail: issueMessage(frozenFrameIssue, "Frozen frames were detected in the preview or quality report."),
      severity: "warning",
      category: "visual quality",
      suggestion: "Regenerate the scene, replace the transition, or trim the frozen segment."
    });
  } else {
    add({
      id: "frozen_frames_pass",
      title: "Frozen frames",
      detail: finalPreflightReport || qualityReport ? "No frozen frames were reported by the current checks." : "Run preflight or video quality analysis to inspect the rendered preview for freezes.",
      severity: finalPreflightReport || qualityReport ? "pass" : "info",
      category: "visual quality"
    });
  }

  const lowRes = reportAssets.find((asset) => {
    const resolution = assetResolution(asset);
    if (!resolution) return false;
    const kind = String(asset.type || "");
    if (!["video", "image"].includes(kind)) return false;
    if (resolution.width < 720 || resolution.height < 720) return true;
    if (width && height && (resolution.width < width * 0.55 || resolution.height < height * 0.55)) return true;
    return false;
  });
  if (lowRes) {
    const resolution = assetResolution(lowRes);
    add({
      id: `low_resolution_${String(lowRes.key || lowRes.asset || "asset")}`,
      title: "Low-resolution clips",
      detail: `${String(lowRes.key || lowRes.asset || "asset")} is ${resolution?.width || "?"}x${resolution?.height || "?"}, which may soften the final export.`,
      severity: "warning",
      category: "assets",
      suggestion: "Use a higher-resolution source, lower the export preset, or accept the softness intentionally."
    });
  } else {
    add({
      id: "low_resolution_pass",
      title: "Low-resolution clips",
      detail: assetReport ? "Analyzed visual assets are not below the current resolution threshold." : "Run Smart Asset analysis to inspect imported media resolution.",
      severity: assetReport ? "pass" : "info",
      category: "assets"
    });
  }

  const target = expectedPresetSize(preset);
  if (target && width && height && !aspectRatiosClose(width, height, target.width, target.height)) {
    add({
      id: "wrong_aspect_ratio",
      title: "Wrong aspect ratio",
      detail: `${friendlyPresetName(preset)} expects ${target.width}x${target.height} style framing, but the project is ${width}x${height}.`,
      severity: /short|tiktok|reel|instagram/i.test(preset) ? "error" : "warning",
      category: "export",
      suggestion: "Use Auto Social Reformat, switch the preset, or change project dimensions before export."
    });
  } else {
    add({
      id: "aspect_ratio_pass",
      title: "Aspect ratio",
      detail: target && width && height ? `Project framing matches ${friendlyPresetName(preset)} closely enough.` : "No target aspect-ratio mismatch is currently detectable.",
      severity: "pass",
      category: "export"
    });
  }

  const exportIssues: string[] = [];
  if (width && width % 2) exportIssues.push("project width is odd");
  if (height && height % 2) exportIssues.push("project height is odd");
  if (fps > 120) exportIssues.push("FPS is unusually high");
  if (exportFormat === "gif" && (project.audio || []).length) exportIssues.push("GIF export will not include audio");
  if (project.exportPreset && project.exportPreset !== preset) exportIssues.push(`project JSON preset is ${friendlyPresetName(project.exportPreset)} while UI preset is ${friendlyPresetName(preset)}`);
  if (preflightIssues.some((issue) => /export|preset|format|codec/i.test(`${issue.category} ${issue.message}`))) exportIssues.push("preflight reported an export settings issue");
  add(exportIssues.length ? {
    id: "export_settings_mismatch",
    title: "Export settings mismatch",
    detail: uniqueStrings(exportIssues).join(" / "),
    severity: exportIssues.some((item) => /odd|preflight/.test(item)) ? "error" : "warning",
    category: "export",
    suggestion: "Open Export settings, choose the target platform preset, then rerun review checks."
  } : {
    id: "export_settings_pass",
    title: "Export settings",
    detail: `${exportFormat.toUpperCase()} export settings look consistent with the current project configuration.`,
    severity: "pass",
    category: "export"
  });

  const musicRisk = copyrightMusicRisk(project, checkedAssets, reportAssets);
  add(musicRisk || {
    id: "copyright_music_pass",
    title: "Music usage",
    detail: "No obvious copyright-risk music filename was detected. Keep license notes with the project when available.",
    severity: "pass",
    category: "legal"
  });

  return checks;
}

function audioReviewWarnings(project: ProjectData, reportAssets: Array<Record<string, unknown>>): FinalReviewCheck[] {
  const warnings: FinalReviewCheck[] = [];
  const audioTracks = project.audio || [];
  const hasVideo = (project.timeline || []).some((scene) => (scene.layers || []).some((layer) => layer.type === "video"));
  if (!audioTracks.length) {
    return hasVideo ? [{
      id: "audio_missing_info",
      title: "Audio too loud/quiet",
      detail: "No dedicated audio/music track is configured, so the edit may feel silent after export.",
      severity: "info",
      category: "audio",
      suggestion: "Add music/SFX or confirm that silence is intentional."
    }] : [];
  }
  const reportByKey = new Map(reportAssets.map((asset) => [String(asset.key || asset.asset || ""), asset]));
  for (const track of audioTracks) {
    const assetKey = String(track.asset || "");
    const volume = Number(track.volume ?? 1);
    if (volume > 1 || volume >= 0.95) {
      warnings.push({
        id: `audio_loud_${assetKey || warnings.length}`,
        title: "Audio too loud",
        detail: `${assetKey || "Audio track"} is set to ${(volume * 100).toFixed(0)}% volume.`,
        severity: "warning",
        category: "audio",
        suggestion: "Lower volume or normalize audio before export."
      });
    } else if (volume <= 0.01 || (volume > 0 && volume < 0.12)) {
      warnings.push({
        id: `audio_quiet_${assetKey || warnings.length}`,
        title: "Audio too quiet",
        detail: `${assetKey || "Audio track"} is set to ${(volume * 100).toFixed(0)}% volume.`,
        severity: "warning",
        category: "audio",
        suggestion: "Raise volume or add loudness normalization before export."
      });
    }
    const report = reportByKey.get(assetKey);
    const loudness = report?.loudness && typeof report.loudness === "object" && !Array.isArray(report.loudness) ? report.loudness as Record<string, unknown> : null;
    const peak = Number(loudness?.peak ?? 0);
    const average = Number(loudness?.average ?? 0);
    if (peak > 0.94) {
      warnings.push({
        id: `audio_peak_${assetKey || warnings.length}`,
        title: "Audio clipping risk",
        detail: `${assetKey || "Audio"} has very high detected peaks.`,
        severity: "warning",
        category: "audio",
        suggestion: "Use limiter/normalization or lower the track volume."
      });
    } else if (peak > 0 && peak < 0.08 && average < 0.03) {
      warnings.push({
        id: `audio_low_peak_${assetKey || warnings.length}`,
        title: "Audio may be too quiet",
        detail: `${assetKey || "Audio"} has low detected loudness.`,
        severity: "warning",
        category: "audio",
        suggestion: "Normalize loudness or increase the track volume."
      });
    }
  }
  return warnings;
}

function firstMatchingIssue(
  issues: Array<FinalPreflightIssue | Record<string, unknown>>,
  pattern: RegExp
): FinalPreflightIssue | Record<string, unknown> | undefined {
  return issues.find((issue) => pattern.test(`${String(issue.category || "")} ${String(issue.message || "")} ${String(issue.id || "")}`));
}

function issueMessage(issue: FinalPreflightIssue | Record<string, unknown>, fallback: string) {
  return String(issue.message || fallback);
}

function assetResolution(asset: Record<string, unknown>): { width: number; height: number } | null {
  const resolution = asset.resolution;
  if (resolution && typeof resolution === "object" && !Array.isArray(resolution)) {
    const record = resolution as Record<string, unknown>;
    const width = Number(record.width || 0);
    const height = Number(record.height || 0);
    if (width > 0 && height > 0) return { width, height };
  }
  const width = Number(asset.width || 0);
  const height = Number(asset.height || 0);
  return width > 0 && height > 0 ? { width, height } : null;
}

function expectedPresetSize(preset: string): { width: number; height: number } | null {
  const value = preset.toLowerCase();
  if (/short|tiktok|reel|instagram/.test(value)) return { width: 1080, height: 1920 };
  if (/square/.test(value)) return { width: 1080, height: 1080 };
  if (/discord|720/.test(value)) return { width: 1280, height: 720 };
  if (/4k|cinematic/.test(value)) return { width: 3840, height: 2160 };
  if (/youtube|1080|landscape/.test(value)) return { width: 1920, height: 1080 };
  return null;
}

function aspectRatiosClose(width: number, height: number, targetWidth: number, targetHeight: number) {
  const actual = width / Math.max(height, 1);
  const target = targetWidth / Math.max(targetHeight, 1);
  return Math.abs(actual - target) <= 0.08;
}

function copyrightMusicRisk(
  project: ProjectData,
  checkedAssets: AssetCheck[],
  reportAssets: Array<Record<string, unknown>>
): FinalReviewCheck | null {
  const licenses = project.metadata?.assetLicenses;
  const licenseRecords = licenses && typeof licenses === "object" && !Array.isArray(licenses) ? licenses as Record<string, unknown> : {};
  const audioKeys = new Set<string>();
  for (const track of project.audio || []) {
    if (track.asset) audioKeys.add(String(track.asset));
  }
  for (const asset of checkedAssets) {
    if (asset.type === "audio") audioKeys.add(asset.key);
  }
  for (const asset of reportAssets) {
    if (String(asset.type || "") === "audio") audioKeys.add(String(asset.key || asset.asset || ""));
  }
  if (!audioKeys.size) return null;
  const namedPaths = [...audioKeys].map((key) => {
    const fromProject = project.assets?.[key];
    const checked = checkedAssets.find((asset) => asset.key === key)?.path;
    const reported = String(reportAssets.find((asset) => String(asset.key || asset.asset || "") === key)?.path || "");
    return { key, path: fromProject || checked || reported || key };
  });
  const risky = namedPaths.find((item) => /song|music|beat|track|copyright|commercial|download|youtube/i.test(`${item.key} ${item.path}`));
  const unlicensed = namedPaths.find((item) => !licenseRecords[item.key] && !licenseRecords[item.path]);
  if (risky || unlicensed) {
    const item = risky || unlicensed || namedPaths[0];
    return {
      id: "copyright_music_risk",
      title: "Copyright-risk music",
      detail: `${shortFileName(item.path)} has no license/attribution metadata saved in this project.`,
      severity: risky ? "warning" : "info",
      category: "legal",
      suggestion: "Verify usage rights before posting, or attach license notes in project metadata."
    };
  }
  return null;
}

function shortFileName(pathValue: string) {
  return pathValue.split(/[\\/]/).filter(Boolean).pop() || pathValue;
}

function uniqueStrings(values: string[]) {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}

function analyzeProactiveAssistance(
  project: ProjectData,
  adaptiveMemory: AdaptiveWorkflowMemory | null,
  renderQueueItems: RenderQueueItem[],
  preset: string,
  useCache: boolean
): ProactiveAnalysis {
  const suggestions: ProactiveSuggestion[] = [];
  const issues: ProactiveSuggestion[] = [];
  const optimizations: ProactiveSuggestion[] = [];
  const opportunities: ProactiveSuggestion[] = [];
  const coaching: ProactiveSuggestion[] = [];
  const scenes = [...(project.timeline || [])].sort((a, b) => Number(a.start || 0) - Number(b.start || 0));
  const duration = totalTimelineDuration(project);
  const verticalPreset = /short|tiktok|reels|instagram/.test(preset);
  const transitionCounts = countTransitions(scenes);
  const repeatedTransition = Object.entries(transitionCounts).sort((a, b) => b[1] - a[1])[0];
  const assetsCount = Object.keys(project.assets || {}).length;
  const failedRender = renderQueueItems.some((item) => item.status === "failed");
  const first = scenes[0];
  if (first && verticalPreset && Number(first.duration || 0) > 3.2) {
    issues.push(proactiveItem("short_intro", "issue", "warning", "Intro may be too long for Shorts", "Short-form hooks usually need the first beat within 3 seconds.", "shorten_intro", first.id, first.start));
  }
  for (const scene of scenes) {
    const caption = sceneCaptionText(scene);
    const wordsPerSecond = captionWordRate(caption, Number(scene.duration || 1));
    if (caption && (wordsPerSecond > 3.4 || caption.length / Math.max(Number(scene.duration || 1), 0.5) > 22)) {
      issues.push(proactiveItem(`caption_fast_${scene.id}`, "issue", "warning", "Captions may be too fast", `${scene.id} reads at about ${wordsPerSecond.toFixed(1)} words/sec.`, "improve_captions", scene.id, scene.start));
    }
    const layers = scene.layers || [];
    const textLayers = layers.filter((layer) => ["text", "caption", "captions", "lower_third"].includes(layer.type)).length;
    if (layers.length >= 5 && textLayers >= 2) {
      issues.push(proactiveItem(`visual_overload_${scene.id}`, "issue", "warning", "Visual overload risk", `${scene.id} has ${layers.length} layers and multiple text elements.`, "review_scene", scene.id, scene.start));
    }
    if (Number(scene.duration || 0) > 8 && !caption && !layers.some((layer) => layer.type === "text")) {
      issues.push(proactiveItem(`dead_section_${scene.id}`, "issue", "warning", "Possible dead section", `${scene.id} is long without text or caption guidance.`, "review_scene", scene.id, scene.start));
    }
  }
  for (let index = 1; index < scenes.length; index += 1) {
    const previous = Number(scenes[index - 1].duration || 0);
    const current = Number(scenes[index].duration || 0);
    if (previous > 0 && current > 4 && current > previous * 2.2) {
      issues.push(proactiveItem(`pacing_drop_${scenes[index].id}`, "issue", "warning", "Scene pacing drops sharply", `${scenes[index].id} is much longer than the previous beat.`, "review_scene", scenes[index].id, scenes[index].start));
    }
  }
  if (repeatedTransition && repeatedTransition[1] >= Math.max(3, Math.ceil((scenes.length - 1) * 0.7))) {
    suggestions.push(proactiveItem("repeated_transition", "workflow", "info", "Transition repetition detected", `${repeatedTransition[0]} is doing most of the scene-to-scene work.`, "smooth_transitions"));
  }
  const adaptiveDefaults = adaptiveMemory?.smartDefaults || {};
  if (String(adaptiveDefaults.captionDensity || "") === "high" && !hasCaptionLayer(project)) {
    suggestions.push(proactiveItem("caption_memory", "workflow", "info", "Creator usually prefers captions", "Your adaptive memory suggests caption-led edits work well for this profile.", "improve_captions"));
  }
  if (duration > 55 || assetsCount > 10) {
    optimizations.push(proactiveItem("enable_proxy", "optimization", "info", "Enable proxies for a smoother preview", "This project is large enough that proxy preview and cache reuse will reduce waiting.", "enable_proxies"));
  }
  if (!useCache) {
    optimizations.push(proactiveItem("enable_cache", "optimization", "info", "Render cache is off", "Re-enabling cache will make preview iterations faster.", "enable_proxies"));
  }
  if (failedRender) {
    optimizations.push(proactiveItem("failed_render", "optimization", "warning", "A render failed recently", "Try preview quality, cache, or a simpler export preset before another final render.", "enable_proxies"));
  }
  const strongMoments = findCreativeOpportunities(scenes);
  opportunities.push(...strongMoments.slice(0, 4));
  if (verticalPreset && first && Number(first.duration || 0) > 3) {
    coaching.push(proactiveItem("coach_shorts_intro", "coaching", "info", "Shorts coaching", "This intro may be too long for Shorts. A tighter first title card usually keeps momentum.", "shorten_intro", first.id, first.start));
  } else if (/tutorial|walkthrough|software/i.test(JSON.stringify(project.metadata || {}))) {
    coaching.push(proactiveItem("coach_tutorial", "coaching", "info", "Tutorial coaching", "Tutorials usually perform better with calmer transitions and readable lower-third captions.", "improve_captions"));
  } else {
    coaching.push(proactiveItem("coach_general", "coaching", "info", "Creative coaching", "The assistant will keep looking for hook, pacing, readability, and thumbnail opportunities while you edit.", "review_scene", scenes[0]?.id, scenes[0]?.start));
  }
  const warningCount = issues.filter((item) => item.severity !== "info").length;
  const pacingScore = Math.max(35, 100 - warningCount * 12 - (repeatedTransition && repeatedTransition[1] > 2 ? 8 : 0));
  const readabilityScore = Math.max(30, 100 - issues.filter((item) => /caption|overload|dead/i.test(item.title)).length * 15);
  return {
    suggestions: suggestions.slice(0, 8),
    issues: issues.slice(0, 8),
    optimizations: optimizations.slice(0, 5),
    opportunities: opportunities.slice(0, 6),
    coaching: coaching.slice(0, 3),
    summary: {
      pacingScore,
      readabilityScore,
      opportunityCount: opportunities.length,
      warningCount
    }
  };
}

function proactiveItem(
  id: string,
  category: ProactiveSuggestion["category"],
  severity: ProactiveSuggestion["severity"],
  title: string,
  detail: string,
  action: string,
  sceneId?: string,
  time?: number,
  command?: string
): ProactiveSuggestion {
  return { id, category, severity, title, detail, action, sceneId, time, command };
}

function buildBackgroundImprovementQueue(project: ProjectData, adaptiveMemory: AdaptiveWorkflowMemory | null, analysis: ProactiveAnalysis): BackgroundImprovement[] {
  const scenes = project.timeline || [];
  const firstText = sceneCaptionText(scenes[0]) || firstTextLayerValue(project) || "New showcase";
  const productName = productNameFromProject(project);
  const preferredHook = String(adaptiveMemory?.preferences?.hookStyle || "clean_professional");
  const items: BackgroundImprovement[] = [];
  items.push({
    id: `hook_${hashTiny(firstText)}_${preferredHook}`,
    type: "alternate_hook",
    title: "Alternate hook",
    detail: "Prepared while idle from the current product goal and creator memory.",
    sceneId: scenes[0]?.id,
    time: scenes[0]?.start || 0,
    text: alternateHookText(productName, preferredHook, firstText)
  });
  const captionScene = scenes
    .map((scene) => ({ scene, caption: sceneCaptionText(scene) }))
    .filter((item) => item.caption.length > 40)
    .sort((a, b) => b.caption.length - a.caption.length)[0];
  if (captionScene) {
    items.push({
      id: `caption_${captionScene.scene.id}_${hashTiny(captionScene.caption)}`,
      type: "alternate_caption",
      title: "Cleaner caption",
      detail: `Shorter caption prepared for ${captionScene.scene.id}.`,
      sceneId: captionScene.scene.id,
      time: captionScene.scene.start,
      text: shortenCaptionText(captionScene.caption)
    });
  }
  const slowScene = scenes.find((scene, index) => index > 0 && Number(scene.duration || 0) > 6);
  if (slowScene) {
    items.push({
      id: `pace_${slowScene.id}`,
      type: "pacing_improvement",
      title: "Tighter pacing",
      detail: `${slowScene.id} can be trimmed slightly without changing source media.`,
      sceneId: slowScene.id,
      time: slowScene.start
    });
  }
  const opportunity = analysis.opportunities[0];
  if (opportunity) {
    items.push({
      id: `thumb_${opportunity.sceneId || "scene"}_${Math.round(Number(opportunity.time || 0) * 10)}`,
      type: "thumbnail_candidate",
      title: "Thumbnail candidate",
      detail: opportunity.detail,
      sceneId: opportunity.sceneId,
      time: opportunity.time
    });
  }
  return items.slice(0, 6);
}

function findCreativeOpportunities(scenes: SceneData[]): ProactiveSuggestion[] {
  const opportunities: ProactiveSuggestion[] = [];
  for (const scene of scenes) {
    const caption = sceneCaptionText(scene).toLowerCase();
    const layerTypes = new Set((scene.layers || []).map((layer) => layer.type));
    const midpoint = Number(scene.start || 0) + Number(scene.duration || 0) / 2;
    if (/result|payoff|success|fixed|before|after|scan|reveal|launch/.test(caption)) {
      opportunities.push(proactiveItem(`reveal_${scene.id}`, "opportunity", "info", "Dramatic reveal moment", `${scene.id} has payoff language that could anchor the edit or thumbnail.`, "preview_moment", scene.id, midpoint));
    } else if (layerTypes.has("video") && Number(scene.duration || 0) <= 3.5) {
      opportunities.push(proactiveItem(`energy_${scene.id}`, "opportunity", "info", "High-energy section", `${scene.id} is short and visual, good for music hits or a quick hook.`, "preview_moment", scene.id, midpoint));
    } else if (layerTypes.has("image") && layerTypes.has("text")) {
      opportunities.push(proactiveItem(`thumbnail_${scene.id}`, "opportunity", "info", "Potential thumbnail frame", `${scene.id} combines a visual with readable text.`, "preview_moment", scene.id, midpoint));
    }
  }
  return opportunities;
}

function countTransitions(scenes: SceneData[]) {
  const counts: Record<string, number> = {};
  for (const scene of scenes) {
    const type = typeof scene.transitionOut?.type === "string" ? scene.transitionOut.type : "";
    if (type) counts[type] = (counts[type] || 0) + 1;
  }
  return counts;
}

function captionWordRate(caption: string, duration: number) {
  const words = caption.split(/\s+/).filter(Boolean).length;
  return words / Math.max(duration, 0.5);
}

function hasCaptionLayer(project: ProjectData) {
  if (project.captions?.length) return true;
  return (project.timeline || []).some((scene) => (scene.layers || []).some((layer) => layer.type === "caption" || layer.type === "captions"));
}

function exportReadinessWarnings(
  project: ProjectData,
  finalPreflight: FinalPreflightReport | null,
  settings: { resolutionSetting: string; aspectRatio: string; burnCaptions: boolean }
): ExportWarning[] {
  const warnings: ExportWarning[] = [];
  const add = (warning: ExportWarning) => {
    if (!warnings.some((item) => item.id === warning.id)) warnings.push(warning);
  };
  const projectSettings = project.project || {};
  const scenes = [...(project.timeline || [])].sort((a, b) => Number(a.start || 0) - Number(b.start || 0));
  const assets = project.assets || {};
  const desired = exportTargetSize(settings.resolutionSetting, settings.aspectRatio);
  const width = Number(projectSettings.width || 0);
  const height = Number(projectSettings.height || 0);
  const supportedExts = new Set([
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".mpeg", ".mpg", ".m4v", ".ts", ".mts", ".m2ts",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".svg",
    ".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"
  ]);

  if (!finalPreflight) {
    add({
      id: "preflight_not_run",
      title: "Run preflight check",
      message: "Final export should be checked for missing media, timing, captions, and platform settings first.",
      suggestion: "Click Run Preflight before exporting the final file.",
      severity: "info"
    });
  }

  for (const issue of finalPreflight?.issues || []) {
    const text = `${issue.category} ${issue.message}`.toLowerCase();
    if (/missing|asset|media|file/.test(text)) {
      add({
        id: `preflight_media_${issue.id}`,
        title: "Missing media",
        message: issue.message,
        suggestion: issue.suggestion || "Relink the asset or remove the layer before export.",
        severity: issue.blocking ? "error" : "warning"
      });
    } else if (/unsupported|codec|decode|format/.test(text)) {
      add({
        id: `preflight_format_${issue.id}`,
        title: "Unsupported file or codec",
        message: issue.message,
        suggestion: issue.suggestion || "Transcode or replace the source media before final export.",
        severity: issue.blocking ? "error" : "warning"
      });
    } else if (/caption|safe|text/.test(text)) {
      add({
        id: `preflight_caption_${issue.id}`,
        title: "Caption or safe-zone issue",
        message: issue.message,
        suggestion: issue.suggestion || "Move captions into the safe zone or adjust caption timing.",
        severity: issue.blocking ? "error" : "warning"
      });
    }
  }

  if (width && height && (width < desired.width || height < desired.height)) {
    add({
      id: "low_resolution",
      title: "Low resolution for preset",
      message: `Project is ${width}x${height}, but ${settings.resolutionSetting} ${settings.aspectRatio} expects about ${desired.width}x${desired.height}.`,
      suggestion: "Use a lower export resolution or switch the project/export preset to the target platform size.",
      severity: "warning"
    });
  }

  let cursor = 0;
  for (const scene of scenes) {
    const start = Number(scene.start || 0);
    const duration = Number(scene.duration || 0);
    if (start - cursor > 0.1) {
      add({
        id: `timeline_gap_${scene.id}`,
        title: "Timeline gap",
        message: `There is a ${(start - cursor).toFixed(1)}s gap before ${scene.id}.`,
        suggestion: "Close the gap, add a title card, or confirm the pause is intentional.",
        severity: "warning"
      });
      break;
    }
    if (cursor - start > 0.1) {
      add({
        id: `timeline_overlap_${scene.id}`,
        title: "Timeline overlap",
        message: `${scene.id} overlaps the previous scene by ${(cursor - start).toFixed(1)}s.`,
        suggestion: "Check transition overlap and scene start times before exporting.",
        severity: "warning"
      });
      break;
    }
    cursor = Math.max(cursor, start + Math.max(0, duration));
  }

  for (const [key, path] of Object.entries(assets)) {
    const ext = mediaExtension(path);
    if (!path || !path.trim()) {
      add({
        id: `empty_asset_${key}`,
        title: "Missing media",
        message: `Asset "${key}" has no file path.`,
        suggestion: "Relink or remove this asset before exporting.",
        severity: "error"
      });
    } else if (ext && !supportedExts.has(ext)) {
      add({
        id: `unsupported_asset_${key}`,
        title: "Unsupported file type",
        message: `${key} uses ${ext}, which is not in the supported import list.`,
        suggestion: "Convert the asset to a supported video, image, or audio format.",
        severity: "warning"
      });
    }
  }

  for (const scene of scenes) {
    for (const layer of scene.layers || []) {
      if (layer.asset && !assets[String(layer.asset)]) {
        add({
          id: `unresolved_layer_asset_${scene.id}_${String(layer.asset)}`,
          title: "Missing media",
          message: `${scene.id} references asset "${String(layer.asset)}", but it is not defined in project assets.`,
          suggestion: "Add the asset to the Media Bin/project JSON or replace the layer asset key.",
          severity: "error"
        });
      }
      if (isTextLikeLayer(layer.type) && width && height && isLayerOutsideSafeZone(layer, width, height)) {
        add({
          id: `caption_safe_${scene.id}_${String(layer.text || layer.type)}`,
          title: "Caption outside safe zone",
          message: `${scene.id} has text or captions close to the edge of the frame.`,
          suggestion: "Move the text inward or use the caption safe-zone overlay before export.",
          severity: "warning"
        });
      }
    }
  }

  if (hasCaptionLayer(project) && !settings.burnCaptions) {
    add({
      id: "captions_not_burned",
      title: "Captions not burned in",
      message: "This project has caption layers, but burn-in captions is turned off.",
      suggestion: "Keep burn-in enabled for social exports, or export separate subtitle files from the delivery package.",
      severity: "info"
    });
  }

  return warnings;
}

function exportTargetSize(resolutionSetting: string, aspectRatio: string) {
  const baseHeight = resolutionSetting === "4k" ? 2160 : resolutionSetting === "1440p" ? 1440 : resolutionSetting === "720p" ? 720 : 1080;
  if (aspectRatio === "9:16") return { width: Math.round(baseHeight * 9 / 16), height: baseHeight };
  if (aspectRatio === "1:1") return { width: baseHeight, height: baseHeight };
  if (aspectRatio === "4:5") return { width: Math.round(baseHeight * 4 / 5), height: baseHeight };
  return { width: Math.round(baseHeight * 16 / 9), height: baseHeight };
}

function mediaExtension(path: string) {
  const clean = path.split(/[?#]/)[0] || "";
  const match = clean.match(/\.[a-z0-9]+$/i);
  return match ? match[0].toLowerCase() : "";
}

function isTextLikeLayer(type: string) {
  return type === "text" || type === "caption" || type === "captions" || type === "lower_third";
}

function isLayerOutsideSafeZone(layer: Record<string, unknown>, width: number, height: number) {
  const x = typeof layer.x === "number" ? layer.x : Number.NaN;
  const y = typeof layer.y === "number" ? layer.y : Number.NaN;
  const safeX = width * 0.06;
  const safeY = height * 0.06;
  const fontSize = Number(layer.fontSize || 0);
  if (Number.isFinite(x) && (x < safeX || x > width - safeX)) return true;
  if (Number.isFinite(y) && (y < safeY || y + Math.max(fontSize, 0) > height - safeY)) return true;
  return false;
}

function reportRecords(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object" && !Array.isArray(item)) : [];
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : [];
}

function collectionFirst(assetReport: Record<string, unknown> | null, name: string): Record<string, unknown> | null {
  const collections = assetReport?.smartCollections;
  if (!collections || typeof collections !== "object" || Array.isArray(collections)) return null;
  return reportRecords((collections as Record<string, unknown>)[name])[0] || null;
}

function firstMoment(source: Record<string, unknown>): Record<string, unknown> | null {
  for (const key of ["moments", "highlightCandidates", "loudMoments", "sceneChanges"]) {
    const found = reportRecords(source[key])[0];
    if (found) return found;
  }
  const smartMoments = source.smartMoments;
  if (smartMoments && typeof smartMoments === "object" && !Array.isArray(smartMoments)) {
    const record = smartMoments as Record<string, unknown>;
    for (const key of ["highlightCandidates", "loudMoments", "sceneChanges", "silentMoments"]) {
      const found = reportRecords(record[key])[0];
      if (found) return found;
    }
  }
  return null;
}

function firstSilentMoment(source: Record<string, unknown>): Record<string, unknown> | null {
  const direct = reportRecords(source.silentMoments)[0];
  if (direct) return direct;
  const smartMoments = source.smartMoments;
  if (smartMoments && typeof smartMoments === "object" && !Array.isArray(smartMoments)) {
    const found = reportRecords((smartMoments as Record<string, unknown>).silentMoments)[0];
    if (found) return found;
  }
  return null;
}

function sceneForAsset(project: ProjectData, assetKey: string): SceneData | undefined {
  if (!assetKey) return undefined;
  return (project.timeline || []).find((scene) => (scene.layers || []).some((layer) => String(layer.asset || "") === assetKey));
}

function timelineTimeForAssetMoment(project: ProjectData, assetKey: string, sourceTime: number): number | undefined {
  if (!assetKey || !Number.isFinite(sourceTime)) return undefined;
  for (const scene of project.timeline || []) {
    for (const layer of scene.layers || []) {
      if (String(layer.asset || "") !== assetKey) continue;
      const trimStart = Number(layer.trimStart || 0);
      const localTime = Math.max(0, sourceTime - trimStart);
      if (localTime <= Number(scene.duration || 0) + 0.1) return Number(scene.start || 0) + localTime;
    }
  }
  return undefined;
}

function applyZoomSuggestion(project: ProjectData, sceneId: string, zoomAmount: number): ProjectData {
  const next = structuredClone(project);
  const scene = (next.timeline || []).find((item) => item.id === sceneId);
  const layer = scene?.layers?.find((item) => item.type === "video" || item.type === "image");
  if (!scene || !layer) return next;
  const currentScale = Number(layer.scale || 1);
  layer.scale = Number(Math.max(Number.isFinite(currentScale) ? currentScale : 1, zoomAmount).toFixed(3));
  layer.animation = {
    ...((layer.animation && typeof layer.animation === "object" && !Array.isArray(layer.animation)) ? layer.animation as Record<string, unknown> : {}),
    in: "zoomIn",
    duration: Number(Math.min(0.8, Math.max(0.35, Number(scene.duration || 1) * 0.2)).toFixed(3))
  };
  next.metadata = {
    ...next.metadata,
    suggestedEdits: {
      ...((next.metadata?.suggestedEdits && typeof next.metadata.suggestedEdits === "object" && !Array.isArray(next.metadata.suggestedEdits)) ? next.metadata.suggestedEdits as Record<string, unknown> : {}),
      lastApplied: "add_zoom",
      appliedAt: new Date().toISOString()
    }
  };
  return next;
}

function addCaptionSuggestion(project: ProjectData, sceneId: string): ProjectData {
  const next = structuredClone(project);
  const scene = (next.timeline || []).find((item) => item.id === sceneId);
  if (!scene) return next;
  const existing = scene.layers?.find((layer) => layer.type === "caption" || layer.type === "captions" || layer.type === "text");
  if (existing && String(existing.text || "").trim()) return next;
  const caption = sceneCaptionText(scene) || captionFromSceneId(scene.id) || "Key moment";
  scene.layers = [
    ...(scene.layers || []),
    {
      type: "caption",
      items: [{ text: caption, start: 0, duration: Math.min(3, Math.max(0.8, Number(scene.duration || 2))) }],
      layout: "caption_bottom",
      fontSize: 52,
      color: "#ffffff",
      strokeColor: "#000000",
      strokeWidth: 3,
      shadow: true,
      safeZone: true
    }
  ];
  next.metadata = {
    ...next.metadata,
    suggestedEdits: {
      ...((next.metadata?.suggestedEdits && typeof next.metadata.suggestedEdits === "object" && !Array.isArray(next.metadata.suggestedEdits)) ? next.metadata.suggestedEdits as Record<string, unknown> : {}),
      lastApplied: "add_caption_here",
      appliedAt: new Date().toISOString()
    }
  };
  return next;
}

function captionFromSceneId(sceneId: string) {
  return friendlyPresetName(sceneId).replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function replaceFirstSceneText(project: ProjectData, text: string): ProjectData {
  const next = structuredClone(project);
  const first = next.timeline?.[0];
  if (!first) return next;
  let replaced = false;
  first.layers = (first.layers || []).map((layer) => {
    if (!replaced && (layer.type === "text" || layer.type === "lower_third")) {
      replaced = true;
      return { ...layer, text };
    }
    return layer;
  });
  if (!replaced) first.layers = [{ type: "text", text, layout: "center", fontSize: 72, color: "#ffffff" }, ...(first.layers || [])];
  return next;
}

function shortenScene(project: ProjectData, sceneId: string, factor: number): ProjectData {
  const index = (project.timeline || []).findIndex((scene) => scene.id === sceneId);
  const scene = project.timeline?.[index];
  if (!scene || index < 0) return project;
  return updateSceneTimingAdvanced(project, index, { duration: Math.max(0.8, Number((Number(scene.duration || 0) * factor).toFixed(3))) }, { ripple: true, snapSeconds: 0.05 });
}

function firstTextLayerValue(project: ProjectData) {
  for (const scene of project.timeline || []) {
    for (const layer of scene.layers || []) {
      if (typeof layer.text === "string" && layer.text.trim()) return layer.text.trim();
    }
  }
  return "";
}

function productNameFromProject(project: ProjectData) {
  const beginner = project.metadata?.beginnerAutoTemplate as Record<string, unknown> | undefined;
  const product = String(project.metadata?.productName || project.metadata?.title || beginner?.productName || "");
  if (product.trim()) return product.trim();
  const firstText = firstTextLayerValue(project);
  return firstText || "this product";
}

function alternateHookText(productName: string, style: string, current: string) {
  const product = productName || "This workflow";
  if (style === "curiosity") return `What if ${product} fixed the blockers before launch?`;
  if (style === "problem_solution") return `Stop losing launches to hidden setup blockers.`;
  if (style === "fast_aggressive") return `${product}: scan, fix, launch.`;
  if (/premium|clean/.test(style)) return `${product}, polished from problem to payoff.`;
  return current.length > 8 ? `${current.replace(/[.!?]+$/, "")} - faster, cleaner, ready.` : `${product} in seconds.`;
}

function shortenCaptionText(caption: string) {
  const clean = caption.replace(/\s+/g, " ").trim();
  if (clean.length <= 72) return clean;
  const words = clean.split(" ");
  const first = words.slice(0, 8).join(" ");
  const second = words.slice(8, 15).join(" ");
  return second ? `${first}\n${second}` : first;
}

function hashTiny(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) hash = ((hash << 5) - hash + value.charCodeAt(index)) | 0;
  return Math.abs(hash).toString(16).slice(0, 6);
}

function formatTimestamp(seconds: number) {
  const value = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(value / 60);
  const remainder = Math.floor(value % 60);
  const frames = Math.round((value - Math.floor(value)) * 100);
  return `${minutes}:${String(remainder).padStart(2, "0")}.${String(frames).padStart(2, "0")}`;
}

function beginnerRequestFromForm(form: BeginnerFormState): BeginnerAutoTemplateRequest {
  const prompt = form.quickPrompt.trim();
  const durationFromPrompt = parseDurationFromPrompt(prompt);
  const promptFeatures = featuresFromPrompt(prompt);
  const detectedProduct = productNameFromPrompt(prompt);
  const customProduct = form.productName.trim() && form.productName !== defaultBeginnerForm.productName;
  const customGoal = form.goal.trim() && form.goal !== defaultBeginnerForm.goal;
  const customFeatures = form.keyFeatures.trim() && form.keyFeatures !== defaultBeginnerForm.keyFeatures;
  const customVibe = form.vibe.trim() && form.vibe !== defaultBeginnerForm.vibe;
  return {
    mediaFile: form.mediaFile,
    imageFolder: form.imageFolder,
    assetFolder: form.assetFolder,
    musicPath: form.musicPath,
    logoPath: form.logoPath,
    template: form.template,
    targetPlatform: form.targetPlatform,
    productName: customProduct ? form.productName.trim() : detectedProduct || form.productName.trim() || "Untitled Product",
    goal: customGoal ? form.goal.trim() : prompt || form.goal.trim() || "Create a polished product video.",
    keyFeatures: customFeatures ? splitLines(form.keyFeatures) : promptFeatures.length ? promptFeatures : splitLines(form.keyFeatures),
    vibe: customVibe ? form.vibe.trim() : vibeFromPrompt(prompt) || form.vibe.trim(),
    duration: form.duration || durationFromPrompt,
    quality: "preview",
    render: true,
    cache: true
  };
}

function beginnerSmartDefaults(template: BeginnerTemplateCard, targetPlatform: string): BeginnerSmartDefaults {
  const platform = targetPlatform.toLowerCase().replace("-", "_");
  const vertical = ["shorts", "youtube_shorts", "tiktok", "reels", "instagram", "instagram_reels"].includes(platform);
  const square = platform === "square";
  const resolution = vertical ? "1080x1920" : square ? "1080x1080" : "1920x1080";
  const fps = square ? 30 : 60;
  const exportPreset = vertical ? (platform === "tiktok" ? "tiktok_reels" : "shorts") : square ? "square" : "youtube_1080p";
  const lower = `${template.pacing} ${template.captionStyle}`.toLowerCase();
  const aggressive = /fast|gaming|trend|hype|aggressive/.test(lower);
  const cinematic = /cinematic|premium|trailer|showcase/.test(lower);
  return {
    aspectRatio: vertical ? "9:16" : square ? "1:1" : "16:9",
    resolution,
    fps,
    exportPreset,
    pacing: template.pacing,
    captionSize: vertical ? 64 : square ? 54 : 46,
    transitionIntensity: aggressive ? 0.75 : cinematic ? 0.55 : 0.35,
    audioNormalization: vertical ? "-14 LUFS" : "-16 LUFS"
  };
}

function templateQuickDefaults(templateKey: string, platform: string) {
  const vertical = ["shorts", "tiktok", "instagram_reels"].includes(platform);
  const defaults: Record<string, { duration: number; vibe: string }> = {
    premium_product_showcase: { duration: 30, vibe: "premium cinematic" },
    youtube_short: { duration: 30, vibe: "fast caption-heavy" },
    tiktok_reels_edit: { duration: 24, vibe: "punchy trend-style" },
    software_demo: { duration: 45, vibe: "clear polished walkthrough" },
    cybersecurity_tool_showcase: { duration: 35, vibe: "premium red black cybersecurity" },
    gaming_montage: { duration: 25, vibe: "high-energy gaming" },
    tutorial_walkthrough: { duration: 60, vibe: "calm tutorial" },
    minimal_saas_promo: { duration: 30, vibe: "minimal clean SaaS" },
    cinematic_trailer: { duration: 40, vibe: "cinematic trailer" },
    before_after_reveal: { duration: 30, vibe: "before after reveal" }
  };
  return defaults[templateKey] || { duration: vertical ? 30 : 45, vibe: "clean cinematic" };
}

function nextBeginnerTemplate(templates: BeginnerTemplateCard[], currentKey: string) {
  const index = Math.max(0, templates.findIndex((item) => item.key === currentKey));
  return templates[(index + 1) % templates.length] || templates[0];
}

function splitLines(value: string) {
  return value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean).slice(0, 8);
}

function parseDurationFromPrompt(prompt: string) {
  const match = prompt.match(/(?:under|about|around|for)?\s*(\d{1,3})\s*(?:second|sec|s)\b/i);
  if (!match) return null;
  const value = Number(match[1]);
  if (!Number.isFinite(value)) return null;
  return Math.max(8, Math.min(90, value));
}

function productNameFromPrompt(prompt: string) {
  const match = prompt.match(/\b(?:for|about)\s+(?:my|the)?\s*([^.,\n]+?)(?:\s+(?:that|with|and|in|under)\b|[.,\n]|$)/i);
  return match?.[1]?.trim() || "";
}

function vibeFromPrompt(prompt: string) {
  const lower = prompt.toLowerCase();
  const parts = [];
  if (lower.includes("blue") && lower.includes("black")) parts.push("blue black");
  if (lower.includes("red") && lower.includes("black")) parts.push("red black");
  if (lower.includes("cinematic")) parts.push("cinematic");
  if (lower.includes("premium")) parts.push("premium");
  if (lower.includes("minimal")) parts.push("minimal");
  if (lower.includes("gaming")) parts.push("gaming");
  return parts.join(" ") || "clean cinematic";
}

function featuresFromPrompt(prompt: string) {
  const afterShow = prompt.split(/\b(?:show|features?|scans?|includes?)\b/i).slice(1).join(" ");
  const source = afterShow || prompt;
  return source
    .replace(/\b(make|create|under|seconds?|cinematic|premium|video|short)\b/gi, "")
    .split(/[,.;&\n]/)
    .map((part) => part.trim())
    .filter((part) => part.length > 3)
    .slice(0, 6);
}

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatEta(seconds?: number) {
  if (!Number.isFinite(Number(seconds))) return "-";
  const value = Math.max(0, Number(seconds));
  if (value < 60) return `${Math.round(value)}s`;
  return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
}

function deliveryPlatformsForPreset(preset: string) {
  if (preset === "shorts") return ["youtube_shorts"];
  if (preset === "tiktok_reels") return ["tiktok"];
  if (preset === "instagram_reels") return ["instagram_reels"];
  if (preset === "discord_720p") return ["discord"];
  if (preset === "high_quality_archive" || preset === "cinematic_4k") return ["high_quality_archive"];
  return ["youtube_landscape"];
}

function packageTitleForProject(project: ProjectData) {
  const metadata = project.metadata || {};
  const content = metadata.contentGenerator as Record<string, unknown> | undefined;
  const brief = content?.contentBrief as Record<string, unknown> | undefined;
  return String(brief?.productName || metadata.productName || metadata.title || "Auto Video");
}

function reviewFromProjectText(text: string, data: Record<string, unknown>, planPath: string | null, reasoning: string): GenerationReviewState {
  const parsedProject = parseProject(text).data;
  if (!parsedProject) return readGenerationReview(data, planPath);
  const projectReview = projectToReviewState(parsedProject, planPath, reasoning);
  const existingReview = readGenerationReview(data, planPath);
  return {
    ...projectReview,
    hook: existingReview.hook || projectReview.hook,
    style: existingReview.style || projectReview.style,
    tone: existingReview.tone || projectReview.tone,
    duration: existingReview.duration || projectReview.duration,
    readyForFinalRender: existingReview.readyForFinalRender,
    unresolved: existingReview.unresolved.length ? existingReview.unresolved : projectReview.unresolved,
    warnings: existingReview.warnings.length ? existingReview.warnings : projectReview.warnings,
    scenes: existingReview.scenes.length ? existingReview.scenes : projectReview.scenes,
    reasoning: existingReview.reasoning || reasoning
  };
}

function projectToReviewState(project: ProjectData, planPath: string | null, reasoning: string): GenerationReviewState {
  const scenes = project.timeline || [];
  const metadata = project.metadata || {};
  const beginner = metadata.beginnerAutoTemplate as Record<string, unknown> | undefined;
  const beginnerTemplate = beginner?.template as Record<string, unknown> | undefined;
  return {
    planPath,
    hook: sceneCaptionText(scenes[0] as SceneData) || firstTextLayerValue(project) || "Opening hook",
    style: String(project.stylePreset || metadata.stylePreset || beginner?.desiredVibe || beginnerTemplate?.name || "Auto style"),
    tone: String(metadata.tone || "creator-friendly"),
    duration: totalTimelineDuration(project),
    readyForFinalRender: false,
    unresolved: scenes.map((scene) => scene.id).filter(Boolean).slice(0, 8),
    warnings: [],
    scenes: scenes.slice(0, 8).map((scene, index) => ({
      key: scene.id || `scene_${index + 1}`,
      label: scene.id || `Scene ${index + 1}`,
      caption: sceneCaptionText(scene as SceneData) || undefined,
      status: "needs_review"
    })),
    reasoning
  };
}

function buildAiPlanDisplay(plan: PendingAiPlan, project: ProjectData) {
  const metadata = project.metadata || {};
  const beginner = metadata.beginnerAutoTemplate as Record<string, unknown> | undefined;
  const beginnerTemplate = beginner?.template as Record<string, unknown> | undefined;
  const settings = project.project || {};
  const scenes = project.timeline || [];
  const duration = totalTimelineDuration(project);
  const transitionTypes = [...new Set(scenes.map((scene) => String(scene.transitionOut?.type || "cut")).filter(Boolean))];
  const audioTracks = project.audio || [];
  const captionStyle = String(beginnerTemplate?.captionStyle || inferCaptionStyle(project));
  const style = plan.review.style || String(project.stylePreset || beginner?.desiredVibe || "clean cinematic");
  const targetPlatform = String(project.exportPreset || settings.exportPreset || beginner?.targetPlatform || plan.preset);
  const explanation = simplePlanExplanation(plan);
  const summary = [
    { label: "Target platform", value: targetPlatform },
    { label: "Final duration", value: `${duration.toFixed(1)}s` },
    { label: "Style", value: style },
    { label: "Caption style", value: captionStyle },
    { label: "Music / sound", value: audioTracks.length ? `${audioTracks.length} audio track(s), normalized mix` : "No music selected yet" },
    { label: "B-roll / overlays", value: overlaySummary(project) },
    { label: "Transitions", value: transitionTypes.join(", ") || "cut" },
    { label: "Export settings", value: `${settings.width || "?"}x${settings.height || "?"} / ${settings.fps || "?"}fps / ${targetPlatform}` }
  ];
  const sceneDisplays = scenes.slice(0, 12).map((scene, index) => {
    const layers = scene.layers || [];
    const mediaLayer = layers.find((layer) => layer.type === "video" || layer.type === "image");
    const animation = mediaLayer?.animation as Record<string, unknown> | undefined;
    const caption = sceneCaptionText(scene as SceneData);
    return {
      id: scene.id || `scene_${index + 1}`,
      name: scene.id || `Scene ${index + 1}`,
      timeRange: `${formatTimestamp(Number(scene.start || 0))} - ${formatTimestamp(Number(scene.start || 0) + Number(scene.duration || 0))}`,
      purpose: inferScenePurpose(scene as SceneData, index, scenes.length),
      caption: caption || "No caption planned",
      effect: String(animation?.in || scene.postProcessing ? describeSceneEffect(scene as SceneData) : "clean cut"),
      transition: String(scene.transitionOut?.type || (index === scenes.length - 1 ? "fade out" : "cut")),
      notes: describeSceneNotes(scene as SceneData)
    };
  });
  const highlights = sceneDisplays.slice(0, 5).map((scene) => `${scene.name}: ${scene.purpose}`);
  const cuts = sceneDisplays.map((scene) => `${scene.timeRange} - ${scene.name}`).slice(0, 6);
  return {
    explanation,
    reasoning: plan.review.reasoning || "The AI organized the edit into a hook, supporting moments, and a payoff so you can review the story before applying it.",
    summary,
    highlights: highlights.length ? highlights : ["AI found the most useful moments from the imported media."],
    cuts: cuts.length ? cuts : ["No timeline cuts have been applied yet."],
    scenes: sceneDisplays
  };
}

function simplePlanExplanation(plan: PendingAiPlan) {
  const sceneCount = plan.review.scenes.length || parseProject(plan.text).data?.timeline?.length || 0;
  const duration = plan.review.duration ? `${plan.review.duration.toFixed(1)} seconds` : "the requested length";
  const hook = plan.review.hook ? ` It opens with: "${plan.review.hook}".` : "";
  return `This plan creates a ${plan.preset} edit with ${sceneCount} scene(s), ${duration}, ${plan.review.style || "a polished style"}, readable captions, planned transitions, and export settings ready for review.${hook}`;
}

function inferCaptionStyle(project: ProjectData) {
  const hasCaption = (project.timeline || []).some((scene) => (scene.layers || []).some((layer) => layer.type === "caption" || layer.type === "captions"));
  if (hasCaption) return "Readable burned-in captions";
  const hasText = (project.timeline || []).some((scene) => (scene.layers || []).some((layer) => layer.type === "text"));
  return hasText ? "Title cards and text overlays" : "No captions planned";
}

function overlaySummary(project: ProjectData) {
  let text = 0;
  let image = 0;
  for (const scene of project.timeline || []) {
    for (const layer of scene.layers || []) {
      if (layer.type === "text" || layer.type === "lower_third") text += 1;
      if (layer.type === "image") image += 1;
    }
  }
  const parts = [];
  if (text) parts.push(`${text} text/title overlay(s)`);
  if (image) parts.push(`${image} image/logo overlay(s)`);
  return parts.join(", ") || "No extra overlays";
}

function inferScenePurpose(scene: SceneData, index: number, total: number) {
  const caption = sceneCaptionText(scene).toLowerCase();
  if (index === 0) return "Hook the viewer quickly";
  if (index === total - 1) return "End with CTA or closing payoff";
  if (/problem|issue|blocked|missing|error|before/.test(caption)) return "Show the problem";
  if (/result|fixed|success|after|ready|done/.test(caption)) return "Show the result";
  if (/scan|detect|feature|dashboard|step/.test(caption)) return "Highlight the feature";
  return "Move the story forward";
}

function describeSceneEffect(scene: SceneData) {
  const mediaLayer = (scene.layers || []).find((layer) => layer.type === "video" || layer.type === "image");
  const animation = mediaLayer?.animation as Record<string, unknown> | undefined;
  const effects = [];
  if (animation?.in) effects.push(String(animation.in));
  if (mediaLayer?.scale && Number(mediaLayer.scale) > 1) effects.push("zoom");
  if (scene.postProcessing) effects.push("color grade");
  return effects.join(", ") || "clean cut";
}

function describeSceneNotes(scene: SceneData) {
  const layerTypes = new Set((scene.layers || []).map((layer) => layer.type));
  const notes = [];
  if (layerTypes.has("video")) notes.push("uses source footage");
  if (layerTypes.has("image")) notes.push("uses visual overlay");
  if (layerTypes.has("text")) notes.push("text is visible");
  if (Number(scene.duration || 0) < 2) notes.push("fast pacing");
  return notes.join(", ") || "simple scene";
}

function readGenerationReview(data: Record<string, unknown>, planPath: string | null): GenerationReviewState {
  const review = data.review && typeof data.review === "object" ? data.review as Record<string, unknown> : {};
  const reasoning = typeof data.reasoning === "string" ? data.reasoning : undefined;
  return reviewDataToState(review, planPath, reasoning);
}

function reviewDataToState(review: Record<string, unknown>, planPath: string | null, reasoning?: string): GenerationReviewState {
  const summary = review.summary && typeof review.summary === "object" ? review.summary as Record<string, unknown> : {};
  const readiness = review.readiness && typeof review.readiness === "object" ? review.readiness as Record<string, unknown> : {};
  const sections = review.sections && typeof review.sections === "object" ? review.sections as Record<string, unknown> : {};
  const sceneSections = Array.isArray(sections.scenes) ? sections.scenes as Array<Record<string, unknown>> : [];
  const unresolved = Array.isArray(readiness.unresolvedSections) ? readiness.unresolvedSections.map(String) : [];
  const assetsWarnings = Array.isArray(summary.warnings) ? summary.warnings.map(String) : [];
  return {
    planPath,
    hook: String(summary.hook || ""),
    style: String(summary.stylePreset || ""),
    tone: String(summary.tone || ""),
    duration: typeof summary.estimatedDuration === "number" ? summary.estimatedDuration : null,
    readyForFinalRender: Boolean(readiness.readyForFinalRender),
    unresolved,
    warnings: assetsWarnings,
    scenes: sceneSections.slice(0, 8).map((scene) => ({
      key: String(scene.key || ""),
      label: String(scene.label || ""),
      caption: typeof scene.caption === "string" ? scene.caption : undefined,
      status: typeof scene.status === "string" ? scene.status : undefined
    })),
    reasoning
  };
}

function AiPanel({
  prompt,
  setPrompt,
  contentMode,
  setContentMode,
  contentTone,
  setContentTone,
  generationReview,
  generationLocks,
  notes,
  onGenerate,
  onYouTubeShort,
  onContentGenerate,
  onAutonomousPipeline,
  onContentRegenerate,
  onContentApprove,
  onContentLock,
  onExplain,
  onRepair,
  onDirector,
  onSuggestTransitions,
  onCaptions,
  onAddScene
}: {
  prompt: string;
  setPrompt: (value: string) => void;
  contentMode: string;
  setContentMode: (value: string) => void;
  contentTone: string;
  setContentTone: (value: string) => void;
  generationReview: GenerationReviewState | null;
  generationLocks: string[];
  notes: string;
  onGenerate: () => void;
  onYouTubeShort: () => void;
  onContentGenerate: () => void;
  onAutonomousPipeline: () => void;
  onContentRegenerate: (target: string) => void;
  onContentApprove: (section?: string, status?: string) => void;
  onContentLock: (section: string) => void;
  onExplain: () => void;
  onRepair: () => void;
  onDirector: () => void;
  onSuggestTransitions: () => void;
  onCaptions: () => void;
  onAddScene: () => void;
}) {
  return (
    <section className="panel ai-panel">
      <h2><Bot size={16} /> AI Panel</h2>
      <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
      <div className="ai-controls">
        <label>
          Mode
          <select value={contentMode} onChange={(event) => setContentMode(event.target.value)}>
            <option value="youtube_shorts">YouTube Shorts</option>
            <option value="tiktok">TikTok</option>
            <option value="product_showcase">Product Showcase</option>
            <option value="tutorial">Tutorial</option>
            <option value="promo_ad">Promo/Ad</option>
          </select>
        </label>
        <label>
          Tone
          <select value={contentTone} onChange={(event) => setContentTone(event.target.value)}>
            <option value="cinematic">Cinematic</option>
            <option value="minimal">Minimal</option>
            <option value="aggressive">Aggressive</option>
            <option value="clean">Clean</option>
          </select>
        </label>
      </div>
      <div className="button-grid">
        <button onClick={onAutonomousPipeline}><Sparkles size={15} /> Autonomous</button>
        <button onClick={onContentGenerate}><ListVideo size={15} /> Content Mode</button>
        <button onClick={onGenerate}><Sparkles size={15} /> Prompt JSON</button>
        <button onClick={onYouTubeShort}><Video size={15} /> YouTube Short</button>
        <button onClick={onDirector}><Bot size={15} /> Director</button>
        <button onClick={onExplain}><FileJson size={15} /> Explain</button>
        <button onClick={onRepair}><Wand2 size={15} /> Repair</button>
        <button onClick={onSuggestTransitions}><RefreshCw size={15} /> Transitions</button>
        <button onClick={onCaptions}><Captions size={15} /> Captions</button>
        <button onClick={onAddScene}><Plus size={15} /> Scene</button>
      </div>
      {generationReview && (
        <div className="generation-review">
          <div className="review-header">
            <strong>Generation Review</strong>
            <span className={generationReview.readyForFinalRender ? "status-pill ok" : "status-pill warn"}>
              {generationReview.readyForFinalRender ? "approved" : `${generationReview.unresolved.length} open`}
            </span>
          </div>
          <p>{generationReview.hook}</p>
          <div className="review-meta">
            <span>{generationReview.style}</span>
            <span>{generationReview.tone}</span>
            <span>{generationReview.duration ? `${generationReview.duration}s` : "duration pending"}</span>
          </div>
          <div className="review-scenes">
            {generationReview.scenes.map((scene) => (
              <button key={scene.key} title={scene.caption || scene.label} onClick={() => onContentLock(scene.key)}>
                <span>{scene.label}</span>
                <small>{scene.status || "needs_review"}</small>
              </button>
            ))}
          </div>
          <div className="review-actions">
            <button onClick={() => onContentApprove("all", "approved")}><CheckCircle2 size={14} /> Approve All</button>
            <button onClick={() => onContentRegenerate("hook")}><RefreshCw size={14} /> Hook</button>
            <button onClick={() => onContentRegenerate("captions")}><Captions size={14} /> Captions</button>
            <button onClick={() => onContentRegenerate("scenes")}><ListVideo size={14} /> Scenes</button>
            <button onClick={() => onContentRegenerate("style")}><Sparkles size={14} /> Style</button>
          </div>
          {generationLocks.length > 0 && <small>Locked: {generationLocks.join(", ")}</small>}
          {generationReview.warnings.length > 0 && <small>Warnings: {generationReview.warnings.slice(0, 2).join(" | ")}</small>}
        </div>
      )}
      <details className="mini-details ai-advanced-reasoning">
        <summary>Advanced: AI reasoning / logs</summary>
        <pre className="mini-pre">{notes || "Project explanations and suggestions appear here."}</pre>
      </details>
    </section>
  );
}

function RenderPanel({
  preset,
  setPreset,
  exportFormat,
  setExportFormat,
  quality,
  setQuality,
  cache,
  setCache,
  resume,
  setResume,
  gpu,
  setGpu,
  logs,
  renderQueueItems,
  project,
  finalPreflight,
  onPreflight,
  onRepairPreflight,
  onPreview,
  onFinal,
  onPauseQueue,
  onResumeQueue,
  onCancelJob,
  onRetryJob,
  onOpenOutput
}: {
  preset: string;
  setPreset: (value: string) => void;
  exportFormat: "mp4" | "mov" | "mkv" | "webm" | "gif";
  setExportFormat: (value: "mp4" | "mov" | "mkv" | "webm" | "gif") => void;
  quality: "preview" | "final";
  setQuality: (value: "preview" | "final") => void;
  cache: boolean;
  setCache: (value: boolean) => void;
  resume: boolean;
  setResume: (value: boolean) => void;
  gpu: boolean;
  setGpu: (value: boolean) => void;
  logs: string[];
  renderQueueItems: RenderQueueItem[];
  project?: ProjectData | null;
  finalPreflight: FinalPreflightReport | null;
  onPreflight: () => void;
  onRepairPreflight: (mode: string, issueId?: string | null) => void;
  onPreview: () => void;
  onFinal: () => void;
  onPauseQueue: () => void;
  onResumeQueue: () => void;
  onCancelJob: (runId: string) => void;
  onRetryJob: (runId: string) => void;
  onOpenOutput: () => void;
}) {
  const activeQueueJob = renderQueueItems.find((item) => item.status === "running") || renderQueueItems.find((item) => item.status === "queued") || renderQueueItems[0];
  const progress = activeQueueJob ? Number(activeQueueJob.progressPercent || 0) : logs.some((line) => line.includes("Export complete")) ? 100 : Math.min(95, logs.length * 7);
  const issues = finalPreflight?.issues || [];
  const scores = finalPreflight?.scores || {};
  const summary = finalPreflight?.summary || {};
  const resolution = summary.resolution as Record<string, unknown> | undefined;
  const [codec, setCodec] = useState("h264");
  const [resolutionSetting, setResolutionSetting] = useState("1080p");
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [fpsSetting, setFpsSetting] = useState(60);
  const [bitrateMode, setBitrateMode] = useState("auto");
  const [customBitrate, setCustomBitrate] = useState("12M");
  const [audioQuality, setAudioQuality] = useState("high");
  const [burnCaptions, setBurnCaptions] = useState(true);
  const [selectedPlatformKey, setSelectedPlatformKey] = useState("youtube");
  const platformPresets = [
    { key: "shorts", label: "YouTube Shorts", preset: "shorts", aspect: "9:16", resolution: "1080p", fps: 60, note: "Vertical 1080x1920, caption-safe." },
    { key: "tiktok", label: "TikTok", preset: "tiktok_reels", aspect: "9:16", resolution: "1080p", fps: 60, note: "Fast vertical social export." },
    { key: "instagram", label: "Instagram Reels", preset: "instagram_reels", aspect: "9:16", resolution: "1080p", fps: 60, note: "Reels-safe 1080x1920." },
    { key: "youtube", label: "YouTube normal video", preset: "youtube_1080p", aspect: "16:9", resolution: "1080p", fps: 60, note: "Standard landscape upload." },
    { key: "x", label: "Twitter/X", preset: "youtube_1080p", aspect: "16:9", resolution: "1080p", fps: 30, note: "MP4 landscape, social-safe bitrate." },
    { key: "facebook", label: "Facebook", preset: "youtube_1080p", aspect: "16:9", resolution: "1080p", fps: 30, note: "Broad compatibility." },
    { key: "custom", label: "Custom", preset, aspect: aspectRatio, resolution: resolutionSetting, fps: fpsSetting, note: "Use the manual settings below." }
  ];
  const selectedPlatform = platformPresets.find((item) => item.key === selectedPlatformKey) || platformPresets[6];
  const exportWarnings = project ? exportReadinessWarnings(project, finalPreflight, { resolutionSetting, aspectRatio, burnCaptions }) : [];
  const activeJob = activeQueueJob && ["running", "queued"].includes(activeQueueJob.status) ? activeQueueJob : null;

  function applyPlatformPreset(item: typeof platformPresets[number]) {
    setSelectedPlatformKey(item.key);
    setPreset(item.preset);
    setAspectRatio(item.aspect);
    setResolutionSetting(item.resolution);
    setFpsSetting(item.fps);
    setExportFormat("mp4");
    setQuality("final");
  }

  function applyResolution(value: string) {
    setSelectedPlatformKey("custom");
    setResolutionSetting(value);
    if (value === "720p") setPreset("discord_720p");
    if (value === "4k") setPreset("cinematic_4k");
    if (value === "1080p" && aspectRatio === "1:1") setPreset("square");
    if (value === "1080p" && aspectRatio === "9:16") setPreset(preset === "instagram_reels" ? "instagram_reels" : "shorts");
    if (value === "1080p" && aspectRatio === "16:9") setPreset("youtube_1080p");
    if (value === "1440p") setPreset("high_quality_archive");
  }

  function applyAspect(value: string) {
    setSelectedPlatformKey("custom");
    setAspectRatio(value);
    if (value === "9:16") setPreset(preset === "tiktok_reels" || preset === "instagram_reels" ? preset : "shorts");
    if (value === "1:1") setPreset("square");
    if (value === "16:9" || value === "4:5") setPreset(resolutionSetting === "720p" ? "discord_720p" : "youtube_1080p");
  }

  function finalExport() {
    if (!finalPreflight) {
      onPreflight();
      return;
    }
    onFinal();
  }

  return (
    <section className="panel render-panel export-workflow-panel">
      <div className="export-header-row">
        <div>
          <span className="eyebrow">Export</span>
          <h2><MonitorPlay size={16} /> Export Workflow</h2>
          <p className="muted">Presets and checks wrap the existing FFmpeg exporter. JSON remains the source of truth.</p>
        </div>
        <span className={finalPreflight?.ready ? "status-pill ok" : finalPreflight ? "status-pill warn" : "status-pill"}>{finalPreflight ? (finalPreflight.ready ? "preflight ready" : "needs fixes") : "preflight not run"}</span>
      </div>

      <div className="platform-preset-grid">
        {platformPresets.map((item) => (
          <button key={item.key} className={selectedPlatform?.key === item.key ? "active" : ""} onClick={() => applyPlatformPreset(item)}>
            <strong>{item.label}</strong>
            <span>{item.aspect} / {item.resolution} / {item.fps}fps</span>
            <small>{item.note}</small>
          </button>
        ))}
      </div>

      <div className="export-settings-grid">
        <label>
          Format
          <select value={exportFormat} onChange={(event) => setExportFormat(event.target.value as "mp4" | "mov" | "mkv" | "webm" | "gif")}>
            <option value="mp4">MP4</option>
            <option value="mov">MOV</option>
            <option value="webm">WebM</option>
          </select>
        </label>
        <label>
          Codec
          <select value={codec} onChange={(event) => setCodec(event.target.value)}>
            <option value="h264">H.264</option>
            <option value="h265" disabled>H.265 / HEVC if supported</option>
            <option value="av1" disabled>AV1 if supported</option>
          </select>
        </label>
        <label>
          Resolution
          <select value={resolutionSetting} onChange={(event) => applyResolution(event.target.value)}>
            <option value="720p">720p</option>
            <option value="1080p">1080p</option>
            <option value="1440p">1440p</option>
            <option value="4k">4K</option>
          </select>
        </label>
        <label>
          Aspect ratio
          <select value={aspectRatio} onChange={(event) => applyAspect(event.target.value)}>
            <option value="16:9">16:9</option>
            <option value="9:16">9:16</option>
            <option value="1:1">1:1</option>
            <option value="4:5">4:5</option>
          </select>
        </label>
        <label>
          FPS
          <select value={fpsSetting} onChange={(event) => setFpsSetting(Number(event.target.value))}>
            <option value={24}>24</option>
            <option value={30}>30</option>
            <option value={60}>60</option>
          </select>
        </label>
        <label>
          Bitrate
          <select value={bitrateMode} onChange={(event) => setBitrateMode(event.target.value)}>
            <option value="auto">Auto</option>
            <option value="custom">Custom</option>
          </select>
        </label>
        {bitrateMode === "custom" && (
          <label>
            Custom bitrate
            <input value={customBitrate} onChange={(event) => setCustomBitrate(event.target.value)} placeholder="12M" />
          </label>
        )}
        <label>
          Audio quality
          <select value={audioQuality} onChange={(event) => setAudioQuality(event.target.value)}>
            <option value="standard">Standard AAC</option>
            <option value="high">High AAC</option>
            <option value="archive">Archive quality</option>
          </select>
        </label>
        <label className="check-control">
          <input type="checkbox" checked={burnCaptions} onChange={(event) => setBurnCaptions(event.target.checked)} />
          Burn captions into video
        </label>
      </div>

      <div className="export-engine-note">
        <span>engine preset <strong>{preset}</strong></span>
        <span>codec path <strong>{codec === "h264" ? "H.264 via current FFmpeg renderer" : "requires supported encoder"}</strong></span>
        <span>bitrate <strong>{bitrateMode === "auto" ? "preset auto" : customBitrate}</strong></span>
        <span>captions <strong>{burnCaptions ? "burned-in timeline text/captions" : "external/subtitle workflow"}</strong></span>
      </div>

      <div className="export-preflight-strip">
        <div>
          <strong>Before export</strong>
          <span>{exportWarnings.length ? `${exportWarnings.length} item(s) need review` : "No local warnings detected"}</span>
        </div>
        <div className="button-grid compact">
          <button onClick={onPreflight}><CheckCircle2 size={15} /> Run Preflight</button>
          <button onClick={onPreview}><Play size={15} /> Preview Render</button>
          <button onClick={finalExport}><MonitorPlay size={15} /> {finalPreflight ? "Export Final" : "Run Preflight First"}</button>
          <button onClick={onOpenOutput}><FolderOpen size={15} /> Open Output</button>
        </div>
      </div>

      {exportWarnings.length > 0 && (
        <div className="export-warning-list">
          {exportWarnings.slice(0, 8).map((warning) => (
            <div className={`preflight-issue ${warning.severity}`} key={warning.id}>
              <strong>{warning.title}</strong>
              <span>{warning.message}</span>
              <small>{warning.suggestion}</small>
            </div>
          ))}
        </div>
      )}

      <div className="toggles">
        <label><input type="checkbox" checked={cache} onChange={(event) => setCache(event.target.checked)} /> cache</label>
        <label><input type="checkbox" checked={resume} onChange={(event) => setResume(event.target.checked)} /> resume failed render</label>
        <label><input type="checkbox" checked={gpu} onChange={(event) => setGpu(event.target.checked)} /> GPU acceleration</label>
        <label>
          Quality
          <select value={quality} onChange={(event) => setQuality(event.target.value as "preview" | "final")}>
            <option value="preview">preview</option>
            <option value="final">final</option>
          </select>
        </label>
      </div>

      <div className="render-queue-mini">
        <div className="review-header">
          <strong>Export Popup / Queue</strong>
          <span className="muted">{renderQueueItems.length ? `${renderQueueItems.length} job(s)` : "idle"}</span>
        </div>
        <div className="button-grid compact">
          <button onClick={onPauseQueue}><Pause size={14} /> Pause</button>
          <button onClick={onResumeQueue}><Play size={14} /> Resume</button>
        </div>
        <div className="list compact-list">
          {renderQueueItems.length === 0 && <span className="muted">No final exports queued.</span>}
          {renderQueueItems.slice(0, 4).map((job) => (
            <div className="queue-row expanded" key={job.runId}>
              <div>
                <strong>{job.label}</strong>
                <small>stage {job.currentScene || job.status} | ETA {formatEta(job.estimatedRemainingSeconds)}</small>
                <small>progress {Math.round(Number(job.progressPercent || 0))}% | {job.outputPath}</small>
                {job.packagePath && <small>package: {job.packagePath}</small>}
                {job.packageError && <small className="error">{job.packageError}</small>}
              </div>
              <span className={job.status}>{Math.round(Number(job.progressPercent || 0))}%</span>
              {job.packageStatus && <span className={job.packageStatus === "completed" ? "status-pill ok" : "status-pill warn"}>{job.packageStatus}</span>}
              {job.status === "running" || job.status === "queued" ? <button onClick={() => onCancelJob(job.runId)}>Cancel</button> : null}
              {job.status === "failed" || job.status === "canceled" ? <button onClick={() => onRetryJob(job.runId)}>Retry</button> : null}
            </div>
          ))}
        </div>
      </div>
      {finalPreflight && (
        <div className="preflight-panel">
          <div className="review-header">
            <strong>Final Preflight</strong>
            <span className={finalPreflight.ready ? "status-pill ok" : "status-pill warn"}>
              {finalPreflight.ready ? "ready" : "blocked"}
            </span>
          </div>
          <div className="metric-grid">
            <span>score <strong>{String(finalPreflight.exportReadinessScore ?? "-")}</strong></span>
            <span>pacing <strong>{String(scores.pacing ?? "-")}</strong></span>
            <span>readability <strong>{String(scores.readability ?? "-")}</strong></span>
            <span>audio <strong>{String(scores.audio ?? "-")}</strong></span>
            <span>brand <strong>{String(scores.brandConsistency ?? "-")}</strong></span>
            <span>technical <strong>{String(scores.technicalReadiness ?? "-")}</strong></span>
          </div>
          <div className="mini-summary">
            <span>{String(summary.platform || preset)}</span>
            <span>{String(resolution?.width || "?")}x{String(resolution?.height || "?")}</span>
            <span>{String(summary.duration ?? "?")}s</span>
            <span>{String(summary.fps ?? "?")}fps</span>
            <span>{String(summary.codec || exportFormat)}</span>
            <span>{String(summary.bitrate || "bitrate auto")}</span>
            <span>captions {String(Boolean(summary.captionsIncluded))}</span>
            <span>thumbnail {String(Boolean(summary.thumbnailIncluded))}</span>
            <span>warnings {String(summary.warningsRemaining ?? finalPreflight.warningsRemaining ?? 0)}</span>
          </div>
          <p className="muted">Suggested repairs are applied only after you approve the individual issue below. No bulk auto-fix runs from this panel.</p>
          <div className="preflight-issues">
            {issues.slice(0, 6).map((issue) => (
              <div className={`preflight-issue ${issue.severity}`} key={issue.id}>
                <strong>{issue.category.replace(/_/g, " ")}</strong>
                <span>{issue.message}</span>
                <small>{issue.suggestion || "Review before export."}</small>
                <div className="button-grid compact">
                  {issue.safeAutoFix && !issue.accepted && <button onClick={() => onRepairPreflight("selected", issue.id)}><Wand2 size={14} /> Approve fix</button>}
                  {!issue.accepted && <button onClick={() => onRepairPreflight("ignore", issue.id)}><CheckCircle2 size={14} /> Accept as intentional</button>}
                  {issue.accepted && <span className="status-pill ok">accepted</span>}
                </div>
              </div>
            ))}
            {!issues.length && <p className="muted">Run preflight before final export.</p>}
          </div>
        </div>
      )}
      <div className="progress"><span style={{ width: `${progress}%` }} /></div>
      <pre className="logs">{logs.slice(-14).join("\n") || "Render logs will stream here."}</pre>
    </section>
  );
}

export default App;
