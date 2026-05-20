import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";
import { ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import crypto from "node:crypto";

type RecentProject = {
  path: string;
  name: string;
  openedAt: string;
};

type EngineResult = {
  ok: boolean;
  stdout: string;
  stderr: string;
  exitCode: number | null;
};

type AppSettings = {
  theme: "graphite" | "midnight" | "light";
  autosave: boolean;
  autosaveIntervalSeconds: number;
  previewTimeSeconds: number;
  keyboardShortcuts: boolean;
};

type TemplatePack = {
  key: string;
  name: string;
  author: string;
  version: string;
  tags: string[];
  previewThumbnail: string;
  requiredAssets: Record<string, string>;
  exportPreset: string;
  transitionStyle: string;
  installState: string;
};

type RenderPayload = {
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

type BeginnerAutoTemplatePayload = {
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

type AutonomousPipelinePayload = {
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

type FrictionEvent = {
  event: string;
  label?: string;
  elapsedMs?: number;
  message?: string;
  projectPath?: string | null;
  outputPath?: string | null;
  uiMode?: string;
  [key: string]: unknown;
};

type AdaptiveWorkflowEvent = {
  event: string;
  profile?: string;
  template?: string | null;
  targetPlatform?: string | null;
  exportPreset?: string | null;
  duration?: number | null;
  style?: string | null;
  pacing?: string | null;
  captionDensity?: string | null;
  motionIntensity?: string | null;
  hookStyle?: string | null;
  correction?: string | null;
  mediaPath?: string | null;
  note?: string | null;
  projectPath?: string | null;
  text?: string | null;
  [key: string]: unknown;
};

type WorkflowSignals = {
  source?: string;
  template?: string;
  targetPlatform?: string;
  exportPreset?: string;
  duration?: number;
  pacing?: string;
  captionDensity?: string;
  motionIntensity?: string;
  hookStyle?: string;
  transition?: string;
  lightingProfile?: string;
  stylePreset?: string;
  aspectRatio?: string;
  mediaKind?: string;
  promptKind?: string;
  captionCount?: number;
  sceneCount?: number;
};

type AdaptiveWorkflowMemory = {
  memoryVersion: number;
  profile: string;
  updatedAt: string;
  localOnly: boolean;
  path: string;
  events: Array<Record<string, unknown>>;
  preferences: Record<string, unknown>;
  smartDefaults: Record<string, unknown>;
  creatorFingerprint: Record<string, unknown>;
  recoverySignals: Record<string, unknown>;
  session: Record<string, unknown>;
  contextSuggestions: Array<Record<string, unknown>>;
  friction: Record<string, unknown>;
};

type QueuedRenderJob = {
  runId: string;
  label: string;
  input: string;
  outputPath: string;
  args: string[];
  payload: RenderPayload;
  status: "queued" | "running" | "completed" | "failed" | "canceled";
  priority: number;
  logs: string[];
  exitCode?: number | null;
  child?: ChildProcessWithoutNullStreams;
  startedAt?: number;
  currentScene?: string;
  progressPercent?: number;
  estimatedRemainingSeconds?: number;
  packagePath?: string;
  packageStatus?: "pending" | "running" | "completed" | "failed";
  packageError?: string;
  sceneCount?: number;
  completedScenes?: number;
};

const engineRoot = app.isPackaged ? path.join(process.resourcesPath, "engine") : path.resolve(__dirname, "..", "..");
const renderPy = path.join(engineRoot, "render.py");
const pythonBinary = process.env.PYTHON || "python";
const userDataDir = app.getPath("userData");
const recentPath = path.join(userDataDir, "recent-projects.json");
const settingsPath = path.join(userDataDir, "settings.json");
const frictionLogPath = path.join(userDataDir, "friction-events.jsonl");
const adaptiveMemoryPath = path.join(userDataDir, "adaptive-workflow-memory.json");
const generatedDir = app.isPackaged ? path.join(userDataDir, "projects") : path.join(engineRoot, "examples", "generated");
const outputRoot = app.isPackaged ? path.join(userDataDir, "output") : path.join(engineRoot, "output");
const exportsRoot = app.isPackaged ? path.join(userDataDir, "exports") : path.join(engineRoot, "exports");
const tempDir = path.join(app.getPath("temp"), "automatic-video-editor-desktop");
const videoImportExtensions = ["mp4", "mov", "mkv", "avi", "webm", "flv", "wmv", "mpeg", "mpg", "m4v", "ts", "mts", "m2ts"];
const imageImportExtensions = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "svg"];
const audioImportExtensions = ["mp3", "wav", "flac", "ogg", "aac", "m4a"];
const allMediaImportExtensions = [...videoImportExtensions, ...imageImportExtensions, ...audioImportExtensions];

let mainWindow: BrowserWindow | null = null;
let splashWindow: BrowserWindow | null = null;
let renderQueue: QueuedRenderJob[] = [];
let activeRender: QueuedRenderJob | null = null;
let renderQueuePaused = false;

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 420,
    height: 260,
    frame: false,
    resizable: false,
    show: true,
    backgroundColor: "#181713",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  splashWindow.loadFile(path.join(__dirname, "..", "splash.html"));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1500,
    height: 940,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: "#101216",
    title: "Automatic Video Editor",
    icon: path.join(__dirname, "..", "assets", "icon.svg"),
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  const startUrl = process.env.ELECTRON_START_URL;
  if (startUrl) {
    mainWindow.loadURL(startUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
  mainWindow.once("ready-to-show", () => {
    splashWindow?.close();
    splashWindow = null;
    mainWindow?.show();
  });
}

app.whenReady().then(() => {
  registerIpc();
  createSplashWindow();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

function registerIpc() {
  ipcMain.handle("engine:info", async () => {
    const schemaText = await fs.readFile(path.join(engineRoot, "src", "schema", "project.schema.json"), "utf-8");
    return {
      engineRoot,
      schema: JSON.parse(schemaText),
      examplesDir: app.isPackaged ? generatedDir : path.join(engineRoot, "examples"),
      outputDir: outputRoot,
      templates: [
        "youtube_intro",
        "tiktok_reels_short",
        "gaming_montage",
        "product_promo",
        "lyric_video",
        "slideshow",
        "meme_edit",
        "tutorial_video"
      ],
      presets: ["youtube_1080p", "tiktok_reels", "shorts", "square", "discord_720p", "cinematic_4k", "instagram_reels", "high_quality_archive", "low_size_preview"],
      styles: ["clean_cinematic", "gaming_montage", "red_black_aegis", "blue_black_cyber", "vaporwave", "minimal_tech", "horror_glitch", "luxury_promo"]
    };
  });

  ipcMain.handle("recent:list", async () => readRecent());

  ipcMain.handle("project:open", async () => {
    const result = await dialog.showOpenDialog({
      title: "Open project.json",
      filters: [{ name: "JSON Project", extensions: ["json"] }],
      properties: ["openFile"]
    });
    if (result.canceled || !result.filePaths[0]) return null;
    return readProjectFile(result.filePaths[0]);
  });

  ipcMain.handle("project:read", async (_event, filePath: string) => readProjectFile(filePath));

  ipcMain.handle("project:save", async (_event, payload: { path?: string | null; text: string }) => {
    const targetPath = payload.path || path.join(generatedDir, "desktop_project.json");
    await fs.mkdir(path.dirname(targetPath), { recursive: true });
    await fs.writeFile(targetPath, payload.text, "utf-8");
    await addRecent(targetPath);
    return readProjectFile(targetPath);
  });

  ipcMain.handle("project:saveAs", async (_event, payload: { text: string }) => {
    const result = await dialog.showSaveDialog({
      title: "Save project JSON",
      defaultPath: path.join(generatedDir, "project.json"),
      filters: [{ name: "JSON Project", extensions: ["json"] }]
    });
    if (result.canceled || !result.filePath) return null;
    await fs.writeFile(result.filePath, payload.text, "utf-8");
    await addRecent(result.filePath);
    return readProjectFile(result.filePath);
  });

  ipcMain.handle("engine:validate", async (_event, payload: { text: string }) => {
    const input = await writeTempProject(payload.text, "validate");
    return runEngine(["validate", input]);
  });

  ipcMain.handle("engine:repair", async (_event, payload: { text: string }) => {
    const input = await writeTempProject(payload.text, "repair");
    const output = tempProjectPath("repaired");
    const result = await runEngine(["repair", input, "-o", output]);
    const text = result.ok ? await fs.readFile(output, "utf-8") : undefined;
    return { ...result, text, path: output };
  });

  ipcMain.handle("engine:aiGenerate", async (_event, payload: { prompt: string }) => {
    const output = tempProjectPath("ai-generated");
    const result = await runEngine(["ai-generate", payload.prompt, "-o", output]);
    const text = result.ok ? await fs.readFile(output, "utf-8") : undefined;
    return { ...result, text, path: output };
  });

  ipcMain.handle("engine:youtubeShort", async (_event, payload: { prompt: string; style?: string | null }) => {
    const outputDir = path.join(generatedDir, `youtube-short-${Date.now()}`);
    const args = ["youtube-short", payload.prompt, "-o", outputDir];
    if (payload.style) args.push("--style", payload.style);
    const result = await runEngine(args);
    const projectPath = path.join(outputDir, "project.json");
    const summaryPath = path.join(outputDir, "youtube_short_summary.json");
    const text = result.ok && fsSync.existsSync(projectPath) ? await fs.readFile(projectPath, "utf-8") : undefined;
    const data = result.ok && fsSync.existsSync(summaryPath) ? JSON.parse(await fs.readFile(summaryPath, "utf-8")) : undefined;
    return { ...result, text, path: projectPath, data };
  });

  ipcMain.handle("engine:contentGenerate", async (_event, payload: { prompt: string; mode: string; tone?: string | null; style?: string | null; existingPlan?: string | null; regenerate?: string | null; locks?: string[] | null; approved?: boolean | null }) => {
    const outputDir = path.join(generatedDir, `content-${payload.mode || "youtube_shorts"}-${Date.now()}`);
    const args = ["content-generate", payload.prompt, "--mode", payload.mode || "youtube_shorts", "-o", outputDir];
    if (payload.tone) args.push("--tone", payload.tone);
    if (payload.style) args.push("--style", payload.style);
    if (payload.existingPlan) args.push("--existing-plan", payload.existingPlan);
    if (payload.regenerate) args.push("--regenerate", payload.regenerate);
    if (payload.locks?.length) payload.locks.forEach((lock) => args.push("--lock", lock));
    if (payload.approved) args.push("--approved");
    const result = await runEngine(args);
    const projectPath = path.join(outputDir, "project.json");
    const summaryPath = path.join(outputDir, "content_generation_summary.json");
    const reviewPath = path.join(outputDir, "generation_review.json");
    const reasoningPath = path.join(outputDir, "ai_reasoning_summary.txt");
    const text = result.ok && fsSync.existsSync(projectPath) ? await fs.readFile(projectPath, "utf-8") : undefined;
    const data = result.ok && fsSync.existsSync(summaryPath) ? JSON.parse(await fs.readFile(summaryPath, "utf-8")) : undefined;
    const review = result.ok && fsSync.existsSync(reviewPath) ? JSON.parse(await fs.readFile(reviewPath, "utf-8")) : undefined;
    const reasoning = result.ok && fsSync.existsSync(reasoningPath) ? await fs.readFile(reasoningPath, "utf-8") : undefined;
    return { ...result, text, path: projectPath, data: data ? { ...data, review, reasoning } : data };
  });

  ipcMain.handle("engine:autonomousPipeline", async (_event, payload: AutonomousPipelinePayload) => {
    const safeName = slugify(payload.prompt || "autonomous-pipeline");
    const outputDir = path.join(generatedDir, `autonomous-${safeName}-${Date.now()}`);
    const args = ["autonomous", payload.prompt || "Create a polished creator video", "-o", outputDir];
    if (payload.assetsFolder) args.push("--assets", payload.assetsFolder);
    if (payload.musicPath) args.push("--music", payload.musicPath);
    if (payload.logoPath) args.push("--logo", payload.logoPath);
    if (payload.profile) args.push("--profile", payload.profile);
    if (payload.platform) args.push("--platform", payload.platform);
    if (payload.contentType) args.push("--content-type", payload.contentType);
    if (payload.vibe) args.push("--vibe", payload.vibe);
    if (payload.duration) args.push("--duration", String(payload.duration));
    if (payload.variants) args.push("--variants", String(payload.variants));
    if (payload.renderPreview !== false) args.push("--render-preview");
    if (payload.approved) args.push("--approved");
    if (payload.finalRender) args.push("--final-render");
    if (payload.package) args.push("--package");
    args.push("--quality", payload.quality || "preview");
    if (payload.cache !== false) args.push("--cache");
    if (payload.gpu) args.push("--gpu");
    const result = await runEngine(args);
    const projectPath = path.join(outputDir, "project.json");
    const summaryPath = path.join(outputDir, "autonomous_pipeline_summary.json");
    const reviewPath = path.join(outputDir, "generation_review.json");
    const reasoningPath = path.join(outputDir, "autonomous_explainability.txt");
    const text = result.ok && fsSync.existsSync(projectPath) ? await fs.readFile(projectPath, "utf-8") : undefined;
    const data = result.ok ? await readJsonIfExists(summaryPath) : undefined;
    const review = result.ok ? await readJsonIfExists(reviewPath) : undefined;
    const reasoning = result.ok && fsSync.existsSync(reasoningPath) ? await fs.readFile(reasoningPath, "utf-8") : undefined;
    if (result.ok && fsSync.existsSync(projectPath)) await addRecent(projectPath);
    return { ...result, text, path: projectPath, data: data ? { ...data, review, reasoning } : data };
  });

  ipcMain.handle("beginner:pickMedia", async () => {
    const result = await dialog.showOpenDialog({
      title: "Select source video",
      filters: [{ name: "Video", extensions: videoImportExtensions }],
      properties: ["openFile"]
    });
    return result.canceled ? null : result.filePaths[0] || null;
  });

  ipcMain.handle("beginner:pickImageFolder", async () => pickFolder("Select image folder"));
  ipcMain.handle("beginner:pickAssetFolder", async () => pickFolder("Select product asset folder"));

  ipcMain.handle("beginner:pickMusic", async () => {
    const result = await dialog.showOpenDialog({
      title: "Select optional music",
      filters: [{ name: "Audio", extensions: audioImportExtensions }],
      properties: ["openFile"]
    });
    return result.canceled ? null : result.filePaths[0] || null;
  });

  ipcMain.handle("beginner:pickLogo", async () => {
    const result = await dialog.showOpenDialog({
      title: "Select optional logo",
      filters: [{ name: "Image", extensions: imageImportExtensions }],
      properties: ["openFile"]
    });
    return result.canceled ? null : result.filePaths[0] || null;
  });

  ipcMain.handle("beginner:autoTemplate", async (_event, payload: BeginnerAutoTemplatePayload) => {
    const safeName = slugify(payload.productName || "auto-video");
    const outputDir = path.join(generatedDir, `beginner-${safeName}-${Date.now()}`);
    const args = [
      "auto-template",
      "create",
      "--template",
      payload.template || "premium_product_showcase",
      "--product-name",
      payload.productName || "Untitled Product",
      "--goal",
      payload.goal || "Create a polished video",
      "--platform",
      payload.targetPlatform || "youtube",
      "--vibe",
      payload.vibe || "",
      "-o",
      outputDir
    ];
    if (payload.mediaFile) args.push("--media", payload.mediaFile);
    if (payload.imageFolder) args.push("--images", payload.imageFolder);
    if (payload.assetFolder) args.push("--assets", payload.assetFolder);
    if (payload.musicPath) args.push("--music", payload.musicPath);
    if (payload.logoPath) args.push("--logo", payload.logoPath);
    if (payload.duration) args.push("--duration", String(payload.duration));
    for (const feature of payload.keyFeatures || []) {
      if (feature.trim()) args.push("--feature", feature.trim());
    }
    if (payload.render !== false) args.push("--render");
    args.push("--quality", payload.quality || "preview");
    if (payload.cache !== false) args.push("--cache");
    const result = await runEngine(args);
    const projectPath = path.join(outputDir, "project.json");
    const summaryPath = path.join(outputDir, "beginner_auto_template_summary.json");
    const text = result.ok && fsSync.existsSync(projectPath) ? await fs.readFile(projectPath, "utf-8") : undefined;
    const data = result.ok ? await readJsonIfExists(summaryPath) : undefined;
    if (result.ok && fsSync.existsSync(projectPath)) await addRecent(projectPath);
    return { ...result, text, path: projectPath, data };
  });

  ipcMain.handle("engine:contentApprove", async (_event, payload: { planPath: string; section?: string | null; status?: string | null }) => {
    const args = ["content-review", "approve", payload.planPath, "--section", payload.section || "all", "--status", payload.status || "approved"];
    const result = await runEngine(args);
    const outputDir = path.dirname(payload.planPath);
    const reviewPath = path.join(outputDir, "generation_review.json");
    const review = result.ok && fsSync.existsSync(reviewPath) ? JSON.parse(await fs.readFile(reviewPath, "utf-8")) : undefined;
    return { ...result, data: review, path: reviewPath };
  });

  ipcMain.handle("engine:template", async (_event, payload: { template: string }) => {
    const output = tempProjectPath(`template-${payload.template}`);
    const result = await runEngine(["template", "create", payload.template, "-o", output]);
    const text = result.ok ? await fs.readFile(output, "utf-8") : undefined;
    return { ...result, text, path: output };
  });

  ipcMain.handle("engine:addCaptions", async (_event, payload: { text: string; transcriptPath: string; mode: string; style: string }) => {
    const input = await writeTempProject(payload.text, "captions-input");
    const output = tempProjectPath("captions-output");
    const result = await runEngine(["captions", input, payload.transcriptPath, "--mode", payload.mode, "--style", payload.style, "-o", output]);
    const text = result.ok ? await fs.readFile(output, "utf-8") : undefined;
    return { ...result, text, path: output };
  });

  ipcMain.handle("engine:director", async (_event, payload: { text: string; projectPath?: string | null; goal: string; preserve?: string[] }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "director-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = tempProjectPath("director-output");
    const args = ["director", input, payload.goal, "-o", output];
    if (payload.preserve?.length) args.push("--preserve", ...payload.preserve);
    const result = await runEngine(args);
    const text = result.ok ? await fs.readFile(output, "utf-8") : undefined;
    const reportPath = output.replace(/\.json$/i, ".director_report.json");
    const report = result.ok && fsSync.existsSync(reportPath) ? JSON.parse(await fs.readFile(reportPath, "utf-8")) : undefined;
    return { ...result, text, path: output, report };
  });

  ipcMain.handle("engine:storyboard", async (_event, payload: { text: string; projectPath?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "storyboard-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const outputDir = path.join(tempDir, `storyboard-${Date.now()}`);
    const result = await runEngine(["storyboard", input, "-o", outputDir]);
    const storyboardPath = path.join(outputDir, "storyboard.json");
    const data = result.ok && fsSync.existsSync(storyboardPath) ? JSON.parse(await fs.readFile(storyboardPath, "utf-8")) : undefined;
    return { ...result, data, path: storyboardPath };
  });

  ipcMain.handle("engine:assetAnalyze", async (_event, payload: { text: string; projectPath?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "asset-analysis-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `asset-intelligence-${Date.now()}.json`);
    const result = await runEngine(["asset-analyze", input, "-o", output]);
    const data = fsSync.existsSync(output) ? JSON.parse(await fs.readFile(output, "utf-8")) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("engine:resolveBroll", async (_event, payload: { text: string; projectPath?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "broll-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = tempProjectPath("broll-output");
    const result = await runEngine(["resolve-broll", input, "-o", output]);
    const text = result.ok ? await fs.readFile(output, "utf-8") : undefined;
    return { ...result, text, path: output };
  });

  ipcMain.handle("transcript:pick", async () => {
    const result = await dialog.showOpenDialog({
      title: "Choose transcript",
      filters: [{ name: "Transcript", extensions: ["txt", "srt", "vtt"] }],
      properties: ["openFile"]
    });
    return result.canceled ? null : result.filePaths[0] || null;
  });

  ipcMain.handle("assets:import", async (_event, payload: { projectPath?: string | null }) => {
    const result = await dialog.showOpenDialog({
      title: "Import assets",
      filters: [{ name: "Media", extensions: allMediaImportExtensions }],
      properties: ["openFile", "multiSelections"]
    });
    if (result.canceled) return [];

    const projectDir = payload.projectPath ? path.dirname(payload.projectPath) : generatedDir;
    const reportPath = path.join(projectDir, ".ave_media", `media_import_${Date.now()}.json`);
    const engineResult = await runEngine([
      "media",
      "import",
      ...result.filePaths,
      "--project-dir",
      projectDir,
      "--normalize",
      "auto",
      "-o",
      reportPath
    ]);
    if (!engineResult.ok) throw new Error(engineResult.stderr || engineResult.stdout || "Media import failed");
    const report = await readJsonIfExists(reportPath) as { imported?: Array<Record<string, unknown>> } | null;
    return (report?.imported || []).map((item) => ({
      key: String(item.assetKey || "asset"),
      path: String(item.projectPath || item.activePath || ""),
      type: mediaType(String(item.activePath || item.projectPath || ""))
    })).filter((item) => item.path);
  });

  ipcMain.handle("assets:check", async (_event, payload: { text: string; projectPath?: string | null }) => {
    return checkAssets(payload.text, payload.projectPath || null);
  });

  ipcMain.handle("history:list", async (_event, payload: { projectPath?: string | null }) => {
    if (!payload.projectPath) return [];
    return readHistory(payload.projectPath);
  });

  ipcMain.handle("history:rollback", async (_event, payload: { projectPath: string; versionId: string }) => {
    const result = await runEngine(["history", "rollback", payload.projectPath, payload.versionId]);
    if (!result.ok) throw new Error(result.stderr || result.stdout || "Rollback failed");
    return readProjectFile(payload.projectPath);
  });

  ipcMain.handle("package:export", async (_event, payload: { text: string; projectPath?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "package-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const result = await dialog.showSaveDialog({
      title: "Export project package",
      defaultPath: path.join(outputRoot, "project.avepkg.zip"),
      filters: [{ name: "AVE Package", extensions: ["zip"] }]
    });
    if (result.canceled || !result.filePath) return { ok: false, stdout: "Package export canceled.", stderr: "", exitCode: 0 };
    const engineResult = await runEngine(["package", "export", input, "-o", result.filePath]);
    const data = engineResult.ok ? { packagePath: result.filePath } : undefined;
    return { ...engineResult, data, path: result.filePath };
  });

  ipcMain.handle("package:open", async () => {
    const result = await dialog.showOpenDialog({
      title: "Open project package",
      filters: [{ name: "AVE Package", extensions: ["zip"] }],
      properties: ["openFile"]
    });
    if (result.canceled || !result.filePaths[0]) return null;
    const target = path.join(generatedDir, path.basename(result.filePaths[0], ".zip"));
    const engineResult = await runEngine(["package", "open", result.filePaths[0], "-o", target]);
    if (!engineResult.ok) throw new Error(engineResult.stderr || engineResult.stdout || "Package open failed");
    return readProjectFile(path.join(target, "project.json"));
  });

  ipcMain.handle("plugin:list", async () => {
    return readPlugins();
  });

  ipcMain.handle("plugin:init", async (_event, payload: { name: string; type: string }) => {
    const result = await runEngine(["plugin", "init", payload.name, payload.type]);
    if (!result.ok) throw new Error(result.stderr || result.stdout || "Plugin creation failed");
    const plugins = await readPlugins();
    return plugins.find((plugin) => plugin.id === safeAssetKey(payload.name)) || plugins[0];
  });

  ipcMain.handle("engine:realtimePreview", async (_event, payload: { text: string; projectPath?: string | null; time?: number; sceneId?: string | null; qualityMode?: string; layerMode?: string }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "realtime-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const outputDir = path.join(tempDir, "realtime-preview");
    const args = ["realtime-preview", input, "-o", outputDir];
    if (typeof payload.time === "number") args.push("--time", String(payload.time));
    if (payload.sceneId) args.push("--scene", payload.sceneId);
    if (payload.qualityMode) args.push("--mode", payload.qualityMode);
    if (payload.layerMode) args.push("--layers", payload.layerMode);
    const result = await runEngine(args);
    const reportPath = path.join(outputDir, "realtime_preview.json");
    const data = result.ok && fsSync.existsSync(reportPath) ? JSON.parse(await fs.readFile(reportPath, "utf-8")) : undefined;
    return { ...result, data, path: reportPath };
  });

  ipcMain.handle("engine:interactivePreview", async (_event, payload: { text: string; projectPath?: string | null; qualityMode?: string; scope?: string; sceneId?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "interactive-preview-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const outputDir = path.join(tempDir, "interactive-preview");
    const args = [
      "interactive-preview",
      input,
      "-o",
      outputDir,
      "--quality-mode",
      payload.qualityMode || "balanced",
      "--scope",
      payload.scope || "full"
    ];
    if (payload.sceneId) args.push("--scene-id", payload.sceneId);
    const result = await runEngine(args);
    const reportPath = path.join(outputDir, "interactive_preview.json");
    const data = result.ok && fsSync.existsSync(reportPath) ? JSON.parse(await fs.readFile(reportPath, "utf-8")) : undefined;
    return { ...result, data, path: data?.previewVideo || reportPath };
  });

  ipcMain.handle("engine:qualityCheck", async (_event, payload: { text: string; projectPath?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "quality-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `quality-${Date.now()}.json`);
    const result = await runEngine(["quality-check", input, "-o", output]);
    const data = fsSync.existsSync(output) ? JSON.parse(await fs.readFile(output, "utf-8")) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("engine:finalPreflight", async (_event, payload: { text: string; projectPath?: string | null; previewVideo?: string | null; format?: string }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "final-preflight-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `final-preflight-${Date.now()}.json`);
    const args = ["final-preflight", "check", input, "-o", output, "--format", payload.format || "mp4"];
    if (payload.previewVideo) args.push("--preview-video", payload.previewVideo);
    const result = await runEngine(args);
    const data = fsSync.existsSync(output) ? JSON.parse(await fs.readFile(output, "utf-8")) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("engine:repairPreflight", async (_event, payload: { text: string; projectPath?: string | null; previewVideo?: string | null; format?: string; mode?: string; issueId?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "final-preflight-repair-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = tempProjectPath("final-preflight-repaired");
    const args = ["final-preflight", "repair", input, "-o", output, "--format", payload.format || "mp4", "--mode", payload.mode || "all"];
    if (payload.previewVideo) args.push("--preview-video", payload.previewVideo);
    if (payload.issueId) args.push("--issue-id", payload.issueId);
    const result = await runEngine(args);
    const text = fsSync.existsSync(output) ? await fs.readFile(output, "utf-8") : undefined;
    const data = text ? JSON.parse(text) : undefined;
    return { ...result, data, text, path: output };
  });

  ipcMain.handle("engine:manifest", async (_event, payload: { text: string; projectPath?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "manifest-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `project-manifest-${Date.now()}.json`);
    const result = await runEngine(["manifest", input, "-o", output]);
    const data = fsSync.existsSync(output) ? JSON.parse(await fs.readFile(output, "utf-8")) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("engine:reformat", async (_event, payload: { text: string; projectPath?: string | null; targets: string[] }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "reformat-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const outputDir = path.join(generatedDir, "desktop_social_reformats");
    const result = await runEngine(["reformat", input, "--targets", ...(payload.targets.length ? payload.targets : ["all"]), "-o", outputDir]);
    return { ...result, data: { outputDir }, path: outputDir };
  });

  ipcMain.handle("engine:repurpose", async (_event, payload: { text: string; projectPath?: string | null; targets?: string[] | null; hooks?: string[] | null; ctas?: string[] | null; reuseStyle?: boolean | null; render?: boolean | null; package?: boolean | null; quality?: "preview" | "final"; maxVariants?: number | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "repurpose-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const outputDir = path.join(generatedDir, `repurposed-${Date.now()}`);
    const args = ["repurpose", input, "--platforms", ...((payload.targets?.length ? payload.targets : ["all"])), "-o", outputDir, "--quality", payload.quality || "preview"];
    for (const hook of payload.hooks || ["all"]) args.push("--hook", hook);
    for (const cta of payload.ctas || ["all"]) args.push("--cta", cta);
    if (payload.reuseStyle === false) args.push("--no-reuse-style");
    if (payload.maxVariants) args.push("--max-variants", String(payload.maxVariants));
    if (payload.render) args.push("--render");
    if (payload.package) args.push("--package");
    const result = await runEngine(args);
    const summaryPath = path.join(outputDir, "repurpose_summary.json");
    const data = result.ok && fsSync.existsSync(summaryPath) ? JSON.parse(await fs.readFile(summaryPath, "utf-8")) : undefined;
    return { ...result, data, path: outputDir };
  });

  ipcMain.handle("engine:postPackage", async (_event, payload: { text: string; projectPath?: string | null; videoPath: string; targets: string[]; title?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "post-package-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const outputDir = path.join(exportsRoot, `posting-package-${Date.now()}`);
    const args = ["post-package", input, payload.videoPath, "--platforms", ...(payload.targets.length ? payload.targets : ["all"]), "-o", outputDir];
    if (payload.title) args.push("--title", payload.title);
    const result = await runEngine(args);
    const summaryPath = path.join(outputDir, "posting_package_summary.json");
    const data = result.ok && fsSync.existsSync(summaryPath) ? JSON.parse(await fs.readFile(summaryPath, "utf-8")) : undefined;
    return { ...result, data, path: outputDir };
  });

  ipcMain.handle("postExport:review", async (_event, payload: { text: string; projectPath?: string | null; videoPath: string; packageDir?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "post-export-review-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `post-export-review-${Date.now()}.json`);
    const args = ["post-export", "review", input, payload.videoPath, "-o", output];
    if (payload.packageDir) args.push("--package-dir", payload.packageDir);
    const result = await runEngine(args);
    const data = fsSync.existsSync(output) ? JSON.parse(await fs.readFile(output, "utf-8")) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("postExport:reexport", async (_event, payload: { text: string; projectPath?: string | null; preset?: string | null; mode?: string | null; format?: string | null; captions?: string | null; thumbnail?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "post-export-reexport-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const outputDir = path.join(generatedDir, `post-export-reexport-${Date.now()}`);
    const args = ["post-export", "reexport", input, "-o", outputDir, "--mode", payload.mode || "custom", "--format", payload.format || "mp4", "--captions", payload.captions || "keep"];
    if (payload.preset) args.push("--preset", payload.preset);
    if (payload.thumbnail) args.push("--thumbnail", payload.thumbnail);
    const result = await runEngine(args);
    const data = result.ok ? await readJsonIfExists(path.join(outputDir, "quick_reexport_summary.json")) : undefined;
    const projectPath = typeof data?.outputProject === "string" ? data.outputProject : null;
    const text = projectPath && fsSync.existsSync(projectPath) ? await fs.readFile(projectPath, "utf-8") : undefined;
    return { ...result, data, text, path: projectPath || outputDir };
  });

  ipcMain.handle("postExport:template", async (_event, payload: { text: string; projectPath?: string | null; videoPath?: string | null; name: string; note?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "post-export-template-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(engineRoot, "templates", "reusable", `${slugify(payload.name || "reusable-template")}.reuse-template.json`);
    const args = ["post-export", "template", input, "--name", payload.name || "Reusable Template", "-o", output];
    if (payload.videoPath) args.push("--video", payload.videoPath);
    if (payload.note) args.push("--note", payload.note);
    const result = await runEngine(args);
    const data = fsSync.existsSync(output) ? JSON.parse(await fs.readFile(output, "utf-8")) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("postExport:variants", async (_event, payload: { text: string; projectPath?: string | null; variants?: string[] | null; hook?: string | null; cta?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "post-export-variants-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const outputDir = path.join(generatedDir, `post-export-variants-${Date.now()}`);
    const args = ["post-export", "variants", input, "-o", outputDir];
    for (const variant of payload.variants || []) args.push("--variant", variant);
    if (payload.hook) args.push("--hook", payload.hook);
    if (payload.cta) args.push("--cta", payload.cta);
    const result = await runEngine(args);
    const data = result.ok ? await readJsonIfExists(path.join(outputDir, "post_export_variants.json")) : undefined;
    return { ...result, data, path: outputDir };
  });

  ipcMain.handle("postExport:note", async (_event, payload: { text: string; projectPath?: string | null; videoPath?: string | null; profile?: string | null; tags?: string[] | null; note?: string | null }) => {
    const input = payload.projectPath || await writeTempProject(payload.text, "post-export-note-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const args = ["post-export", "note", input, "--profile", payload.profile || "Default Creator"];
    if (payload.videoPath) args.push("--video", payload.videoPath);
    for (const tag of payload.tags || []) args.push("--tag", tag);
    if (payload.note) args.push("--note", payload.note);
    const result = await runEngine(args);
    return { ...result, data: { stdout: result.stdout }, path: undefined };
  });

  ipcMain.handle("brand:init", async () => {
    const result = await dialog.showSaveDialog({
      title: "Create brand kit",
      defaultPath: path.join(generatedDir, "brand_kit.json"),
      filters: [{ name: "Brand Kit", extensions: ["json"] }]
    });
    if (result.canceled || !result.filePath) return { ok: false, stdout: "Brand kit creation canceled.", stderr: "", exitCode: 0 };
    const engineResult = await runEngine(["brand", "init", "-o", result.filePath]);
    const data = engineResult.ok ? JSON.parse(await fs.readFile(result.filePath, "utf-8")) : undefined;
    return { ...engineResult, data, path: result.filePath };
  });

  ipcMain.handle("brand:apply", async (_event, payload: { text: string; projectPath?: string | null }) => {
    const pick = await dialog.showOpenDialog({
      title: "Choose brand kit",
      filters: [{ name: "Brand Kit", extensions: ["json"] }],
      properties: ["openFile"]
    });
    if (pick.canceled || !pick.filePaths[0]) return { ok: false, stdout: "Brand kit apply canceled.", stderr: "", exitCode: 0 };
    const input = payload.projectPath || await writeTempProject(payload.text, "brand-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = tempProjectPath("brand-output");
    const result = await runEngine(["brand", "apply", input, pick.filePaths[0], "-o", output]);
    const text = result.ok ? await fs.readFile(output, "utf-8") : undefined;
    return { ...result, text, path: output };
  });

  ipcMain.handle("templatePack:list", async () => templatePackRows());

  ipcMain.handle("templatePack:export", async (_event, payload: { template: string }) => {
    const result = await dialog.showSaveDialog({
      title: "Export template pack",
      defaultPath: path.join(outputRoot, `${payload.template}.template-pack.zip`),
      filters: [{ name: "Template Pack", extensions: ["zip"] }]
    });
    if (result.canceled || !result.filePath) return { ok: false, stdout: "Template export canceled.", stderr: "", exitCode: 0 };
    const engineResult = await runEngine(["template-pack", "export", payload.template, "-o", result.filePath]);
    return { ...engineResult, data: { packagePath: result.filePath }, path: result.filePath };
  });

  ipcMain.handle("templatePack:install", async () => {
    const result = await dialog.showOpenDialog({
      title: "Install template pack",
      filters: [{ name: "Template Pack", extensions: ["zip"] }],
      properties: ["openFile"]
    });
    if (result.canceled || !result.filePaths[0]) return { ok: false, stdout: "Template install canceled.", stderr: "", exitCode: 0 };
    const engineResult = await runEngine(["template-pack", "install", result.filePaths[0]]);
    return { ...engineResult, data: { packagePath: result.filePaths[0] } };
  });

  ipcMain.handle("settings:get", async () => readSettings());

  ipcMain.handle("settings:save", async (_event, settings: unknown) => {
    const next = { ...defaultSettings(), ...(settings as Record<string, unknown>) };
    await fs.mkdir(userDataDir, { recursive: true });
    await fs.writeFile(settingsPath, JSON.stringify(next, null, 2), "utf-8");
    const keys = settings && typeof settings === "object" ? Object.keys(settings as Record<string, unknown>) : [];
    await logFrictionEvent({ event: "settings_changed", label: "settings", keys });
    return next;
  });

  ipcMain.handle("friction:log", async (_event, payload: FrictionEvent) => logFrictionEvent(payload));

  ipcMain.handle("friction:report", async () => readFrictionReport());

  ipcMain.handle("recovery:autosave", async (_event, payload: { text: string; projectPath?: string | null }) => {
    if (!payload.text.trim()) return null;
    const projectId = payload.projectPath ? safeAssetKey(payload.projectPath) : "unsaved";
    const dir = path.join(userDataDir, "recovery", projectId);
    await fs.mkdir(dir, { recursive: true });
    const filePath = path.join(dir, `autosave-${Date.now()}.json`);
    await fs.writeFile(filePath, payload.text, "utf-8");
    return { type: "autosave", path: filePath, timestamp: new Date().toISOString(), size: Buffer.byteLength(payload.text) };
  });

  ipcMain.handle("recovery:list", async (_event, payload: { projectPath?: string | null }) => {
    const projectId = payload.projectPath ? safeAssetKey(payload.projectPath) : "unsaved";
    const dir = path.join(userDataDir, "recovery", projectId);
    return readRecoveryPoints(dir);
  });

  ipcMain.handle("recovery:restore", async (_event, payload: { sourcePath: string; targetPath?: string | null }) => {
    const text = await fs.readFile(payload.sourcePath, "utf-8");
    const target = payload.targetPath || path.join(generatedDir, "recovered_project.json");
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, text, "utf-8");
    await addRecent(target);
    return readProjectFile(target);
  });

  ipcMain.handle("phase10:status", async () => {
    await fs.mkdir(tempDir, { recursive: true });
    const stamp = Date.now();
    const dependencyPath = path.join(tempDir, `dependency-${stamp}.json`);
    const modelPath = path.join(tempDir, `models-${stamp}.json`);
    const privacyPath = path.join(tempDir, `privacy-${stamp}.json`);
    const performancePath = path.join(tempDir, `performance-${stamp}.json`);
    await runEngine(["dependency-check", "-o", dependencyPath]);
    await runEngine(["model-manager", "status", "-o", modelPath]);
    await runEngine(["privacy-report", "-o", privacyPath]);
    await runEngine(["performance-report", "-o", performancePath]);
    return {
      generatedAt: new Date().toISOString(),
      docsPath: path.join(engineRoot, "docs"),
      dependency: await readJsonIfExists(dependencyPath),
      model: await readJsonIfExists(modelPath),
      privacy: await readJsonIfExists(privacyPath),
      performance: await readJsonIfExists(performancePath)
    };
  });

  ipcMain.handle("workflow:dashboard", async (_event, payload: { text: string; projectPath?: string | null }) => {
    await fs.mkdir(tempDir, { recursive: true });
    const input = payload.projectPath || await writeTempProject(payload.text, "workflow-dashboard-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `workflow-dashboard-${Date.now()}.json`);
    const result = await runEngine(["workflow", "dashboard", "--project", input, "-o", output]);
    const data = result.ok ? await readJsonIfExists(output) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("workflow:adaptiveMemory", async (_event, payload: { text?: string | null; projectPath?: string | null; profile?: string | null }) => {
    return buildAdaptiveWorkflowMemory(payload || {});
  });

  ipcMain.handle("workflow:adaptiveRecord", async (_event, payload: AdaptiveWorkflowEvent) => {
    return recordAdaptiveWorkflowEvent(payload || { event: "unknown" });
  });

  ipcMain.handle("feedback:analyze", async (_event, payload: { text: string; projectPath?: string | null; videoPath?: string | null }) => {
    await fs.mkdir(tempDir, { recursive: true });
    const input = payload.projectPath || await writeTempProject(payload.text, "feedback-analyze-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `feedback-analysis-${Date.now()}.json`);
    const args = ["feedback", "analyze", input, "-o", output];
    if (payload.videoPath) args.push("--video", payload.videoPath);
    const result = await runEngine(args);
    const data = result.ok ? await readJsonIfExists(output) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("feedback:review", async (_event, payload: { text: string; projectPath?: string | null; videoPath?: string | null; profile?: string | null; note?: string | null; ratings?: Record<string, number> }) => {
    await fs.mkdir(tempDir, { recursive: true });
    const input = payload.projectPath || await writeTempProject(payload.text, "feedback-review-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `feedback-review-${Date.now()}.json`);
    const args = ["feedback", "review", input, "--profile", payload.profile || "Default Creator", "-o", output];
    if (payload.videoPath) args.push("--video", payload.videoPath);
    if (payload.note) args.push("--note", payload.note);
    const ratings = payload.ratings || {};
    const ratingMap: Array<[string, string]> = [
      ["pacing", "--pacing"],
      ["readability", "--readability"],
      ["transitions", "--transitions"],
      ["cinematicQuality", "--cinematic"],
      ["hookStrength", "--hook"],
      ["captionQuality", "--captions"],
      ["overallPolish", "--polish"]
    ];
    for (const [key, flag] of ratingMap) {
      if (ratings[key] !== undefined) args.push(flag, String(ratings[key]));
    }
    const result = await runEngine(args);
    const data = result.ok ? await readJsonIfExists(output) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("feedback:learn", async (_event, payload: { profile: string }) => {
    await fs.mkdir(tempDir, { recursive: true });
    const output = path.join(tempDir, `creator-identity-${Date.now()}.json`);
    const result = await runEngine(["feedback", "learn", payload.profile || "Default Creator", "-o", output]);
    const data = result.ok ? await readJsonIfExists(output) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("evolution:report", async (_event, payload: { text: string; projectPath?: string | null; profile?: string | null; includeReleaseCheck?: boolean }) => {
    await fs.mkdir(tempDir, { recursive: true });
    const input = payload.projectPath || await writeTempProject(payload.text, "evolution-input");
    if (payload.projectPath) await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    const output = path.join(tempDir, `evolution-report-${Date.now()}.json`);
    const args = ["evolution-report", "--project", input, "--profile", payload.profile || "Default Creator", "-o", output];
    if (payload.includeReleaseCheck) args.push("--include-release-check");
    const result = await runEngine(args);
    const data = result.ok ? await readJsonIfExists(output) : undefined;
    return { ...result, data, path: output };
  });

  ipcMain.handle("docs:open", async () => {
    await shell.openPath(path.join(engineRoot, "docs"));
  });

  ipcMain.handle("render:start", async (_event, payload: RenderPayload) => {
    return enqueueRender(payload);
  });

  ipcMain.handle("render:queue", async () => serializeQueue());

  ipcMain.handle("render:pause", async () => {
    renderQueuePaused = true;
    broadcastQueue();
    return serializeQueue();
  });

  ipcMain.handle("render:resume", async () => {
    renderQueuePaused = false;
    processRenderQueue();
    broadcastQueue();
    return serializeQueue();
  });

  ipcMain.handle("render:cancel", async (_event, payload: { runId: string }) => {
    cancelRender(payload.runId);
    return serializeQueue();
  });

  ipcMain.handle("render:retry", async (_event, payload: { runId: string }) => {
    retryRender(payload.runId);
    return serializeQueue();
  });

  ipcMain.handle("render:priority", async (_event, payload: { runId: string; priority: number }) => {
    const job = renderQueue.find((item) => item.runId === payload.runId);
    if (job && job.status === "queued") {
      job.priority = payload.priority;
      sortRenderQueue();
    }
    broadcastQueue();
    return serializeQueue();
  });

  ipcMain.handle("shell:reveal", async (_event, filePath: string) => {
    shell.showItemInFolder(filePath);
  });

  ipcMain.handle("shell:openOutput", async () => {
    await shell.openPath(outputRoot);
  });
}

async function readProjectFile(filePath: string) {
  const text = await fs.readFile(filePath, "utf-8");
  await addRecent(filePath);
  return { path: filePath, text, name: path.basename(filePath) };
}

async function enqueueRender(payload: RenderPayload) {
  const runId = crypto.randomUUID();
  const input = payload.projectPath || await writeTempProject(payload.text, `render-${runId}`);
  if (payload.projectPath) {
    await fs.writeFile(payload.projectPath, payload.text, "utf-8");
    await addRecent(payload.projectPath);
  }
  const requestedFormat = payload.format || "mp4";
  const extension = requestedFormat === "image_sequence" ? "png" : requestedFormat;
  const outputName = requestedFormat === "image_sequence"
    ? `${payload.quality === "preview" ? "desktop_preview" : "desktop_final"}_%05d.${extension}`
    : `${payload.quality === "preview" ? "desktop_preview" : "desktop_final"}.${extension}`;
  const outputPath = payload.outputPath || path.join(outputRoot, outputName);
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const args = ["render", input, "-o", outputPath, "--quality", payload.quality];
  if (payload.preset) args.push("--preset", payload.preset);
  if (payload.format) args.push("--format", payload.format);
  if (payload.generatePlaceholders) args.push("--generate-placeholders");
  if (payload.cache) args.push("--cache");
  if (payload.resume) args.push("--resume");
  if (payload.gpu) args.push("--gpu");

  const job: QueuedRenderJob = {
    runId,
    label: payload.label || (payload.quality === "preview" ? "Preview render" : "Final render"),
    input,
    outputPath,
    args,
    payload,
    status: "queued",
    priority: Number(payload.priority || 0),
    logs: [],
    progressPercent: 0,
    packageStatus: payload.createDeliveryPackage ? "pending" : undefined,
    sceneCount: estimateSceneCount(payload.text),
    completedScenes: 0
  };
  renderQueue.push(job);
  sortRenderQueue();
  broadcastQueue();
  processRenderQueue();
  return { runId, outputPath };
}

function processRenderQueue() {
  if (renderQueuePaused || activeRender) return;
  const job = renderQueue.find((item) => item.status === "queued");
  if (!job) return;
  activeRender = job;
  job.status = "running";
  job.startedAt = Date.now();
  job.progressPercent = Math.max(job.progressPercent || 0, 2);
  broadcastQueue();
  const child = spawn(pythonBinary, [renderPy, ...job.args], { cwd: engineRoot, windowsHide: true });
  job.child = child;
  child.stdout.on("data", (chunk: Buffer) => collectRenderLog(job, chunk.toString(), "stdout"));
  child.stderr.on("data", (chunk: Buffer) => collectRenderLog(job, chunk.toString(), "stderr"));
  child.on("close", async (exitCode) => {
    job.exitCode = exitCode;
    job.status = job.status === "canceled" ? "canceled" : exitCode === 0 ? "completed" : "failed";
    if (job.status === "completed") job.progressPercent = 100;
    job.child = undefined;
    if (job.status === "completed" && job.payload.quality === "final" && job.payload.createDeliveryPackage) {
      await createDeliveryPackageForJob(job);
    }
    activeRender = null;
    mainWindow?.webContents.send("render:complete", { runId: job.runId, exitCode, outputPath: job.outputPath, packagePath: job.packagePath });
    broadcastQueue();
    processRenderQueue();
  });
}

function collectRenderLog(job: QueuedRenderJob, text: string, stream: "stdout" | "stderr") {
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    job.logs = [...job.logs.slice(-120), line];
    updateRenderProgress(job, line);
    mainWindow?.webContents.send("render:log", { runId: job.runId, line, stream });
  }
  broadcastQueue();
}

async function createDeliveryPackageForJob(job: QueuedRenderJob) {
  job.packageStatus = "running";
  job.packageError = undefined;
  broadcastQueue();
  const packageDir = path.join(exportsRoot, `${safePackageName(job)}-${Date.now()}`);
  const renderLogPath = path.join(path.dirname(job.outputPath), `${job.runId}-render_logs.txt`);
  await fs.mkdir(path.dirname(renderLogPath), { recursive: true });
  await fs.writeFile(renderLogPath, job.logs.join("\n") + "\n", "utf-8");
  const platforms = job.payload.packagePlatforms?.length ? job.payload.packagePlatforms : platformsForPreset(job.payload.preset);
  const args = ["post-package", job.input, job.outputPath, "--platforms", ...platforms, "-o", packageDir, "--render-logs", renderLogPath];
  if (job.payload.packageTitle) args.push("--title", job.payload.packageTitle);
  const renderReportPath = path.join(path.dirname(job.outputPath), "render_report.json");
  if (fsSync.existsSync(renderReportPath)) args.push("--render-report", renderReportPath);
  const result = await runEngine(args);
  for (const line of `${result.stdout}\n${result.stderr}`.split(/\r?\n/)) {
    if (line.trim()) {
      job.logs = [...job.logs.slice(-120), line];
      mainWindow?.webContents.send("render:log", { runId: job.runId, line, stream: "stdout" });
    }
  }
  if (result.ok) {
    job.packageStatus = "completed";
    job.packagePath = packageDir;
  } else {
    job.packageStatus = "failed";
    job.packageError = result.stderr || result.stdout || "Delivery package failed.";
  }
  broadcastQueue();
}

function updateRenderProgress(job: QueuedRenderJob, line: string) {
  const lower = line.toLowerCase();
  const sceneMatch = line.match(/(?:Rendering scene|Using cached scene) '([^']+)'/i);
  if (sceneMatch) {
    job.currentScene = sceneMatch[1];
    job.completedScenes = Math.min(job.sceneCount || 1, (job.completedScenes || 0) + 1);
    const sceneRatio = (job.completedScenes || 0) / Math.max(1, job.sceneCount || 1);
    job.progressPercent = Math.max(job.progressPercent || 0, Math.round(8 + sceneRatio * 58));
  } else if (lower.includes("rendering scenes")) {
    job.progressPercent = Math.max(job.progressPercent || 0, 6);
  } else if (lower.includes("applying transitions")) {
    job.currentScene = "transitions";
    job.progressPercent = Math.max(job.progressPercent || 0, 72);
  } else if (lower.includes("rendering audio")) {
    job.currentScene = "audio mix";
    job.progressPercent = Math.max(job.progressPercent || 0, 82);
  } else if (lower.includes("exporting")) {
    job.currentScene = "export";
    job.progressPercent = Math.max(job.progressPercent || 0, 92);
  } else if (lower.includes("export complete")) {
    job.currentScene = "complete";
    job.progressPercent = 100;
  }
  if (job.startedAt && job.progressPercent && job.progressPercent > 1 && job.progressPercent < 100) {
    const elapsed = (Date.now() - job.startedAt) / 1000;
    const totalEstimate = elapsed / (job.progressPercent / 100);
    job.estimatedRemainingSeconds = Math.max(0, Math.round(totalEstimate - elapsed));
  } else if (job.progressPercent === 100) {
    job.estimatedRemainingSeconds = 0;
  }
}

function estimateSceneCount(text: string) {
  try {
    const project = JSON.parse(text) as { timeline?: Array<{ excludeFromFinal?: boolean }> };
    return Math.max(1, (project.timeline || []).filter((scene) => !scene.excludeFromFinal).length);
  } catch {
    return 1;
  }
}

function platformsForPreset(preset?: string | null) {
  const value = preset || "youtube_1080p";
  if (value === "shorts") return ["youtube_shorts"];
  if (value === "tiktok_reels") return ["tiktok"];
  if (value === "instagram_reels") return ["instagram_reels"];
  if (value === "discord_720p") return ["discord"];
  if (value === "high_quality_archive" || value === "cinematic_4k") return ["high_quality_archive"];
  return ["youtube_landscape"];
}

function safePackageName(job: QueuedRenderJob) {
  try {
    const project = JSON.parse(fsSync.readFileSync(job.input, "utf-8")) as {
      metadata?: { productName?: string; title?: string; contentGenerator?: { contentBrief?: { productName?: string } } };
    };
    return slugify(
      project.metadata?.contentGenerator?.contentBrief?.productName
      || project.metadata?.productName
      || project.metadata?.title
      || path.basename(job.input, path.extname(job.input))
    );
  } catch {
    return slugify(path.basename(job.input, path.extname(job.input)));
  }
}

function cancelRender(runId: string) {
  const job = renderQueue.find((item) => item.runId === runId);
  if (!job) return;
  if (job.status === "running" && job.child) {
    job.status = "canceled";
    job.child.kill();
  } else if (job.status === "queued") {
    job.status = "canceled";
  }
  broadcastQueue();
}

function retryRender(runId: string) {
  const job = renderQueue.find((item) => item.runId === runId);
  if (!job || !["failed", "canceled", "completed"].includes(job.status)) return;
  job.status = "queued";
  job.exitCode = undefined;
  job.logs = [];
  job.progressPercent = 0;
  job.currentScene = undefined;
  job.estimatedRemainingSeconds = undefined;
  job.packagePath = undefined;
  job.packageError = undefined;
  job.packageStatus = job.payload.createDeliveryPackage ? "pending" : undefined;
  job.completedScenes = 0;
  sortRenderQueue();
  broadcastQueue();
  processRenderQueue();
}

function sortRenderQueue() {
  renderQueue.sort((a, b) => {
    if (a.status === "running") return -1;
    if (b.status === "running") return 1;
    if (a.status !== b.status) {
      const rank = { queued: 0, failed: 1, canceled: 2, completed: 3, running: -1 };
      return rank[a.status] - rank[b.status];
    }
    return b.priority - a.priority;
  });
}

function serializeQueue() {
  return renderQueue.map((job) => ({
    runId: job.runId,
    label: job.label,
    outputPath: job.outputPath,
    status: job.status,
    priority: job.priority,
    exitCode: job.exitCode,
    currentScene: job.currentScene,
    progressPercent: job.progressPercent || 0,
    estimatedRemainingSeconds: job.estimatedRemainingSeconds,
    packagePath: job.packagePath,
    packageStatus: job.packageStatus,
    packageError: job.packageError,
    sceneCount: job.sceneCount,
    completedScenes: job.completedScenes
  }));
}

function broadcastQueue() {
  mainWindow?.webContents.send("render:queue", serializeQueue());
}

async function runEngine(args: string[]): Promise<EngineResult> {
  return new Promise((resolve) => {
    const child = spawn(pythonBinary, [renderPy, ...args], { cwd: engineRoot, windowsHide: true });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on("close", (exitCode) => {
      resolve({ ok: exitCode === 0, stdout, stderr, exitCode });
    });
  });
}

async function readJsonIfExists(filePath: string) {
  if (!fsSync.existsSync(filePath)) return null;
  return JSON.parse(await fs.readFile(filePath, "utf-8"));
}

async function pickFolder(title: string) {
  const result = await dialog.showOpenDialog({
    title,
    properties: ["openDirectory"]
  });
  return result.canceled ? null : result.filePaths[0] || null;
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40) || "auto-video";
}

async function writeTempProject(text: string, prefix: string) {
  await fs.mkdir(tempDir, { recursive: true });
  const filePath = path.join(tempDir, `${prefix}-${Date.now()}.json`);
  await fs.writeFile(filePath, text, "utf-8");
  return filePath;
}

function tempProjectPath(prefix: string) {
  return path.join(tempDir, `${prefix}-${Date.now()}.json`);
}

async function readRecent(): Promise<RecentProject[]> {
  try {
    const text = await fs.readFile(recentPath, "utf-8");
    return JSON.parse(text);
  } catch {
    return [];
  }
}

async function addRecent(filePath: string) {
  await fs.mkdir(userDataDir, { recursive: true });
  const existing = await readRecent();
  const next = [
    { path: filePath, name: path.basename(filePath), openedAt: new Date().toISOString() },
    ...existing.filter((item) => item.path !== filePath)
  ].slice(0, 12);
  await fs.writeFile(recentPath, JSON.stringify(next, null, 2), "utf-8");
}

function defaultSettings(): AppSettings {
  return {
    theme: "graphite",
    autosave: true,
    autosaveIntervalSeconds: 45,
    previewTimeSeconds: 1,
    keyboardShortcuts: true
  };
}

async function readSettings(): Promise<AppSettings> {
  try {
    const text = await fs.readFile(settingsPath, "utf-8");
    return { ...defaultSettings(), ...JSON.parse(text) };
  } catch {
    return defaultSettings();
  }
}

async function logFrictionEvent(payload: FrictionEvent) {
  const safeEvent = String(payload.event || "event").replace(/[^a-z0-9_:-]+/gi, "_").slice(0, 80);
  const item = {
    ...payload,
    event: safeEvent,
    label: payload.label ? String(payload.label).slice(0, 160) : undefined,
    createdAt: new Date().toISOString(),
    localOnly: true
  };
  await fs.mkdir(path.dirname(frictionLogPath), { recursive: true });
  await fs.appendFile(frictionLogPath, `${JSON.stringify(item)}\n`, "utf-8");
  return item;
}

async function readFrictionReport() {
  const events = await readFrictionEvents();
  const top = new Map<string, number>();
  for (const event of events) {
    const label = String(event.label || event.event || "event");
    top.set(label, (top.get(label) || 0) + 1);
  }
  const topLabels = [...top.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([label, count]) => ({ label, count }));
  return {
    eventCount: events.length,
    slowOperations: events.filter((event) => String(event.event) === "slow_operation").length,
    failedOperations: events.filter((event) => String(event.event).includes("failed")).length,
    repeatedSettings: events.filter((event) => String(event.event) === "settings_changed").length,
    recent: events.slice(-12).reverse(),
    topLabels,
    localOnly: true,
    path: frictionLogPath
  };
}

async function readFrictionEvents() {
  if (!fsSync.existsSync(frictionLogPath)) return [];
  const text = await fs.readFile(frictionLogPath, "utf-8");
  return text
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line) as Record<string, unknown>;
      } catch {
        return { event: "corrupt_friction_log_line", createdAt: new Date().toISOString(), line };
      }
    })
    .slice(-500);
}

async function readAdaptiveMemory(): Promise<AdaptiveWorkflowMemory> {
  const fallback: AdaptiveWorkflowMemory = {
    memoryVersion: 1,
    profile: "Default Creator",
    updatedAt: new Date(0).toISOString(),
    localOnly: true,
    path: adaptiveMemoryPath,
    events: [],
    preferences: {},
    smartDefaults: {},
    creatorFingerprint: {},
    recoverySignals: {},
    session: { recentPrompts: [], recentlyApprovedStyles: [], recentRegenerationBehavior: [] },
    contextSuggestions: [],
    friction: {}
  };
  try {
    if (!fsSync.existsSync(adaptiveMemoryPath)) return fallback;
    const parsed = JSON.parse(await fs.readFile(adaptiveMemoryPath, "utf-8")) as Partial<AdaptiveWorkflowMemory>;
    return {
      ...fallback,
      ...parsed,
      path: adaptiveMemoryPath,
      events: Array.isArray(parsed.events) ? parsed.events.slice(-500) : []
    };
  } catch {
    return {
      ...fallback,
      recoverySignals: {
        memoryRecovery: "Previous adaptive memory could not be read. A fresh local memory was started."
      }
    };
  }
}

async function writeAdaptiveMemory(memory: AdaptiveWorkflowMemory): Promise<AdaptiveWorkflowMemory> {
  const next = {
    ...memory,
    updatedAt: new Date().toISOString(),
    localOnly: true,
    path: adaptiveMemoryPath,
    events: memory.events.slice(-500)
  };
  await fs.mkdir(path.dirname(adaptiveMemoryPath), { recursive: true });
  await fs.writeFile(adaptiveMemoryPath, JSON.stringify(next, null, 2), "utf-8");
  return next;
}

async function recordAdaptiveWorkflowEvent(payload: AdaptiveWorkflowEvent): Promise<AdaptiveWorkflowMemory> {
  const memory = await readAdaptiveMemory();
  const signals = await workflowSignalsFromInputs(payload.text, payload.projectPath, payload.mediaPath || undefined);
  const event = {
    ...payload,
    event: sanitizeMemoryToken(payload.event || "event"),
    profile: payload.profile || memory.profile || "Default Creator",
    createdAt: new Date().toISOString(),
    localOnly: true,
    signals
  };
  const events = [...memory.events, event].slice(-500);
  const derived = await deriveAdaptiveWorkflowMemory({
    ...memory,
    profile: event.profile,
    events
  }, {
    text: payload.text,
    projectPath: payload.projectPath,
    profile: event.profile
  });
  return writeAdaptiveMemory(derived);
}

async function buildAdaptiveWorkflowMemory(payload: { text?: string | null; projectPath?: string | null; profile?: string | null }): Promise<AdaptiveWorkflowMemory> {
  const memory = await readAdaptiveMemory();
  const derived = await deriveAdaptiveWorkflowMemory({
    ...memory,
    profile: payload.profile || memory.profile || "Default Creator"
  }, payload);
  return writeAdaptiveMemory(derived);
}

async function deriveAdaptiveWorkflowMemory(
  memory: AdaptiveWorkflowMemory,
  payload: { text?: string | null; projectPath?: string | null; profile?: string | null }
): Promise<AdaptiveWorkflowMemory> {
  const [currentSignals, recentSignals, frictionEvents] = await Promise.all([
    workflowSignalsFromInputs(payload.text, payload.projectPath),
    workflowSignalsFromRecentProjects(),
    readFrictionEvents()
  ]);
  const eventSignals = memory.events.map((event) => event.signals as WorkflowSignals | undefined).filter(Boolean) as WorkflowSignals[];
  const allSignals = [currentSignals, ...eventSignals, ...recentSignals].filter(Boolean) as WorkflowSignals[];
  const preferences = deriveWorkflowPreferences(memory.events, allSignals);
  const recoverySignals = deriveRecoverySignals(memory.events, frictionEvents);
  const session = deriveSessionContinuity(memory.events, payload.projectPath);
  return {
    ...memory,
    profile: payload.profile || memory.profile || "Default Creator",
    preferences,
    smartDefaults: deriveSmartDefaults(preferences, currentSignals),
    creatorFingerprint: deriveCreatorFingerprint(preferences, recoverySignals, allSignals),
    recoverySignals,
    session,
    contextSuggestions: deriveContextSuggestions(currentSignals, preferences, recoverySignals),
    friction: summarizeFrictionForMemory(frictionEvents),
    updatedAt: new Date().toISOString(),
    localOnly: true,
    path: adaptiveMemoryPath
  };
}

async function workflowSignalsFromRecentProjects(): Promise<WorkflowSignals[]> {
  const recent = await readRecent();
  const signals: WorkflowSignals[] = [];
  for (const item of recent.slice(0, 8)) {
    try {
      if (!fsSync.existsSync(item.path)) continue;
      const text = await fs.readFile(item.path, "utf-8");
      signals.push(await workflowSignalsFromInputs(text, item.path));
    } catch {
      // Recent projects are advisory only; bad entries should not block the app.
    }
  }
  return signals;
}

async function workflowSignalsFromInputs(text?: string | null, projectPath?: string | null, mediaPath?: string | null): Promise<WorkflowSignals> {
  const signals: WorkflowSignals = {
    source: projectPath || mediaPath || "current"
  };
  if (mediaPath) assignDefined(signals, mediaSignalsFromPath(mediaPath));
  if (text?.trim()) {
    try {
      assignDefined(signals, projectSignalsFromObject(JSON.parse(text) as Record<string, unknown>, projectPath || undefined));
    } catch {
      assignDefined(signals, promptSignalsFromText(text));
    }
  } else if (projectPath && fsSync.existsSync(projectPath)) {
    try {
      const projectText = await fs.readFile(projectPath, "utf-8");
      assignDefined(signals, projectSignalsFromObject(JSON.parse(projectText) as Record<string, unknown>, projectPath));
    } catch {
      assignDefined(signals, mediaSignalsFromPath(projectPath));
    }
  }
  return signals;
}

function projectSignalsFromObject(project: Record<string, unknown>, source?: string): WorkflowSignals {
  const projectConfig = asRecord(project.project);
  const metadata = asRecord(project.metadata);
  const beginner = asRecord(metadata.beginnerAutoTemplate);
  const beginnerTemplate = asRecord(beginner.template);
  const smartDefaults = asRecord(beginner.smartDefaults);
  const timeline = Array.isArray(project.timeline) ? project.timeline as Array<Record<string, unknown>> : [];
  const captions = Array.isArray(project.captions) ? project.captions as Array<Record<string, unknown>> : [];
  const width = Number(projectConfig.width || smartDefaults.width || 0);
  const height = Number(projectConfig.height || smartDefaults.height || 0);
  const duration = Number(projectConfig.duration || Math.max(0, ...timeline.map((scene) => Number(scene.start || 0) + Number(scene.duration || 0))));
  const transitionCounts: Record<string, number> = {};
  let captionCount = captions.length;
  let zoomLayers = 0;
  let mediaLayers = 0;
  for (const scene of timeline) {
    const transition = asRecord(scene.transitionOut);
    const transitionType = String(transition.type || "").trim();
    if (transitionType) bumpCount(transitionCounts, transitionType);
    const layers = Array.isArray(scene.layers) ? scene.layers as Array<Record<string, unknown>> : [];
    for (const layer of layers) {
      const type = String(layer.type || "");
      if (type === "caption" || type === "captions") {
        const items = Array.isArray(layer.items) ? layer.items : [];
        captionCount += Math.max(1, items.length);
      }
      if (type === "text") captionCount += 0.5;
      if (type === "video" || type === "image") {
        mediaLayers += 1;
        const animation = asRecord(layer.animation);
        const scale = Number(layer.scale || 1);
        if (scale > 1.08 || String(animation.in || animation.out || "").toLowerCase().includes("zoom")) zoomLayers += 1;
      }
    }
  }
  const textSample = [
    String(metadata.prompt || ""),
    String(metadata.contentPrompt || ""),
    ...timeline.slice(0, 3).flatMap((scene) => {
      const layers = Array.isArray(scene.layers) ? scene.layers as Array<Record<string, unknown>> : [];
      return layers.map((layer) => String(layer.text || "")).filter(Boolean);
    })
  ].join(" ");
  return {
    source,
    template: String(beginnerTemplate.key || metadata.template || metadata.templateKey || metadata.sourceTemplate || "").trim() || undefined,
    targetPlatform: String(beginner.targetPlatform || platformFromDimensions(width, height) || "").trim() || undefined,
    exportPreset: String(project.exportPreset || projectConfig.exportPreset || smartDefaults.exportPreset || "").trim() || undefined,
    duration: Number.isFinite(duration) && duration > 0 ? Number(duration.toFixed(2)) : undefined,
    pacing: String(smartDefaults.pacing || pacingFromTimeline(timeline, duration) || "").trim() || undefined,
    captionDensity: captionDensityFromCounts(captionCount, duration),
    motionIntensity: motionIntensityFromCounts(zoomLayers, mediaLayers, transitionCounts),
    hookStyle: hookStyleFromText(textSample),
    transition: topCountKey(transitionCounts),
    lightingProfile: lightingProfileFromProject(project, beginner.desiredVibe),
    stylePreset: String(project.stylePreset || metadata.stylePreset || "").trim() || undefined,
    aspectRatio: aspectRatioFromDimensions(width, height),
    mediaKind: promptSignalsFromText(`${source || ""} ${textSample}`).mediaKind,
    promptKind: promptSignalsFromText(textSample).promptKind,
    captionCount: Math.round(captionCount),
    sceneCount: timeline.length
  };
}

function promptSignalsFromText(text: string): WorkflowSignals {
  const lower = text.toLowerCase();
  const tokens = wordTokens(lower);
  const signals: WorkflowSignals = {};
  if (/desktop|screen recording|screen capture|obs|window|dashboard|software|app demo|login|scan/.test(lower)) signals.mediaKind = "desktop_recording";
  if (/game|gameplay|kill|montage|facecam|explosion|reaction/.test(lower)) signals.mediaKind = "gameplay";
  if (/talking head|webcam|podcast|speaker|interview/.test(lower)) signals.mediaKind = "talking_head";
  if (/tutorial|walkthrough|how to|step by step|lesson/.test(lower)) signals.promptKind = "tutorial";
  if (/short|tiktok|reel|vertical/.test(lower)) signals.targetPlatform = "shorts";
  if (/youtube landscape|long form|16:9/.test(lower)) signals.targetPlatform = "youtube";
  if (/premium|cinematic|trailer|showcase/.test(lower)) signals.pacing = "cinematic";
  if (/fast|aggressive|hype|punchy/.test(lower)) signals.motionIntensity = "high";
  if (/minimal|clean|calm|readable/.test(lower)) signals.motionIntensity = "low";
  if (/caption|subtitle|text heavy/.test(lower)) signals.captionDensity = "high";
  if (tokens.has("blue") && (tokens.has("black") || tokens.has("cyber"))) signals.lightingProfile = "blue_black_cyber";
  else if ((tokens.has("red") && tokens.has("black")) || tokens.has("cyber") || tokens.has("security") || tokens.has("hacker")) signals.lightingProfile = "red_black_cyber";
  if (/luxury|premium/.test(lower)) signals.lightingProfile = signals.lightingProfile || "premium_soft";
  signals.hookStyle = hookStyleFromText(text);
  return signals;
}

function mediaSignalsFromPath(mediaPath: string): WorkflowSignals {
  const ext = path.extname(mediaPath).replace(".", "").toLowerCase();
  const name = path.basename(mediaPath).toLowerCase();
  const signals = promptSignalsFromText(name);
  if (videoImportExtensions.includes(ext)) signals.mediaKind = signals.mediaKind || "video";
  if (imageImportExtensions.includes(ext)) signals.mediaKind = "image_collection";
  if (audioImportExtensions.includes(ext)) signals.mediaKind = "music";
  if (/desktop|screen|recording|obs|capture|demo|dashboard|software/.test(name)) signals.mediaKind = "desktop_recording";
  if (/game|clip|kill|montage|highlight/.test(name)) signals.mediaKind = "gameplay";
  if (/tutorial|lesson|walkthrough/.test(name)) signals.promptKind = "tutorial";
  return signals;
}

function deriveWorkflowPreferences(events: Array<Record<string, unknown>>, signals: WorkflowSignals[]) {
  const counts: Record<string, Record<string, number>> = {
    template: {},
    targetPlatform: {},
    exportPreset: {},
    pacing: {},
    captionDensity: {},
    motionIntensity: {},
    hookStyle: {},
    transition: {},
    lightingProfile: {},
    stylePreset: {}
  };
  const durations: number[] = [];
  for (const signal of signals) {
    for (const key of Object.keys(counts) as Array<keyof WorkflowSignals>) {
      const value = signal[key];
      if (typeof value === "string" && value.trim()) bumpCount(counts[key], value, 1);
    }
    if (typeof signal.duration === "number" && Number.isFinite(signal.duration)) durations.push(signal.duration);
  }
  for (const event of events) {
    const weight = event.event === "render_success" || event.event === "beginner_auto_video" ? 2 : event.event === "render_review" ? 1.5 : 1;
    for (const key of Object.keys(counts)) {
      const value = event[key];
      if (typeof value === "string" && value.trim()) bumpCount(counts[key], value, weight);
    }
    const duration = Number(event.duration);
    if (Number.isFinite(duration) && duration > 0) durations.push(duration);
  }
  return {
    template: topCountKey(counts.template) || "premium_product_showcase",
    targetPlatform: topCountKey(counts.targetPlatform) || "youtube",
    exportPreset: topCountKey(counts.exportPreset) || "youtube_1080p",
    duration: medianNumber(durations) || 30,
    pacing: topCountKey(counts.pacing) || "Smooth feature reveals",
    captionDensity: topCountKey(counts.captionDensity) || "medium",
    motionIntensity: topCountKey(counts.motionIntensity) || "medium",
    hookStyle: topCountKey(counts.hookStyle) || "clean_professional",
    transition: topCountKey(counts.transition) || "crossfade",
    lightingProfile: topCountKey(counts.lightingProfile) || "clean_cinematic",
    stylePreset: topCountKey(counts.stylePreset) || "clean_cinematic",
    evidence: {
      events: events.length,
      projects: signals.length,
      localOnly: true
    }
  };
}

function deriveSmartDefaults(preferences: Record<string, unknown>, currentSignals?: WorkflowSignals) {
  const targetPlatform = String(currentSignals?.targetPlatform || preferences.targetPlatform || "youtube");
  const vertical = ["shorts", "youtube_shorts", "tiktok", "reels", "instagram", "instagram_reels"].includes(targetPlatform);
  const square = targetPlatform === "square";
  const exportPreset = String(currentSignals?.exportPreset || preferences.exportPreset || (vertical ? "shorts" : square ? "square" : "youtube_1080p"));
  const motion = String(preferences.motionIntensity || "medium");
  return {
    template: currentSignals?.template || preferences.template || "premium_product_showcase",
    targetPlatform,
    exportPreset,
    aspectRatio: currentSignals?.aspectRatio || (vertical ? "9:16" : square ? "1:1" : "16:9"),
    resolution: vertical ? "1080x1920" : square ? "1080x1080" : "1920x1080",
    captionDensity: preferences.captionDensity || "medium",
    captionSize: vertical ? 64 : square ? 54 : 46,
    pacing: preferences.pacing || "Smooth feature reveals",
    transition: preferences.transition || "crossfade",
    transitionIntensity: motion === "high" ? 0.72 : motion === "low" ? 0.32 : 0.52,
    lightingProfile: preferences.lightingProfile || "clean_cinematic",
    duration: preferences.duration || 30,
    audioNormalization: vertical ? "-14 LUFS" : "-16 LUFS",
    localOnly: true
  };
}

function deriveRecoverySignals(events: Array<Record<string, unknown>>, frictionEvents: Array<Record<string, unknown>>) {
  const correctionCounts: Record<string, number> = {};
  let rejectedScenes = 0;
  let exportRetries = 0;
  let pacingComplaints = 0;
  let captionTimingCorrections = 0;
  let zoomCorrections = 0;
  let transitionSpeedCorrections = 0;
  for (const event of events) {
    const eventName = String(event.event || "");
    const correction = String(event.correction || event.note || "");
    const lower = `${eventName} ${correction}`.toLowerCase();
    if (correction) bumpCount(correctionCounts, correction);
    if (/reject|needs_review|skip/.test(lower)) rejectedScenes += 1;
    if (/export_retry|render_failed|failed_export/.test(lower)) exportRetries += 1;
    if (/too slow|too fast|pacing|faster|slower/.test(lower)) pacingComplaints += 1;
    if (/caption.*timing|slow down the captions|captions too fast/.test(lower)) captionTimingCorrections += 1;
    if (/zoom/.test(lower)) zoomCorrections += 1;
    if (/transition.*speed|transition/.test(lower)) transitionSpeedCorrections += 1;
  }
  exportRetries += frictionEvents.filter((event) => String(event.event || "").includes("failed_export")).length;
  return {
    repeatedCorrections: Object.entries(correctionCounts).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([label, count]) => ({ label, count })),
    rejectedScenes,
    exportRetries,
    pacingComplaints,
    captionTimingCorrections,
    zoomCorrections,
    transitionSpeedCorrections,
    adaptiveRules: [
      captionTimingCorrections >= 2 ? "Future captions should be slower and less dense." : "",
      zoomCorrections >= 2 ? "Future zooms should start milder and require fewer corrections." : "",
      transitionSpeedCorrections >= 2 ? "Future transitions should use the preferred speed and avoid over-repetition." : "",
      pacingComplaints >= 2 ? "Future timelines should apply the creator's recent pacing corrections automatically." : ""
    ].filter(Boolean),
    localOnly: true
  };
}

function deriveSessionContinuity(events: Array<Record<string, unknown>>, projectPath?: string | null) {
  const recentPrompts = events
    .map((event) => String(event.prompt || event.note || ""))
    .filter((value) => value.length > 8)
    .slice(-8)
    .reverse();
  const approvedStyles = events
    .filter((event) => /approve|render_success|render_review/.test(String(event.event || "")))
    .map((event) => String(event.style || event.stylePreset || event.template || ""))
    .filter(Boolean)
    .slice(-8)
    .reverse();
  const regeneration = events
    .filter((event) => /regenerate|assistant_instruction|scene_action/.test(String(event.event || "")))
    .map((event) => ({ event: event.event, correction: event.correction || event.note, createdAt: event.createdAt }))
    .slice(-8)
    .reverse();
  return {
    lastProjectPath: projectPath || events.map((event) => String(event.projectPath || "")).filter(Boolean).slice(-1)[0] || null,
    lastPreviewPosition: Number(events.map((event) => event.previewTime).filter((value) => Number.isFinite(Number(value))).slice(-1)[0] || 0),
    recentPrompts,
    recentlyApprovedStyles: approvedStyles,
    recentRegenerationBehavior: regeneration,
    localOnly: true
  };
}

function deriveCreatorFingerprint(preferences: Record<string, unknown>, recoverySignals: Record<string, unknown>, signals: WorkflowSignals[]) {
  const avgSceneCount = averageNumber(signals.map((signal) => signal.sceneCount));
  const pacing = String(preferences.pacing || "");
  const motion = String(preferences.motionIntensity || "medium");
  const lighting = String(preferences.lightingProfile || "clean_cinematic");
  const transition = String(preferences.transition || "crossfade");
  const captionDensity = String(preferences.captionDensity || "medium");
  return {
    pacingIdentity: pacing.toLowerCase().includes("fast") || motion === "high" ? "fast short-form pacing" : avgSceneCount > 7 ? "structured multi-scene pacing" : "measured cinematic pacing",
    cinematicStyle: lighting,
    transitionBehavior: transition === "cut" ? "direct cuts" : `${transition} led flow`,
    motionPhilosophy: motion === "high" ? "energetic motion" : motion === "low" ? "restrained motion" : "balanced motion",
    captionBehavior: captionDensity === "high" ? "caption-led" : captionDensity === "low" ? "minimal captions" : "balanced captions",
    brandingConsistency: lighting.includes("red") ? "red/black visual identity" : "clean brand-safe palette",
    recoveryAwareness: (recoverySignals.adaptiveRules as string[] | undefined)?.slice(0, 3) || [],
    localOnly: true
  };
}

function deriveContextSuggestions(currentSignals: WorkflowSignals, preferences: Record<string, unknown>, recoverySignals: Record<string, unknown>) {
  const suggestions: Array<Record<string, unknown>> = [];
  const mediaKind = currentSignals.mediaKind || currentSignals.promptKind;
  if (mediaKind === "desktop_recording") suggestions.push({ title: "Use showcase mode", reason: "Imported media looks like a desktop or software recording.", apply: { template: "software_demo", lightingProfile: preferences.lightingProfile || "clean_cinematic" } });
  if (mediaKind === "gameplay") suggestions.push({ title: "Use montage pacing", reason: "Gameplay signals were detected in the file name or prompt.", apply: { template: "gaming_montage", motionIntensity: "high" } });
  if (mediaKind === "talking_head") suggestions.push({ title: "Use caption-heavy mode", reason: "Talking-head content usually benefits from readable captions and calmer motion.", apply: { captionDensity: "high", motionIntensity: "low" } });
  if (currentSignals.promptKind === "tutorial") suggestions.push({ title: "Use clarity mode", reason: "Tutorial language detected. Slower pacing and safe-zone captions are likely better.", apply: { template: "tutorial_walkthrough", motionIntensity: "low" } });
  const rules = Array.isArray(recoverySignals.adaptiveRules) ? recoverySignals.adaptiveRules as string[] : [];
  for (const rule of rules.slice(0, 3)) suggestions.push({ title: "Apply learned recovery", reason: rule, apply: { learnedRule: rule } });
  if (!suggestions.length) suggestions.push({ title: "Keep familiar defaults", reason: "No strong media context detected, so the app will use your recent successful defaults.", apply: { template: preferences.template, exportPreset: preferences.exportPreset } });
  return suggestions.slice(0, 6).map((item, index) => ({ id: `adaptive_${index + 1}`, ...item, localOnly: true }));
}

function summarizeFrictionForMemory(events: Array<Record<string, unknown>>) {
  const labels: Record<string, number> = {};
  for (const event of events) bumpCount(labels, String(event.label || event.event || "event"));
  return {
    eventCount: events.length,
    slowOperations: events.filter((event) => String(event.event) === "slow_operation").length,
    failedOperations: events.filter((event) => String(event.event).includes("failed")).length,
    repeatedSettings: events.filter((event) => String(event.event) === "settings_changed").length,
    topLabels: Object.entries(labels).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([label, count]) => ({ label, count })),
    localOnly: true
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function assignDefined<T extends Record<string, unknown>>(target: T, source: Record<string, unknown>) {
  for (const [key, value] of Object.entries(source)) {
    if (value !== undefined && value !== "") target[key as keyof T] = value as T[keyof T];
  }
  return target;
}

function bumpCount(target: Record<string, number>, key: string, weight = 1) {
  const clean = key.trim();
  if (!clean) return;
  target[clean] = (target[clean] || 0) + weight;
}

function topCountKey(counts: Record<string, number>) {
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0];
}

function medianNumber(values: number[]) {
  const clean = values.filter((value) => Number.isFinite(value) && value > 0).sort((a, b) => a - b);
  if (!clean.length) return 0;
  const middle = Math.floor(clean.length / 2);
  return Number((clean.length % 2 ? clean[middle] : (clean[middle - 1] + clean[middle]) / 2).toFixed(2));
}

function averageNumber(values: Array<number | undefined>) {
  const clean = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : 0;
}

function sanitizeMemoryToken(value: string) {
  return value.replace(/[^a-z0-9_:-]+/gi, "_").slice(0, 80) || "event";
}

function platformFromDimensions(width: number, height: number) {
  if (!width || !height) return "";
  if (height > width) return "shorts";
  if (Math.abs(width - height) < 10) return "square";
  return "youtube";
}

function aspectRatioFromDimensions(width: number, height: number) {
  if (!width || !height) return undefined;
  if (height > width) return "9:16";
  if (Math.abs(width - height) < 10) return "1:1";
  return "16:9";
}

function pacingFromTimeline(timeline: Array<Record<string, unknown>>, duration: number) {
  if (!timeline.length || !duration) return "";
  const averageScene = duration / timeline.length;
  if (averageScene <= 2.4) return "fast short-form";
  if (averageScene >= 6) return "calm readable";
  return "balanced cinematic";
}

function captionDensityFromCounts(captionCount: number, duration: number) {
  if (!duration) return undefined;
  const perMinute = captionCount / Math.max(duration / 60, 0.1);
  if (perMinute > 38) return "high";
  if (perMinute < 12) return "low";
  return "medium";
}

function motionIntensityFromCounts(zoomLayers: number, mediaLayers: number, transitionCounts: Record<string, number>) {
  const transitionScore = Object.entries(transitionCounts).reduce((score, [key, count]) => score + (/zoom|slide|shake|glitch/.test(key) ? count * 1.4 : count * 0.5), 0);
  const ratio = mediaLayers ? zoomLayers / mediaLayers : 0;
  if (ratio > 0.6 || transitionScore > 8) return "high";
  if (ratio < 0.15 && transitionScore < 3) return "low";
  return "medium";
}

function hookStyleFromText(text: string) {
  const lower = text.toLowerCase();
  if (/why|what if|secret|hidden|nobody|did you know/.test(lower)) return "curiosity";
  if (/problem|broken|fix|mistake|stop|can't|missing/.test(lower)) return "problem_solution";
  if (/fast|watch|boom|insane|wild/.test(lower)) return "fast_aggressive";
  if (/premium|professional|clean|showcase/.test(lower)) return "clean_professional";
  return "direct";
}

function lightingProfileFromProject(project: Record<string, unknown>, desiredVibe: unknown) {
  const text = `${String(project.stylePreset || "")} ${String(desiredVibe || "")} ${JSON.stringify(project.metadata || {})}`.toLowerCase();
  const tokens = wordTokens(text);
  if (tokens.has("blue") && (tokens.has("black") || tokens.has("cyber"))) return "blue_black_cyber";
  if ((tokens.has("red") && tokens.has("black")) || tokens.has("cyber") || tokens.has("hacker")) return "red_black_cyber";
  if (/luxury|premium/.test(text)) return "premium_soft";
  if (/vapor/.test(text)) return "vaporwave";
  if (/horror|glitch/.test(text)) return "horror_glitch";
  if (/minimal|clean/.test(text)) return "minimal_clean";
  return undefined;
}

function wordTokens(text: string) {
  return new Set((text.replace(/[_/]+/g, " ").match(/[a-z0-9]+/g) || []));
}

async function readRecoveryPoints(dir: string) {
  if (!fsSync.existsSync(dir)) return [];
  const points = [];
  for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
    if (!entry.isFile() || path.extname(entry.name).toLowerCase() !== ".json") continue;
    const filePath = path.join(dir, entry.name);
    const stat = await fs.stat(filePath);
    points.push({
      type: entry.name.startsWith("autosave") ? "autosave" : "backup",
      path: filePath,
      timestamp: stat.mtime.toISOString(),
      size: stat.size
    });
  }
  return points.sort((a, b) => String(b.timestamp).localeCompare(String(a.timestamp)));
}

async function templatePackRows(): Promise<TemplatePack[]> {
  const templateRows: Array<Pick<TemplatePack, "key" | "name" | "exportPreset" | "transitionStyle" | "requiredAssets">> = [
    { key: "youtube_intro", name: "YouTube Intro", exportPreset: "youtube_1080p", transitionStyle: "crossfade", requiredAssets: { logo: "image", intro_bg: "video", music: "audio", whoosh: "audio" } },
    { key: "tiktok_reels_short", name: "TikTok/Reels Short", exportPreset: "tiktok_reels", transitionStyle: "slide", requiredAssets: { clip1: "video", clip2: "video", music: "audio", pop: "audio" } },
    { key: "gaming_montage", name: "Gaming Montage", exportPreset: "youtube_1080p", transitionStyle: "zoom", requiredAssets: { clip1: "video", clip2: "video", clip3: "video", music: "audio", impact: "audio" } },
    { key: "product_promo", name: "Product Promo", exportPreset: "square", transitionStyle: "fadeToBlack", requiredAssets: { product: "image", broll: "video", music: "audio" } },
    { key: "lyric_video", name: "Lyric Video", exportPreset: "youtube_1080p", transitionStyle: "crossfade", requiredAssets: { background: "video", music: "audio" } },
    { key: "slideshow", name: "Slideshow", exportPreset: "youtube_1080p", transitionStyle: "crossfade", requiredAssets: { photo1: "image", photo2: "image", photo3: "image", music: "audio" } },
    { key: "meme_edit", name: "Meme Edit", exportPreset: "square", transitionStyle: "cut", requiredAssets: { clip: "video", reaction: "image", music: "audio", hit: "audio" } },
    { key: "tutorial_video", name: "Tutorial Video", exportPreset: "youtube_1080p", transitionStyle: "slide", requiredAssets: { screen: "video", music: "audio", click: "audio" } }
  ];
  return templateRows.map((item) => ({
    ...item,
    author: "Aegis",
    version: "1.0.0",
    tags: tagsForTemplate(item.key),
    previewThumbnail: path.join(engineRoot, "examples", "templates", "packs", "thumbnails", `${item.key}.png`),
    installState: "bundled"
  }));
}

function tagsForTemplate(key: string) {
  const tags: Record<string, string[]> = {
    youtube_intro: ["youtube", "intro", "creator"],
    tiktok_reels_short: ["vertical", "shorts", "captions"],
    gaming_montage: ["gaming", "fast", "montage"],
    product_promo: ["product", "promo", "square"],
    lyric_video: ["music", "lyrics", "karaoke"],
    slideshow: ["photos", "memory", "simple"],
    meme_edit: ["meme", "reaction", "square"],
    tutorial_video: ["tutorial", "screen", "education"]
  };
  return tags[key] || ["template"];
}

function sendLog(webContents: Electron.WebContents, runId: string, text: string, stream: "stdout" | "stderr") {
  for (const line of text.split(/\r?\n/)) {
    if (line.trim()) webContents.send("render:log", { runId, line, stream });
  }
}

function safeAssetKey(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "asset";
}

function mediaType(filePath: string): "image" | "video" | "audio" | "unknown" {
  const ext = path.extname(filePath).toLowerCase();
  if (imageImportExtensions.map((value) => `.${value}`).includes(ext)) return "image";
  if (videoImportExtensions.map((value) => `.${value}`).includes(ext)) return "video";
  if (audioImportExtensions.map((value) => `.${value}`).includes(ext)) return "audio";
  return "unknown";
}

function checkAssets(text: string, projectPath: string | null) {
  const data = JSON.parse(text);
  const projectDir = projectPath ? path.dirname(projectPath) : engineRoot;
  const assets = data.assets && typeof data.assets === "object" ? data.assets : {};
  return Object.entries(assets).map(([key, rawValue]) => {
    const value = String(rawValue);
    const resolved = path.isAbsolute(value) ? value : path.resolve(projectDir, value);
    return {
      key,
      path: resolved,
      exists: fsSync.existsSync(resolved),
      type: mediaType(resolved)
    };
  });
}

async function readHistory(projectPath: string) {
  const historyDir = path.join(path.dirname(projectPath), ".ave_history");
  if (!fsSync.existsSync(historyDir)) return [];
  const summaries = [];
  for (const entry of await fs.readdir(historyDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const summaryPath = path.join(historyDir, entry.name, "change_summary.json");
    if (!fsSync.existsSync(summaryPath)) continue;
    summaries.push(JSON.parse(await fs.readFile(summaryPath, "utf-8")));
  }
  return summaries.sort((a, b) => String(b.timestamp || "").localeCompare(String(a.timestamp || "")));
}

async function readPlugins() {
  const pluginsRoot = path.join(engineRoot, "plugins");
  if (!fsSync.existsSync(pluginsRoot)) return [];
  const plugins = [];
  for (const entry of await fs.readdir(pluginsRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const manifestPath = path.join(pluginsRoot, entry.name, "plugin.json");
    if (!fsSync.existsSync(manifestPath)) continue;
    const manifest = JSON.parse(await fs.readFile(manifestPath, "utf-8"));
    plugins.push({ ...manifest, path: path.dirname(manifestPath) });
  }
  return plugins.sort((a, b) => `${a.type}:${a.name}`.localeCompare(`${b.type}:${b.name}`));
}
