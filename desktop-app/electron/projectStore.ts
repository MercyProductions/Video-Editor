import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";
import { safeAssetKey } from "./media";

export type RecentProject = {
  path: string;
  name: string;
  openedAt: string;
};

export type AppSettings = {
  theme: "aegis" | "graphite" | "midnight" | "slate" | "high_contrast" | "light";
  autosave: boolean;
  autosaveIntervalSeconds: number;
  previewTimeSeconds: number;
  keyboardShortcuts: boolean;
  onboardingComplete: boolean;
  defaultWorkflow: "quick" | "guided" | "advanced";
  defaultPlatform: string;
  defaultStyle: string;
  defaultExportFolder?: string | null;
  beginnerTips: boolean;
  workspacePreset: "beginner" | "ai" | "editing" | "captions" | "export" | "minimal";
  panelDock: "standard" | "inspector_left" | "media_right" | "preview_focus";
  uiScale: "small" | "medium" | "large" | "auto";
  accentColor: string;
  leftRailWidth: number;
  rightRailWidth: number;
  leftRailOpen: boolean;
  rightRailOpen: boolean;
  monitorPositions?: Record<string, { x?: number; y?: number; width: number; height: number }>;
};

export type RecoveryPoint = {
  type: string;
  path: string;
  timestamp?: string;
  size?: number;
  projectId?: string;
};

type ProjectStoreConfig = {
  userDataDir: string;
  generatedDir: string;
  tempDir: string;
  outputRoot: string;
  legacyOutputRoots: string[];
};

export class ProjectStore {
  private readonly recentPath: string;
  private readonly settingsPath: string;
  private readonly sessionStatePath: string;

  constructor(private readonly config: ProjectStoreConfig) {
    this.recentPath = path.join(config.userDataDir, "recent-projects.json");
    this.settingsPath = path.join(config.userDataDir, "settings.json");
    this.sessionStatePath = path.join(config.userDataDir, "session-state.json");
  }

  async readProjectFile(filePath: string) {
    const text = await fs.readFile(filePath, "utf-8");
    await this.addRecent(filePath);
    return { path: filePath, text, name: path.basename(filePath) };
  }

  async writeProjectFile(filePath: string, text: string) {
    await fs.mkdir(path.dirname(filePath), { recursive: true });
    await fs.writeFile(filePath, text, "utf-8");
    await this.addRecent(filePath);
    return this.readProjectFile(filePath);
  }

  async writeTempProject(text: string, prefix: string) {
    await fs.mkdir(this.config.tempDir, { recursive: true });
    const filePath = path.join(this.config.tempDir, `${prefix}-${Date.now()}.json`);
    await fs.writeFile(filePath, text, "utf-8");
    return filePath;
  }

  tempProjectPath(prefix: string) {
    return path.join(this.config.tempDir, `${prefix}-${Date.now()}.json`);
  }

  async readRecent(): Promise<RecentProject[]> {
    try {
      const text = await fs.readFile(this.recentPath, "utf-8");
      return JSON.parse(text);
    } catch {
      return [];
    }
  }

  async addRecent(filePath: string) {
    await fs.mkdir(this.config.userDataDir, { recursive: true });
    const existing = await this.readRecent();
    const next = [
      { path: filePath, name: path.basename(filePath), openedAt: new Date().toISOString() },
      ...existing.filter((item) => item.path !== filePath)
    ].slice(0, 12);
    await fs.writeFile(this.recentPath, JSON.stringify(next, null, 2), "utf-8");
  }

  defaultSettings(): AppSettings {
    return {
      theme: "aegis",
      autosave: true,
      autosaveIntervalSeconds: 120,
      previewTimeSeconds: 1,
      keyboardShortcuts: true,
      onboardingComplete: false,
      defaultWorkflow: "quick",
      defaultPlatform: "youtube_shorts",
      defaultStyle: "cinematic",
      defaultExportFolder: this.config.outputRoot,
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
  }

  normalizeSettings(settings: Partial<AppSettings> = {}): AppSettings {
    const next = { ...this.defaultSettings(), ...settings };
    if (!next.defaultExportFolder || this.isLegacyExportFolder(next.defaultExportFolder)) {
      next.defaultExportFolder = this.config.outputRoot;
    }
    return next;
  }

  async readSettings(): Promise<AppSettings> {
    try {
      const text = await fs.readFile(this.settingsPath, "utf-8");
      return this.normalizeSettings(JSON.parse(text));
    } catch {
      return this.normalizeSettings();
    }
  }

  async saveSettings(settings: Partial<AppSettings>) {
    const next = this.normalizeSettings(settings);
    await fs.mkdir(this.config.userDataDir, { recursive: true });
    await fs.writeFile(this.settingsPath, JSON.stringify(next, null, 2), "utf-8");
    return next;
  }

  async autosaveRecovery(text: string, projectPath?: string | null, reasonValue?: string | null) {
    if (!text.trim()) return null;
    const projectId = projectPath ? safeAssetKey(projectPath) : "unsaved";
    const dir = path.join(this.config.userDataDir, "recovery", projectId);
    await fs.mkdir(dir, { recursive: true });
    const reason = safeAssetKey(reasonValue || "autosave");
    const filePath = path.join(dir, `${reason}-${Date.now()}.json`);
    await fs.writeFile(filePath, text, "utf-8");
    return { type: reason, path: filePath, timestamp: new Date().toISOString(), size: Buffer.byteLength(text), projectId };
  }

  async listRecovery(projectPath?: string | null) {
    const projectId = projectPath ? safeAssetKey(projectPath) : "unsaved";
    const dir = path.join(this.config.userDataDir, "recovery", projectId);
    return this.readRecoveryPoints(dir);
  }

  async restoreRecovery(sourcePath: string, targetPath?: string | null) {
    const text = await fs.readFile(sourcePath, "utf-8");
    const target = targetPath || path.join(this.config.generatedDir, "recovered_project.json");
    return this.writeProjectFile(target, text);
  }

  async readLatestRecoveryPoint() {
    return (await this.readAllRecoveryPoints())[0] || null;
  }

  async readStartupRecoveryState() {
    let previous: Record<string, unknown> | null = null;
    try {
      previous = fsSync.existsSync(this.sessionStatePath) ? JSON.parse(await fs.readFile(this.sessionStatePath, "utf-8")) : null;
    } catch {
      previous = null;
    }
    const latestRecovery = await this.readLatestRecoveryPoint();
    return {
      crashed: Boolean(previous?.active && latestRecovery),
      lastSavedAt: String(previous?.timestamp || latestRecovery?.timestamp || ""),
      latestRecovery
    };
  }

  writeSessionState(active: boolean) {
    try {
      fsSync.mkdirSync(this.config.userDataDir, { recursive: true });
      fsSync.writeFileSync(this.sessionStatePath, JSON.stringify({ active, timestamp: new Date().toISOString() }, null, 2) + "\n", "utf-8");
    } catch {
      // Session markers are recovery helpers only; failure should not block app startup/shutdown.
    }
  }

  private isLegacyExportFolder(folder: string | null | undefined) {
    if (!folder) return true;
    const resolved = path.resolve(folder);
    return this.config.legacyOutputRoots.some((legacy) => resolved === path.resolve(legacy));
  }

  private async readRecoveryPoints(dir: string) {
    if (!fsSync.existsSync(dir)) return [] as RecoveryPoint[];
    const points: RecoveryPoint[] = [];
    const projectId = path.basename(dir);
    for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
      if (!entry.isFile() || path.extname(entry.name).toLowerCase() !== ".json") continue;
      const filePath = path.join(dir, entry.name);
      const stat = await fs.stat(filePath);
      points.push({
        type: entry.name.startsWith("autosave") ? "autosave" : entry.name.split("-")[0] || "backup",
        path: filePath,
        timestamp: stat.mtime.toISOString(),
        size: stat.size,
        projectId
      });
    }
    return points.sort((a, b) => String(b.timestamp).localeCompare(String(a.timestamp)));
  }

  private async readAllRecoveryPoints() {
    const root = path.join(this.config.userDataDir, "recovery");
    if (!fsSync.existsSync(root)) return [] as RecoveryPoint[];
    const all: RecoveryPoint[] = [];
    for (const entry of await fs.readdir(root, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      all.push(...await this.readRecoveryPoints(path.join(root, entry.name)));
    }
    return all.sort((a, b) => String(b.timestamp || "").localeCompare(String(a.timestamp || "")));
  }
}
