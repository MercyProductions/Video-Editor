import Editor, { OnMount } from "@monaco-editor/react";
import {
  Bot,
  Captions,
  CheckCircle2,
  ChevronDown,
  Clock,
  FileJson,
  FolderOpen,
  Image,
  LayoutTemplate,
  ListVideo,
  MonitorPlay,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Save,
  Scissors,
  Sparkles,
  Video,
  Wand2,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

type Tab = "beginner" | "json" | "timeline" | "preview" | "assets" | "director" | "storyboard" | "workflow" | "product";
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
type BeginnerTemplateCard = {
  key: string;
  name: string;
  aspectRatio: string;
  platform: string;
  pacing: string;
  captionStyle: string;
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
  theme: "graphite",
  autosave: true,
  autosaveIntervalSeconds: 45,
  previewTimeSeconds: 1,
  keyboardShortcuts: true
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
  const [uiMode, setUiMode] = useState<"beginner" | "advanced">("beginner");
  const [activeTab, setActiveTab] = useState<Tab>("beginner");
  const [status, setStatus] = useState("Ready");
  const [validation, setValidation] = useState<EngineResult | null>(null);
  const [assets, setAssets] = useState<AssetCheck[]>([]);
  const [prompt, setPrompt] = useState("Create a 20 second gaming montage with fast cuts, red black theme, captions, and bass drop transitions.");
  const [contentMode, setContentMode] = useState("youtube_shorts");
  const [contentTone, setContentTone] = useState("cinematic");
  const [generationReview, setGenerationReview] = useState<GenerationReviewState | null>(null);
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
  const [manifestReport, setManifestReport] = useState<Record<string, unknown> | null>(null);
  const [repurposeReport, setRepurposeReport] = useState<Record<string, unknown> | null>(null);
  const [postingPackageReport, setPostingPackageReport] = useState<Record<string, unknown> | null>(null);
  const [postExportReview, setPostExportReview] = useState<Record<string, unknown> | null>(null);
  const [postExportTemplate, setPostExportTemplate] = useState<Record<string, unknown> | null>(null);
  const [postExportVariants, setPostExportVariants] = useState<Record<string, unknown> | null>(null);
  const [postExportNote, setPostExportNote] = useState<Record<string, unknown> | null>(null);
  const [templatePacks, setTemplatePacks] = useState<TemplatePack[]>([]);
  const [recoveryPoints, setRecoveryPoints] = useState<RecoveryPoint[]>([]);
  const [socialTargets, setSocialTargets] = useState(["youtube_shorts", "tiktok", "instagram_reels", "youtube_landscape", "discord", "x_twitter"]);
  const [hardeningStatus, setHardeningStatus] = useState<HardeningStatus | null>(null);
  const [workflowDashboard, setWorkflowDashboard] = useState<Record<string, unknown> | null>(null);
  const [feedbackAnalysis, setFeedbackAnalysis] = useState<Record<string, unknown> | null>(null);
  const [feedbackReview, setFeedbackReview] = useState<Record<string, unknown> | null>(null);
  const [creatorIdentity, setCreatorIdentity] = useState<Record<string, unknown> | null>(null);
  const [evolutionReport, setEvolutionReport] = useState<Record<string, unknown> | null>(null);
  const [beginnerForm, setBeginnerForm] = useState<BeginnerFormState>(defaultBeginnerForm);
  const [beginnerSummary, setBeginnerSummary] = useState<Record<string, unknown> | null>(null);
  const [frictionReport, setFrictionReport] = useState<FrictionReport | null>(null);
  const [adaptiveMemory, setAdaptiveMemory] = useState<AdaptiveWorkflowMemory | null>(null);
  const [processing, setProcessing] = useState<ProcessingState>(idleProcessingState);
  const [activityFeed, setActivityFeed] = useState<ProcessingActivity[]>([]);
  const [processingCollapsed, setProcessingCollapsed] = useState(true);
  const [assistantDraft, setAssistantDraft] = useState("");
  const [assistantMessages, setAssistantMessages] = useState<CollaborationMessage[]>([]);
  const [proactiveMuted, setProactiveMuted] = useState(false);
  const [leftRailOpen, setLeftRailOpen] = useState(false);
  const [rightRailOpen, setRightRailOpen] = useState(false);
  const [backgroundImprovements, setBackgroundImprovements] = useState<BackgroundImprovement[]>([]);

  const parsed = useMemo(() => parseProject(projectText), [projectText]);
  const project = parsed.data;
  const proactiveAnalysis = useMemo(
    () => project ? analyzeProactiveAssistance(project, adaptiveMemory, renderQueueItems, preset, useCache) : emptyProactiveAnalysis,
    [project, adaptiveMemory, renderQueueItems, preset, useCache]
  );
  const monacoRef = useRef<MonacoInstance | null>(null);
  const latestProjectRef = useRef({ text: projectText, path: projectPath, preset });
  const lastActivityKeyRef = useRef("");

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
    window.ave.listPlugins().then(setPlugins).catch(() => setPlugins([]));
    window.ave.getSettings().then((value) => {
      setSettings(value);
      setPreviewTimeSeconds(value.previewTimeSeconds);
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
      window.ave.autosaveProject({ text: current.text, projectPath: current.path }).catch(() => undefined);
    }, Math.max(10, settings.autosaveIntervalSeconds) * 1000);
    return () => window.clearInterval(interval);
  }, [settings.autosave, settings.autosaveIntervalSeconds]);

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

  const updateProject = useCallback((data: ProjectData) => {
    setProjectText(formatProject(data));
  }, []);

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

  function beginProcessing(label: string, stage = "Starting", detail?: string) {
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
    if (activity) pushActivity(activity, kind, detail);
  }

  function finishProcessing(label: string, kind: ActivityKind = "success") {
    setProcessing((current) => ({
      ...current,
      isActive: false,
      currentStage: kind === "success" ? "Complete" : "Needs attention",
      activeTask: label,
      progress: kind === "success" ? 100 : current.progress,
      etaSeconds: kind === "success" ? 0 : current.etaSeconds,
      workers: current.workers.map((worker) => ({ ...worker, status: kind === "success" ? "complete" : worker.status }))
    }));
    if (kind !== "info") setProcessingCollapsed(true);
    pushActivity(label, kind);
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
  }

  async function saveProject() {
    const file = await window.ave.saveProject({ path: projectPath, text: projectText });
    setProjectPath(file.path);
    setStatus(`Saved ${file.name}`);
    setRecent(await window.ave.getRecentProjects());
  }

  async function saveAs() {
    const file = await window.ave.saveProjectAs({ text: projectText });
    if (!file) return;
    setProjectPath(file.path);
    setStatus(`Saved ${file.name}`);
    setRecent(await window.ave.getRecentProjects());
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
      setProjectText(result.text);
      setStatus("JSON repaired");
    } else {
      setStatus("Repair failed");
    }
  }

  async function createFromTemplate(template: string) {
    const result = await window.ave.createTemplate({ template });
    if (result.ok && result.text) {
      setProjectText(result.text);
      setProjectPath(null);
      setStatus(`Template loaded: ${templateLabels[template] || template}`);
      setUiMode("advanced");
      setActiveTab("json");
    } else {
      setStatus(result.stderr || result.stdout || "Template failed");
    }
  }

  async function generateBeginnerAutoVideo(renderQuality: "preview" | "final") {
    await productAction("Beginner Auto Video", async () => {
      const quick = beginnerRequestFromForm(beginnerForm);
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
        render: true,
        cache: true
      });
      if (result.ok && result.text) {
        const sceneCount = parseProject(result.text).data?.timeline?.length || 0;
        setProjectText(result.text);
        setProjectPath(result.path || null);
        setBeginnerSummary(result.data || null);
        const outputs = result.data?.outputs as Record<string, unknown> | undefined;
        const renderedVideo = typeof outputs?.renderedVideo === "string" ? outputs.renderedVideo : null;
        if (renderedVideo) setPreviewPath(renderedVideo);
        const presetValue = quick.targetPlatform === "youtube" ? "youtube_1080p" : quick.targetPlatform === "tiktok" ? "tiktok_reels" : quick.targetPlatform;
        setPreset(presetValue);
        void recordAdaptiveEvent({
          event: "beginner_auto_video",
          template: quick.template,
          targetPlatform: quick.targetPlatform,
          exportPreset: presetValue,
          duration: quick.duration,
          style: quick.vibe,
          pacing: selectedPacingForTemplate(quick.template),
          mediaPath: quick.mediaFile || quick.assetFolder || quick.imageFolder || null,
          prompt: beginnerForm.quickPrompt,
          note: renderQuality
        });
        setStatus(renderQuality === "final" ? "Beginner final video rendered" : "Beginner preview video rendered");
        updateProcessing({
          currentStage: "Auto video ready",
          activeTask: renderQuality === "final" ? "Final MP4 rendered" : "Preview rendered",
          progress: 100,
          currentScene: `${sceneCount} scenes generated`
        }, `Built ${sceneCount} auto-video scenes`, "success", renderedVideo || undefined);
        setUiMode("beginner");
        setActiveTab("beginner");
        setRecent(await window.ave.getRecentProjects());
      } else {
        setStatus(result.stderr || result.stdout || "Beginner Auto Video failed");
      }
    });
  }

  async function generateFromPrompt() {
    beginProcessing("Prompt JSON", "Generating project JSON", prompt);
    const result = await window.ave.aiGenerate({ prompt });
    if (result.ok && result.text) {
      setProjectText(result.text);
      setProjectPath(null);
      setStatus("AI project generated");
      setUiMode("advanced");
      setActiveTab("timeline");
      finishProcessing("Prompt JSON generated", "success");
    } else {
      setStatus(result.stderr || result.stdout || "AI generation failed");
      finishProcessing("Prompt JSON failed", "error");
    }
  }

  async function generateYouTubeShort() {
    beginProcessing("YouTube Short", "Creating hook/body/outro structure", prompt);
    const result = await window.ave.youtubeShort({ prompt, style: "auto" });
    if (result.ok && result.text) {
      setProjectText(result.text);
      setProjectPath(result.path || null);
      setPreset("shorts");
      const hook = typeof result.data?.hook === "string" ? result.data.hook : "Short generated";
      const duration = typeof result.data?.duration === "number" ? `${result.data.duration}s` : "vertical";
      setAiNotes(`YouTube Short ready.\nHook: ${hook}\nDuration: ${duration}\nRender preset: shorts`);
      setStatus("YouTube Short generated");
      setUiMode("advanced");
      setActiveTab("timeline");
      updateProcessing({ currentStage: "Short plan ready", progress: 100, currentScene: `${parseProject(result.text).data?.timeline?.length || "Generated"} scenes` }, "Generated YouTube Short plan", "success", hook);
      finishProcessing("YouTube Short generated", "success");
    } else {
      setStatus(result.stderr || result.stdout || "YouTube Short generation failed");
      finishProcessing("YouTube Short failed", "error");
    }
  }

  async function generateContentMode(regenerate = "full") {
    beginProcessing(regenerate === "full" ? "Content Mode" : `Regenerate ${regenerate}`, stageForRegeneration(regenerate), prompt);
    const result = await window.ave.contentGenerate({
      prompt,
      mode: contentMode,
      tone: contentTone,
      style: "auto",
      existingPlan: regenerate === "full" ? null : generationPlanPath,
      regenerate,
      locks: generationLocks
    });
    if (result.ok && result.text) {
      setProjectText(result.text);
      setProjectPath(result.path || null);
      const presetValue = typeof result.data?.targetPlatform === "string" && result.data.targetPlatform === "tiktok" ? "tiktok_reels" : "shorts";
      setPreset(presetValue);
      const hook = typeof result.data?.hook === "string" ? result.data.hook : "Content generated";
      const duration = typeof result.data?.duration === "number" ? `${result.data.duration}s` : "generated";
      const planPath = typeof result.data?.contentPlanPath === "string" ? result.data.contentPlanPath : null;
      setGenerationPlanPath(planPath);
      const reviewState = readGenerationReview(result.data || {}, planPath);
      setGenerationReview(reviewState);
      setAiNotes(`Content plan ready for review.\nMode: ${contentMode}\nHook: ${hook}\nDuration: ${duration}\nApprove sections before final export.`);
      setStatus(regenerate === "full" ? "Content review plan generated" : `Regenerated ${regenerate}`);
      setUiMode("advanced");
      setActiveTab("timeline");
      updateProcessing({
        currentStage: "Review plan ready",
        progress: 100,
        currentScene: `${reviewState.scenes.length || "Generated"} review scenes`
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
      renderPreview: true,
      quality: "preview",
      cache: true
    });
    if (result.ok && result.text) {
      setProjectText(result.text);
      setProjectPath(result.path || null);
      const planPath = typeof result.data?.contentPlanPath === "string" ? result.data.contentPlanPath : null;
      setGenerationPlanPath(planPath);
      setGenerationReview(readGenerationReview(result.data || {}, planPath));
      const previewVideo = typeof result.data?.previewVideo === "string" ? result.data.previewVideo : null;
      if (previewVideo) setPreviewPath(previewVideo);
      const planning = result.data?.planning as Record<string, unknown> | undefined;
      const qualityReview = result.data?.qualityReview as Record<string, unknown> | undefined;
      const hook = typeof planning?.hookStrategy === "string" ? planning.hookStrategy : "autonomous structure";
      const score = typeof qualityReview?.readinessScore === "number" ? qualityReview.readinessScore : null;
      const reasoning = typeof result.data?.reasoning === "string" ? result.data.reasoning : typeof result.data?.reasoning === "undefined" && typeof result.data?.review === "object" ? "" : "";
      const explanation = typeof result.data?.reasoning === "string" ? result.data.reasoning : typeof result.data?.explainabilityTextPath === "string" ? `Explainability written to ${result.data.explainabilityTextPath}` : "";
      setAiNotes(`Autonomous production plan ready.\nHook strategy: ${hook}\nReadiness: ${score ?? "review needed"}/100\n${explanation || reasoning || "Review and approve sections before final export."}`);
      setStatus("Autonomous production pipeline generated");
      setUiMode("advanced");
      setActiveTab(previewVideo ? "preview" : "timeline");
      updateProcessing({
        currentStage: "Autonomous plan ready",
        activeTask: "Preview, review packet, variants, and quality report generated",
        progress: 100,
        currentScene: `${parseProject(result.text).data?.timeline?.length || "Generated"} scenes`
      }, "Autonomous production pipeline complete", "success", previewVideo || undefined);
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

  async function render(label: string, renderQuality: "preview" | "final") {
    beginProcessing(label, renderQuality === "final" ? "Preparing final export" : "Preparing preview render", `${preset} ${exportFormat}`);
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
    }
    const result = await window.ave.startRender({
      text: projectText,
      projectPath,
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
      setProjectText(result.text);
      setDirectorReport(result.report || null);
      setAiNotes(String(result.report?.summary || "AI Director pass complete."));
      setStatus("AI Director updated the project");
      if (projectPath) setHistory(await window.ave.listHistory({ projectPath }));
      setActiveTab("director");
      finishProcessing("AI Director pass complete", "success");
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
      setProjectText(result.text);
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
      return report;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setAppError(`Final preflight: ${message}`);
      setStatus("Final preflight failed");
      return null;
    }
  }

  async function repairFinalPreflight(mode: string, issueId?: string | null) {
    await productAction("Preflight repair", async () => {
      const result = await window.ave.repairPreflight({
        text: projectText,
        projectPath,
        previewVideo: previewPath,
        format: exportFormat,
        mode,
        issueId
      });
      if (result.text) setProjectText(result.text);
      const refreshed = await window.ave.finalPreflight({
        text: result.text || projectText,
        projectPath: result.path || projectPath,
        previewVideo: previewPath,
        format: exportFormat
      });
      if (refreshed.data) setFinalPreflightReport(refreshed.data as FinalPreflightReport);
      setStatus(mode === "all" ? "Safe preflight repairs applied" : `Preflight issue ${mode}`);
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
        setProjectText(result.text);
        setProjectPath(result.path || null);
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
        setProjectText(result.text);
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
      setStatus("Settings saved");
    });
  }

  async function autosaveNow() {
    await productAction("Autosave", async () => {
      await window.ave.autosaveProject({ text: projectText, projectPath });
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
      setStatus(`Recovered ${file.name}`);
    });
  }

  async function refreshHardeningStatus() {
    await productAction("Hardening status", async () => {
      const statusReport = await window.ave.getHardeningStatus();
      setHardeningStatus(statusReport);
      setStatus("Local hardening status refreshed");
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

  async function refreshFrictionReport() {
    const report = await window.ave.getFrictionReport();
    setFrictionReport(report);
    setStatus("Local friction report refreshed");
  }

  const preflightBlockingIssues = (finalPreflightReport?.issues || []).filter((issue) => issue.blocking);
  const preflightWarningCount = (finalPreflightReport?.issues || []).filter((issue) => !issue.accepted && issue.severity === "warning").length;

  return (
    <div className={`app-shell theme-${settings.theme} mode-${uiMode} ${leftRailOpen ? "" : "left-rail-collapsed"} ${rightRailOpen ? "" : "right-rail-collapsed"}`}>
      <header className="topbar">
        <div>
          <strong>Automatic Video Editor</strong>
          <span>{projectPath || "Unsaved project"}</span>
        </div>
        <div className="toolbar">
          <button title="Create a beginner auto video" onClick={() => { setUiMode("beginner"); setActiveTab("beginner"); }}>
            <Sparkles size={16} /> New Auto Video
          </button>
          {uiMode === "beginner" && (
            <button title="Unlock JSON, timeline, assets, and advanced render controls" onClick={() => { setUiMode("advanced"); setActiveTab("json"); }}>
              <FileJson size={16} /> Advanced Mode
            </button>
          )}
          {uiMode === "advanced" && (
            <>
              <button title={leftRailOpen ? "Hide dashboard panel" : "Show dashboard panel"} onClick={() => setLeftRailOpen((open) => !open)}>
                <LayoutTemplate size={16} /> Dashboard
              </button>
              <button title={rightRailOpen ? "Hide AI/render controls" : "Show AI/render controls"} onClick={() => setRightRailOpen((open) => !open)}>
                <Bot size={16} /> Controls
              </button>
              <button title="New project" onClick={() => { setProjectText(formatProject(blankProject())); setProjectPath(null); setUiMode("advanced"); setActiveTab("json"); }}>
                <Plus size={16} /> New
              </button>
              <button title="Open project JSON" onClick={openProject}>
                <FolderOpen size={16} /> Open
              </button>
              <button title="Save project" onClick={saveProject}>
                <Save size={16} /> Save
              </button>
              <button title="Save as" onClick={saveAs}>
                <FileJson size={16} /> Save As
              </button>
              <button title="Validate JSON" onClick={validate}>
                <CheckCircle2 size={16} /> Validate
              </button>
              <button title="Repair JSON with engine" onClick={repair}>
                <Wand2 size={16} /> Repair
              </button>
            </>
          )}
        </div>
      </header>
      {appError && (
        <div className="error-toast">
          <span>{appError}</span>
          <button onClick={() => setAppError("")}>Dismiss</button>
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
              onPreviewPartial={(sceneId) => { void (sceneId ? previewCollaborationScene(sceneId) : Promise.resolve(setActiveTab("preview"))); }}
            />
          )}
        </div>
        <aside className="left-rail" aria-hidden={!leftRailOpen}>
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
              setActiveTab("json");
            }}
            onTemplate={createFromTemplate}
          />
        </aside>

        <section className="center-stage">
          <nav className="tabs">
            <button className={activeTab === "beginner" ? "active" : ""} onClick={() => setActiveTab("beginner")}><Sparkles size={15} /> Beginner</button>
            {uiMode === "advanced" && (
              <>
                <button className={activeTab === "json" ? "active" : ""} onClick={() => setActiveTab("json")}><FileJson size={15} /> JSON</button>
                <button className={activeTab === "timeline" ? "active" : ""} onClick={() => setActiveTab("timeline")}><ListVideo size={15} /> Timeline</button>
                <button className={activeTab === "preview" ? "active" : ""} onClick={() => setActiveTab("preview")}><MonitorPlay size={15} /> Preview</button>
                <button className={activeTab === "assets" ? "active" : ""} onClick={() => setActiveTab("assets")}><Image size={15} /> Assets</button>
                <button className={activeTab === "director" ? "active" : ""} onClick={() => setActiveTab("director")}><Bot size={15} /> Director</button>
                <button className={activeTab === "storyboard" ? "active" : ""} onClick={() => setActiveTab("storyboard")}><LayoutTemplate size={15} /> Storyboard</button>
                <button className={activeTab === "workflow" ? "active" : ""} onClick={() => setActiveTab("workflow")}><Scissors size={15} /> Workflow</button>
                <button className={activeTab === "product" ? "active" : ""} onClick={() => setActiveTab("product")}><CheckCircle2 size={15} /> Product</button>
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
              onAdvanced={() => { setUiMode("advanced"); setActiveTab("json"); }}
            />
          )}
          {activeTab === "json" && (
            <JsonEditor text={projectText} schemaReady={Boolean(engine)} onChange={setProjectText} onMount={onEditorMount} validation={validation} />
          )}
          {activeTab === "timeline" && project && <VisualTimeline project={project} onProjectChange={updateProject} />}
          {activeTab === "preview" && (
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
          )}
          {activeTab === "assets" && project && (
            <AssetLibrary
              project={project}
              assets={assets}
              assetReport={assetReport}
              onImport={importAssets}
              onAnalyze={runAssetIntelligence}
              onDropAsset={(asset) => updateProject(addAssetToFirstScene(project, asset))}
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
                const file = await window.ave.rollbackHistory({ projectPath, versionId });
                setProjectText(file.text);
                setStatus(`Rolled back to ${versionId}`);
              }}
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
          <details className="rail-section" open>
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
              onCaptions={async () => {
                const transcript = await window.ave.pickTranscript();
                if (!transcript) return;
                const result = await window.ave.addCaptions({ text: projectText, transcriptPath: transcript, mode: "word", style: "tiktok" });
                if (result.ok && result.text) setProjectText(result.text);
              }}
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
          <details className="rail-section" open>
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

      <footer className="statusbar">
        <span>{status}</span>
        {parsed.error && <span className="error">JSON parse error: {parsed.error}</span>}
        {project && <span>{project.timeline?.length || 0} scenes | {Object.keys(project.assets || {}).length} assets | {totalTimelineDuration(project).toFixed(1)}s</span>}
      </footer>
    </div>
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
        <details className="reasoning-panel">
          <summary>AI reasoning</summary>
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

function VisualTimeline({ project, onProjectChange }: { project: ProjectData; onProjectChange: (project: ProjectData) => void }) {
  const [zoom, setZoom] = useState(1);
  const [snapSeconds, setSnapSeconds] = useState(0.25);
  const [rippleEdits, setRippleEdits] = useState(true);
  const [selectedScene, setSelectedScene] = useState(0);
  const duration = Math.max(totalTimelineDuration(project), 1);
  const pxPerSecond = 70 * zoom;
  const width = duration * pxPerSecond;
  const layerCounts = collectLayerTypes(project);
  const timelineMeta = project.metadata?.timeline as Record<string, unknown> | undefined;
  const timelineMarkers = Array.isArray(timelineMeta?.markers)
    ? (timelineMeta.markers as Array<Record<string, unknown>>)
    : [];

  const beginResize = (sceneIndex: number, event: React.PointerEvent) => {
    event.preventDefault();
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

  const dropAsset = (sceneIndex: number, event: React.DragEvent) => {
    event.preventDefault();
    const assetKey = event.dataTransfer.getData("text/plain");
    if (assetKey) onProjectChange(addAssetLayerToScene(project, sceneIndex, assetKey));
  };

  const nudgeSelected = (delta: number) => {
    const scene = project.timeline?.[selectedScene];
    if (!scene) return;
    onProjectChange(updateSceneTimingAdvanced(project, selectedScene, { start: Math.max(0, Number(scene.start || 0) + delta) }, { ripple: false, snapSeconds }));
  };

  return (
    <div
      className="timeline-pane"
      tabIndex={0}
      onKeyDown={(event) => {
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
      <div className="timeline-tools">
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
        <span>{duration.toFixed(1)}s</span>
        <span>selected {project.timeline?.[selectedScene]?.id || "-"}</span>
        <span>{Object.entries(layerCounts).map(([type, count]) => `${type}:${count}`).join(" | ")}</span>
      </div>
      <div className="timeline-scroll">
        <div className="time-ruler" style={{ width }}>
          {Array.from({ length: Math.ceil(duration) + 1 }).map((_, index) => (
            <span key={index} style={{ left: index * pxPerSecond }}>{index}s</span>
          ))}
        </div>
        <div className="scene-track" style={{ width }}>
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
              className={`scene-block ${selectedScene === index ? "selected" : ""}`}
              key={scene.id}
              onClick={() => setSelectedScene(index)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => dropAsset(index, event)}
              style={{ left: scene.start * pxPerSecond, width: Math.max(scene.duration * pxPerSecond, 36) }}
            >
              <strong>{scene.id}</strong>
              <span>{scene.duration.toFixed(2)}s</span>
              {scene.group && <small>{scene.group}</small>}
              {scene.transitionOut && <small>{String(scene.transitionOut.type || "transition")}</small>}
              <button className="resize-handle" title="Drag timing handle" onPointerDown={(event) => beginResize(index, event)} />
            </div>
          ))}
        </div>
        <div className="layer-tracks" style={{ width }}>
          {(project.timeline || []).map((scene) =>
            scene.layers.map((layer, layerIndex) => (
              <div
                key={`${scene.id}-${layerIndex}`}
                className={`layer-pill ${layer.type}`}
                style={{
                  left: (scene.start + Number(layer.start || 0)) * pxPerSecond,
                  width: Math.max(Number(layer.duration || scene.duration) * pxPerSecond, 40),
                  top: layerIndex * 34
                }}
              >
                {layer.type} {layer.asset || layer.text || ""}
              </div>
            ))
          )}
        </div>
        <div className="audio-track" style={{ width }}>
          {(project.audio || []).map((track, index) => (
            <div key={index} className="audio-pill" style={{ left: Number(track.start || 0) * pxPerSecond }}>
              audio {String(track.asset || "")}
            </div>
          ))}
        </div>
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
  const [time, setTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.85);
  const [loop, setLoop] = useState(false);
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

  function syncVideo(nextTime: number) {
    const clamped = Math.max(0, Math.min(nextTime, timelineDuration || nextTime));
    if (videoRef.current) videoRef.current.currentTime = clamped;
    setTime(clamped);
  }

  function setRate(nextRate: number) {
    setPlaybackRate(nextRate);
    if (videoRef.current) videoRef.current.playbackRate = nextRate;
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
      <div className="preview-frame">
        {src ? (
          <>
            <video
              ref={videoRef}
              src={src}
              loop={loop}
              muted={muted}
              onPlay={(event) => { event.currentTarget.playbackRate = playbackRate; event.currentTarget.volume = volume; }}
              onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
              onLoadedMetadata={(event) => {
                setVideoDuration(event.currentTarget.duration || 0);
                event.currentTarget.playbackRate = playbackRate;
                event.currentTarget.volume = volume;
              }}
            />
            <div className="safe-zone title-zone" />
            <div className="safe-zone action-zone" />
          </>
        ) : framePath ? (
          <>
            <img className="preview-still" src={window.ave.toFileUrl(framePath)} alt="" />
            <div className="safe-zone title-zone" />
            <div className="safe-zone action-zone" />
          </>
        ) : (
          <div className="empty-preview">Render a preview to scrub frames here.</div>
        )}
      </div>
      <div className="preview-controls interactive-controls">
        <div className="preview-toolbar">
          <button onClick={onInteractivePreview}><RefreshCw size={16} /> Build Preview Cache</button>
          <select value={previewQualityMode} onChange={(event) => setPreviewQualityMode(event.target.value)} title="Preview quality mode">
            <option value="draft">draft preview</option>
            <option value="proxy">proxy preview</option>
            <option value="balanced">balanced preview</option>
            <option value="high">high-quality preview</option>
            <option value="final_sim">final render simulation</option>
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
        </div>
        <div className="preview-toolbar">
          <button onClick={() => videoRef.current?.play()}><Play size={16} /> Play</button>
          <button onClick={() => videoRef.current?.pause()}><Pause size={16} /> Pause</button>
          <button onClick={() => { videoRef.current?.pause(); syncVideo(0); }}>Stop</button>
          <button onClick={() => { syncVideo(0); videoRef.current?.play(); }}><RefreshCw size={16} /> Restart</button>
          <button onClick={() => syncVideo(time - 1 / Math.max(fps, 1))}>Frame -</button>
          <button onClick={() => syncVideo(time + 1 / Math.max(fps, 1))}>Frame +</button>
          <button onClick={onRealtimePreview}><MonitorPlay size={16} /> Cache Frame</button>
        </div>
        <div className="preview-toolbar">
          <select value={playbackRate} onChange={(event) => setRate(Number(event.target.value))} title="Playback speed">
            <option value={0.25}>0.25x</option>
            <option value={0.5}>0.5x</option>
            <option value={1}>1x</option>
            <option value={1.25}>1.25x</option>
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
        <input
          type="range"
          min={0}
          max={Math.max(duration, 0)}
          step={0.05}
          value={Math.min(previewTimeSeconds, Math.max(duration, 0))}
          onChange={(event) => setPreviewTimeSeconds(Number(event.target.value))}
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

function AssetLibrary({
  project,
  assets,
  assetReport,
  onImport,
  onAnalyze,
  onDropAsset
}: {
  project: ProjectData;
  assets: AssetCheck[];
  assetReport: Record<string, unknown> | null;
  onImport: () => void;
  onAnalyze: () => void;
  onDropAsset: (asset: ImportedAsset) => void;
}) {
  const analyzedAssets = Array.isArray(assetReport?.assets) ? assetReport.assets as Array<Record<string, unknown>> : [];
  return (
    <div className="assets-pane">
      <div className="asset-tools">
        <button onClick={onImport}><Plus size={15} /> Import Media</button>
        <button onClick={onAnalyze}><CheckCircle2 size={15} /> Analyze</button>
        <span>{Object.keys(project.assets || {}).length} JSON assets</span>
        <span>{assets.filter((asset) => !asset.exists).length} missing</span>
      </div>
      <div className="asset-grid">
        {assets.map((asset) => (
          <button
            key={asset.key}
            className={`asset-tile ${asset.exists ? "" : "missing"}`}
            title={asset.path}
            draggable
            onDragStart={(event) => event.dataTransfer.setData("text/plain", asset.key)}
            onDoubleClick={() => onDropAsset({ key: asset.key, path: asset.path, type: asset.type })}
          >
            {asset.type === "image" && asset.exists ? <img src={window.ave.toFileUrl(asset.path)} alt="" /> : <Video size={30} />}
            <strong>{asset.key}</strong>
            <span>{asset.exists ? asset.type : "missing"}</span>
            {analyzedAssets.find((item) => item.key === asset.key) && <span>analyzed</span>}
          </button>
        ))}
      </div>
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
  plugins,
  renderQueueItems,
  onExportPackage,
  onOpenPackage,
  onRollback,
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
  plugins: PluginInfo[];
  renderQueueItems: RenderQueueItem[];
  onExportPackage: () => void;
  onOpenPackage: () => void;
  onRollback: (versionId: string) => void;
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
        </div>
        <div className="list">
          {history.length === 0 && <span className="muted">No saved AI edits.</span>}
          {history.map((item) => (
            <div className="history-row" key={item.id}>
              <strong>{item.id}</strong>
              <span>{item.summary || item.timestamp}</span>
              <button disabled={!projectPath} onClick={() => onRollback(item.id)}>Rollback</button>
            </div>
          ))}
        </div>
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
    duration: durationFromPrompt || form.duration,
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
      <pre>{notes || "Project explanations and suggestions appear here."}</pre>
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
  return (
    <section className="panel render-panel">
      <h2><MonitorPlay size={16} /> Render Panel</h2>
      <label>
        Preset
        <select value={preset} onChange={(event) => setPreset(event.target.value)}>
          {["youtube_1080p", "tiktok_reels", "shorts", "square", "discord_720p", "instagram_reels", "high_quality_archive", "low_size_preview", "cinematic_4k"].map((item) => <option key={item}>{item}</option>)}
        </select>
      </label>
      <label>
        Format
        <select value={exportFormat} onChange={(event) => setExportFormat(event.target.value as "mp4" | "mov" | "mkv" | "webm" | "gif")}>
          {["mp4", "mov", "mkv", "webm", "gif"].map((item) => <option key={item}>{item}</option>)}
        </select>
      </label>
      <label>
        Quality
        <select value={quality} onChange={(event) => setQuality(event.target.value as "preview" | "final")}>
          <option value="preview">preview</option>
          <option value="final">final</option>
        </select>
      </label>
      <div className="toggles">
        <label><input type="checkbox" checked={cache} onChange={(event) => setCache(event.target.checked)} /> cache</label>
        <label><input type="checkbox" checked={resume} onChange={(event) => setResume(event.target.checked)} /> resume</label>
        <label><input type="checkbox" checked={gpu} onChange={(event) => setGpu(event.target.checked)} /> GPU</label>
      </div>
      <div className="button-grid">
        <button onClick={onPreview}><Play size={15} /> Preview</button>
        <button onClick={onPreflight}><CheckCircle2 size={15} /> Preflight</button>
        <button onClick={onFinal}><MonitorPlay size={15} /> Final</button>
        <button onClick={onOpenOutput}><FolderOpen size={15} /> Output</button>
      </div>
      <div className="render-queue-mini">
        <div className="review-header">
          <strong>Final Export Queue</strong>
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
                <small>{job.currentScene || job.status} | ETA {formatEta(job.estimatedRemainingSeconds)}</small>
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
          <div className="button-grid compact">
            <button onClick={() => onRepairPreflight("all")}><Wand2 size={14} /> Fix Safe</button>
          </div>
          <div className="preflight-issues">
            {issues.slice(0, 6).map((issue) => (
              <div className={`preflight-issue ${issue.severity}`} key={issue.id}>
                <strong>{issue.category.replace(/_/g, " ")}</strong>
                <span>{issue.message}</span>
                <small>{issue.suggestion || "Review before export."}</small>
                <div className="button-grid compact">
                  {issue.safeAutoFix && <button onClick={() => onRepairPreflight("selected", issue.id)}>Fix</button>}
                  <button onClick={() => onRepairPreflight("ignore", issue.id)}>Accept</button>
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
