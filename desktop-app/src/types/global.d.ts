export {};

declare global {
  interface Window {
    ave: AveApi;
  }

  type AveApi = {
    getEngineInfo: () => Promise<EngineInfo>;
    getRecentProjects: () => Promise<RecentProject[]>;
    openProject: () => Promise<ProjectFile | null>;
    readProject: (path: string) => Promise<ProjectFile>;
    saveProject: (payload: { path?: string | null; text: string }) => Promise<ProjectFile>;
    saveProjectAs: (payload: { text: string }) => Promise<ProjectFile | null>;
    validateJson: (payload: { text: string }) => Promise<EngineResult>;
    repairJson: (payload: { text: string }) => Promise<EngineTextResult>;
    aiGenerate: (payload: { prompt: string }) => Promise<EngineTextResult>;
    youtubeShort: (payload: { prompt: string; style?: string | null }) => Promise<EngineJsonTextResult>;
    contentGenerate: (payload: { prompt: string; mode: string; tone?: string | null; style?: string | null; existingPlan?: string | null; regenerate?: string | null; locks?: string[] | null; approved?: boolean | null }) => Promise<EngineJsonTextResult>;
    autonomousPipeline: (payload: AutonomousPipelineRequest) => Promise<EngineJsonTextResult>;
    beginnerPickMedia: () => Promise<string | null>;
    beginnerPickImageFolder: () => Promise<string | null>;
    beginnerPickAssetFolder: () => Promise<string | null>;
    beginnerPickMusic: () => Promise<string | null>;
    beginnerPickLogo: () => Promise<string | null>;
    beginnerAutoTemplate: (payload: BeginnerAutoTemplateRequest) => Promise<EngineJsonTextResult>;
    contentApprove: (payload: { planPath: string; section?: string | null; status?: string | null }) => Promise<EngineJsonResult>;
    createTemplate: (payload: { template: string }) => Promise<EngineTextResult>;
    addCaptions: (payload: { text: string; transcriptPath: string; mode: string; style: string }) => Promise<EngineTextResult>;
    runDirector: (payload: { text: string; projectPath?: string | null; goal: string; preserve?: string[] }) => Promise<EngineJsonTextResult>;
    generateStoryboard: (payload: { text: string; projectPath?: string | null }) => Promise<EngineJsonResult>;
    analyzeAssets: (payload: { text: string; projectPath?: string | null }) => Promise<EngineJsonResult>;
    resolveBroll: (payload: { text: string; projectPath?: string | null }) => Promise<EngineTextResult>;
    listHistory: (payload: { projectPath?: string | null }) => Promise<HistoryVersion[]>;
    recordHistory: (payload: { projectPath?: string | null; oldText: string; newText: string; summary: Record<string, unknown> }) => Promise<HistoryVersion | null>;
    rollbackHistory: (payload: { projectPath: string; versionId: string }) => Promise<ProjectFile>;
    exportPackage: (payload: { text: string; projectPath?: string | null }) => Promise<EngineJsonResult>;
    openPackage: () => Promise<ProjectFile | null>;
    listPlugins: () => Promise<PluginInfo[]>;
    initPlugin: (payload: { name: string; type: string }) => Promise<PluginInfo>;
    realtimePreview: (payload: { text: string; projectPath?: string | null; time?: number; sceneId?: string | null; qualityMode?: string; layerMode?: string }) => Promise<EngineJsonResult>;
    interactivePreview: (payload: { text: string; projectPath?: string | null; qualityMode?: string; scope?: string; sceneId?: string | null }) => Promise<EngineJsonResult>;
    qualityCheck: (payload: { text: string; projectPath?: string | null }) => Promise<EngineJsonResult>;
    finalPreflight: (payload: { text: string; projectPath?: string | null; previewVideo?: string | null; format?: string }) => Promise<EngineJsonResult>;
    repairPreflight: (payload: { text: string; projectPath?: string | null; previewVideo?: string | null; format?: string; mode?: string; issueId?: string | null }) => Promise<EngineJsonTextResult>;
    projectManifest: (payload: { text: string; projectPath?: string | null }) => Promise<EngineJsonResult>;
    socialReformat: (payload: { text: string; projectPath?: string | null; targets: string[] }) => Promise<EngineJsonResult>;
    repurposeContent: (payload: { text: string; projectPath?: string | null; targets?: string[] | null; hooks?: string[] | null; ctas?: string[] | null; reuseStyle?: boolean | null; render?: boolean | null; package?: boolean | null; quality?: "preview" | "final"; maxVariants?: number | null }) => Promise<EngineJsonResult>;
    postPackage: (payload: { text: string; projectPath?: string | null; videoPath: string; targets: string[]; title?: string | null }) => Promise<EngineJsonResult>;
    postExportReview: (payload: { text: string; projectPath?: string | null; videoPath: string; packageDir?: string | null }) => Promise<EngineJsonResult>;
    postExportReexport: (payload: { text: string; projectPath?: string | null; preset?: string | null; mode?: string | null; format?: string | null; captions?: string | null; thumbnail?: string | null }) => Promise<EngineJsonTextResult>;
    postExportTemplate: (payload: { text: string; projectPath?: string | null; videoPath?: string | null; name: string; note?: string | null }) => Promise<EngineJsonResult>;
    postExportVariants: (payload: { text: string; projectPath?: string | null; variants?: string[] | null; hook?: string | null; cta?: string | null }) => Promise<EngineJsonResult>;
    postExportNote: (payload: { text: string; projectPath?: string | null; videoPath?: string | null; profile?: string | null; tags?: string[] | null; note?: string | null }) => Promise<EngineJsonResult>;
    initBrandKit: () => Promise<EngineJsonResult>;
    applyBrandKit: (payload: { text: string; projectPath?: string | null }) => Promise<EngineTextResult>;
    listTemplatePacks: () => Promise<TemplatePack[]>;
    exportTemplatePack: (payload: { template: string }) => Promise<EngineJsonResult>;
    installTemplatePack: () => Promise<EngineJsonResult>;
    getSettings: () => Promise<AppSettings>;
    saveSettings: (settings: AppSettings) => Promise<AppSettings>;
    logFriction: (payload: Record<string, unknown>) => Promise<Record<string, unknown>>;
    getFrictionReport: () => Promise<FrictionReport>;
    autosaveProject: (payload: { text: string; projectPath?: string | null }) => Promise<RecoveryPoint | null>;
    listRecovery: (payload: { projectPath?: string | null }) => Promise<RecoveryPoint[]>;
    restoreRecovery: (payload: { sourcePath: string; targetPath?: string | null }) => Promise<ProjectFile>;
    getHardeningStatus: () => Promise<HardeningStatus>;
    workflowDashboard: (payload: { text: string; projectPath?: string | null }) => Promise<EngineJsonResult>;
    getAdaptiveWorkflowMemory: (payload: { text?: string | null; projectPath?: string | null; profile?: string | null }) => Promise<AdaptiveWorkflowMemory>;
    recordAdaptiveWorkflowEvent: (payload: Record<string, unknown>) => Promise<AdaptiveWorkflowMemory>;
    feedbackAnalyze: (payload: { text: string; projectPath?: string | null; videoPath?: string | null }) => Promise<EngineJsonResult>;
    feedbackReview: (payload: { text: string; projectPath?: string | null; videoPath?: string | null; profile?: string | null; note?: string | null; ratings?: Record<string, number> }) => Promise<EngineJsonResult>;
    feedbackLearn: (payload: { profile: string }) => Promise<EngineJsonResult>;
    evolutionReport: (payload: { text: string; projectPath?: string | null; profile?: string | null; includeReleaseCheck?: boolean }) => Promise<EngineJsonResult>;
    openLocalDocs: () => Promise<void>;
    pickTranscript: () => Promise<string | null>;
    importAssets: (payload: { projectPath?: string | null }) => Promise<ImportedAsset[]>;
    checkAssets: (payload: { text: string; projectPath?: string | null }) => Promise<AssetCheck[]>;
    startRender: (payload: RenderRequest) => Promise<{ runId: string; outputPath: string }>;
    getRenderQueue: () => Promise<RenderQueueItem[]>;
    pauseRenderQueue: () => Promise<RenderQueueItem[]>;
    resumeRenderQueue: () => Promise<RenderQueueItem[]>;
    cancelRenderJob: (payload: { runId: string }) => Promise<RenderQueueItem[]>;
    retryRenderJob: (payload: { runId: string }) => Promise<RenderQueueItem[]>;
    prioritizeRenderJob: (payload: { runId: string; priority: number }) => Promise<RenderQueueItem[]>;
    revealPath: (path: string) => Promise<void>;
    openOutputFolder: () => Promise<void>;
    toFileUrl: (path: string) => string;
    onRenderLog: (callback: (event: RenderLogEvent) => void) => () => void;
    onRenderComplete: (callback: (event: RenderCompleteEvent) => void) => () => void;
    onRenderQueue: (callback: (items: RenderQueueItem[]) => void) => () => void;
  };

  type EngineInfo = {
    engineRoot: string;
    schema: Record<string, unknown>;
    examplesDir: string;
    outputDir: string;
    templates: string[];
    presets: string[];
    styles: string[];
  };

  type RecentProject = {
    path: string;
    name: string;
    openedAt: string;
  };

  type ProjectFile = {
    path: string;
    text: string;
    name: string;
  };

  type BeginnerAutoTemplateRequest = {
    mediaFile?: string | null;
    imageFolder?: string | null;
    assetFolder?: string | null;
    musicPath?: string | null;
    logoPath?: string | null;
    targetPlatform: string;
    template: string;
    productName: string;
    goal: string;
    keyFeatures?: string[];
    vibe?: string | null;
    duration?: number | null;
    quality?: "preview" | "final";
    render?: boolean | null;
    cache?: boolean | null;
  };

  type AutonomousPipelineRequest = {
    prompt: string;
    assetsFolder?: string | null;
    musicPath?: string | null;
    logoPath?: string | null;
    profile?: string | null;
    platform?: string | null;
    contentType?: string | null;
    vibe?: string | null;
    duration?: number | null;
    variants?: number | null;
    approved?: boolean | null;
    renderPreview?: boolean | null;
    finalRender?: boolean | null;
    package?: boolean | null;
    quality?: "preview" | "final" | null;
    cache?: boolean | null;
    gpu?: boolean | null;
  };

  type EngineResult = {
    ok: boolean;
    stdout: string;
    stderr: string;
    exitCode: number | null;
  };

  type EngineTextResult = EngineResult & {
    text?: string;
    path?: string;
  };

  type EngineJsonResult = EngineResult & {
    data?: Record<string, unknown>;
    path?: string;
  };

  type EngineJsonTextResult = EngineTextResult & {
    data?: Record<string, unknown>;
    report?: Record<string, unknown>;
  };

  type ImportedAsset = {
    key: string;
    path: string;
    type: "image" | "video" | "audio" | "unknown";
  };

  type AssetCheck = {
    key: string;
    path: string;
    exists: boolean;
    type: "image" | "video" | "audio" | "unknown";
  };

  type RenderRequest = {
    text: string;
    projectPath?: string | null;
    outputPath?: string | null;
    quality: "preview" | "final";
    preset?: string | null;
    format?: "mp4" | "mov" | "mkv" | "webm" | "gif" | "image_sequence" | null;
    generatePlaceholders?: boolean;
    cache?: boolean;
    resume?: boolean;
    gpu?: boolean;
    label?: string;
    priority?: number;
    createDeliveryPackage?: boolean;
    packagePlatforms?: string[];
    packageTitle?: string | null;
  };

  type RenderQueueItem = {
    runId: string;
    label: string;
    outputPath: string;
    status: "queued" | "running" | "completed" | "failed" | "canceled";
    priority: number;
    exitCode?: number | null;
    currentScene?: string;
    progressPercent?: number;
    estimatedRemainingSeconds?: number;
    packagePath?: string;
    packageStatus?: "pending" | "running" | "completed" | "failed";
    packageError?: string;
    sceneCount?: number;
    completedScenes?: number;
  };

  type HistoryVersion = {
    id: string;
    timestamp?: string;
    summary?: string;
    [key: string]: unknown;
  };

  type PluginInfo = {
    id: string;
    name: string;
    type: string;
    version?: string;
    path?: string;
    [key: string]: unknown;
  };

  type TemplatePack = {
    key: string;
    name: string;
    author: string;
    version: string;
    tags: string[];
    previewThumbnail?: string;
    requiredAssets?: Record<string, string>;
    exportPreset?: string;
    transitionStyle?: string;
    installState?: string;
    [key: string]: unknown;
  };

  type AppSettings = {
    theme: "graphite" | "midnight" | "light";
    autosave: boolean;
    autosaveIntervalSeconds: number;
    previewTimeSeconds: number;
    keyboardShortcuts: boolean;
  };

  type FrictionReport = {
    eventCount: number;
    slowOperations: number;
    failedOperations: number;
    repeatedSettings: number;
    recent: Array<Record<string, unknown>>;
    topLabels: Array<{ label: string; count: number }>;
    [key: string]: unknown;
  };

  type AdaptiveWorkflowMemory = {
    memoryVersion?: number;
    profile?: string;
    updatedAt?: string;
    localOnly?: boolean;
    path?: string;
    events?: Array<Record<string, unknown>>;
    preferences?: Record<string, unknown>;
    smartDefaults?: Record<string, unknown>;
    creatorFingerprint?: Record<string, unknown>;
    recoverySignals?: Record<string, unknown>;
    session?: Record<string, unknown>;
    contextSuggestions?: Array<Record<string, unknown>>;
    friction?: Record<string, unknown>;
    [key: string]: unknown;
  };

  type RecoveryPoint = {
    type: string;
    path: string;
    timestamp?: string;
    size?: number;
  };

  type HardeningStatus = {
    dependency?: Record<string, unknown>;
    model?: Record<string, unknown>;
    privacy?: Record<string, unknown>;
    performance?: Record<string, unknown>;
    docsPath?: string;
    generatedAt?: string;
  };

  type RenderLogEvent = {
    runId: string;
    line: string;
    stream: "stdout" | "stderr";
  };

  type RenderCompleteEvent = {
    runId: string;
    exitCode: number | null;
    outputPath: string;
    packagePath?: string;
  };
}
