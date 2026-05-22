import { ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";
import { EngineResult } from "./engine";

export type RenderPayload = {
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

type RenderQueueConfig = {
  pythonBinary: string;
  renderPy: string;
  engineRoot: string;
  outputRoot: string;
  exportsRoot: string;
  writeTempProject: (text: string, prefix: string) => Promise<string>;
  addRecent: (filePath: string) => Promise<void>;
  runEngine: (args: string[]) => Promise<EngineResult>;
  send: (channel: string, payload: unknown) => void;
};

export class RenderQueueController {
  private queue: QueuedRenderJob[] = [];
  private activeRender: QueuedRenderJob | null = null;
  private paused = false;

  constructor(private readonly config: RenderQueueConfig) {}

  async enqueue(payload: RenderPayload) {
    const runId = crypto.randomUUID();
    const input = await this.config.writeTempProject(payload.text, `render-${runId}`);
    if (payload.projectPath) await this.config.addRecent(payload.projectPath);
    const requestedFormat = payload.format || "mp4";
    const extension = requestedFormat === "image_sequence" ? "png" : requestedFormat;
    const outputPath = payload.outputPath || defaultRenderOutputPath(payload, runId, extension, this.config.outputRoot);
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
    this.queue.push(job);
    this.sort();
    this.broadcast();
    this.process();
    return { runId, outputPath };
  }

  serialize() {
    return this.queue.map((job) => ({
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

  pause() {
    this.paused = true;
    this.broadcast();
    return this.serialize();
  }

  resume() {
    this.paused = false;
    this.process();
    this.broadcast();
    return this.serialize();
  }

  cancel(runId: string) {
    const job = this.queue.find((item) => item.runId === runId);
    if (!job) return this.serialize();
    if (job.status === "running" && job.child) {
      job.status = "canceled";
      job.child.kill();
    } else if (job.status === "queued") {
      job.status = "canceled";
    }
    this.broadcast();
    return this.serialize();
  }

  retry(runId: string) {
    const job = this.queue.find((item) => item.runId === runId);
    if (!job || !["failed", "canceled", "completed"].includes(job.status)) return this.serialize();
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
    this.sort();
    this.broadcast();
    this.process();
    return this.serialize();
  }

  setPriority(runId: string, priority: number) {
    const job = this.queue.find((item) => item.runId === runId);
    if (job && job.status === "queued") {
      job.priority = priority;
      this.sort();
    }
    this.broadcast();
    return this.serialize();
  }

  failedCount() {
    return this.queue.filter((job) => job.status === "failed").length;
  }

  private process() {
    if (this.paused || this.activeRender) return;
    const job = this.queue.find((item) => item.status === "queued");
    if (!job) return;
    this.activeRender = job;
    job.status = "running";
    job.startedAt = Date.now();
    job.progressPercent = Math.max(job.progressPercent || 0, 2);
    this.broadcast();
    const child = spawn(this.config.pythonBinary, [this.config.renderPy, ...job.args], {
      cwd: this.config.engineRoot,
      windowsHide: true
    });
    job.child = child;
    child.stdout.on("data", (chunk: Buffer) => this.collectLog(job, chunk.toString(), "stdout"));
    child.stderr.on("data", (chunk: Buffer) => this.collectLog(job, chunk.toString(), "stderr"));
    child.on("close", async (exitCode) => {
      job.exitCode = exitCode;
      job.status = job.status === "canceled" ? "canceled" : exitCode === 0 ? "completed" : "failed";
      if (job.status === "completed") job.progressPercent = 100;
      job.child = undefined;
      if (job.status === "completed" && job.payload.quality === "final" && job.payload.createDeliveryPackage) {
        await this.createDeliveryPackage(job);
      }
      this.activeRender = null;
      this.config.send("render:complete", {
        runId: job.runId,
        exitCode,
        outputPath: job.outputPath,
        packagePath: job.packagePath
      });
      this.broadcast();
      this.process();
    });
  }

  private collectLog(job: QueuedRenderJob, text: string, stream: "stdout" | "stderr") {
    for (const line of text.split(/\r?\n/)) {
      if (!line.trim()) continue;
      job.logs = [...job.logs.slice(-120), line];
      updateRenderProgress(job, line);
      this.config.send("render:log", { runId: job.runId, line, stream });
    }
    this.broadcast();
  }

  private async createDeliveryPackage(job: QueuedRenderJob) {
    job.packageStatus = "running";
    job.packageError = undefined;
    this.broadcast();
    const packageDir = path.join(this.config.exportsRoot, `${safePackageName(job)}-${Date.now()}`);
    const renderLogPath = path.join(path.dirname(job.outputPath), `${job.runId}-render_logs.txt`);
    await fs.mkdir(path.dirname(renderLogPath), { recursive: true });
    await fs.writeFile(renderLogPath, job.logs.join("\n") + "\n", "utf-8");
    const platforms = job.payload.packagePlatforms?.length ? job.payload.packagePlatforms : platformsForPreset(job.payload.preset);
    const args = ["post-package", job.input, job.outputPath, "--platforms", ...platforms, "-o", packageDir, "--render-logs", renderLogPath];
    if (job.payload.packageTitle) args.push("--title", job.payload.packageTitle);
    const renderReportPath = path.join(path.dirname(job.outputPath), "render_report.json");
    if (fsSync.existsSync(renderReportPath)) args.push("--render-report", renderReportPath);
    const result = await this.config.runEngine(args);
    for (const line of `${result.stdout}\n${result.stderr}`.split(/\r?\n/)) {
      if (line.trim()) {
        job.logs = [...job.logs.slice(-120), line];
        this.config.send("render:log", { runId: job.runId, line, stream: "stdout" });
      }
    }
    if (result.ok) {
      job.packageStatus = "completed";
      job.packagePath = packageDir;
    } else {
      job.packageStatus = "failed";
      job.packageError = result.stderr || result.stdout || "Delivery package failed.";
    }
    this.broadcast();
  }

  private sort() {
    this.queue.sort((a, b) => {
      if (a.status === "running") return -1;
      if (b.status === "running") return 1;
      if (a.status !== b.status) {
        const rank = { queued: 0, failed: 1, canceled: 2, completed: 3, running: -1 };
        return rank[a.status] - rank[b.status];
      }
      return b.priority - a.priority;
    });
  }

  private broadcast() {
    this.config.send("render:queue", this.serialize());
  }
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

export function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40) || "auto-video";
}

function timestampForFilename(date = new Date()) {
  return date
    .toISOString()
    .replace(/\.\d{3}Z$/, "Z")
    .replace(/:/g, "")
    .replace("T", "-");
}

export function defaultRenderOutputPath(payload: RenderPayload, runId: string, extension: string, outputRoot: string) {
  const projectName = slugify(renderProjectName(payload));
  const quality = slugify(payload.quality || "render");
  const preset = slugify(payload.preset || "project");
  const shortRun = runId.replace(/-/g, "").slice(0, 8);
  const baseName = `${projectName}-${quality}-${preset}-${timestampForFilename()}-${shortRun}`;
  if (payload.format === "image_sequence") {
    return path.join(outputRoot, baseName, `${baseName}_%05d.${extension}`);
  }
  return path.join(outputRoot, `${baseName}.${extension}`);
}

function renderProjectName(payload: RenderPayload) {
  const fromProject = projectTitleFromText(payload.text);
  if (fromProject) return fromProject;
  if (payload.projectPath) return path.basename(payload.projectPath, path.extname(payload.projectPath));
  if (payload.label) return payload.label;
  return "automatic-video";
}

function projectTitleFromText(text: string) {
  try {
    const data = JSON.parse(text) as Record<string, any>;
    const metadata = data.metadata || {};
    const contentGenerator = metadata.contentGenerator || {};
    const brief = contentGenerator.contentBrief || {};
    const beginner = metadata.beginnerAutoTemplate || {};
    const project = data.project || {};
    const candidates = [
      data.title,
      data.name,
      metadata.title,
      metadata.name,
      brief.productName,
      beginner.template?.name,
      project.name,
    ];
    for (const value of candidates) {
      if (typeof value === "string" && value.trim()) return value.trim();
    }
    const firstTextLayer = firstTimelineText(data.timeline);
    if (firstTextLayer) return firstTextLayer;
  } catch {
    return null;
  }
  return null;
}

function firstTimelineText(timeline: unknown) {
  if (!Array.isArray(timeline)) return null;
  for (const scene of timeline) {
    if (!scene || typeof scene !== "object") continue;
    const layers = (scene as Record<string, unknown>).layers;
    if (!Array.isArray(layers)) continue;
    for (const layer of layers) {
      if (!layer || typeof layer !== "object") continue;
      const layerData = layer as Record<string, unknown>;
      if (typeof layerData.text === "string" && layerData.text.trim()) {
        return layerData.text.trim();
      }
      if (typeof layerData.title === "string" && layerData.title.trim()) {
        return layerData.title.trim();
      }
    }
  }
  return null;
}
