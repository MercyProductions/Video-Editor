import crypto from "node:crypto";
import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";
import { safeAssetKey } from "./media";

export async function readHistory(projectPath: string) {
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

export async function recordHistorySnapshot(
  projectPath: string | null,
  oldText: string,
  newText: string,
  summary: Record<string, unknown>,
  generatedDir: string
) {
  if (!oldText.trim() || !newText.trim()) return null;
  const targetPath = projectPath || path.join(generatedDir, `ai-applied-${Date.now()}`, "project.json");
  await fs.mkdir(path.dirname(targetPath), { recursive: true });
  if (!fsSync.existsSync(targetPath)) await fs.writeFile(targetPath, newText, "utf-8");
  const historyDir = path.join(path.dirname(targetPath), ".ave_history");
  const versionId = `${new Date().toISOString().replace(/[-:.]/g, "").replace("T", "T").slice(0, 15)}Z_${crypto.randomUUID().slice(0, 8)}`;
  const versionDir = path.join(historyDir, versionId);
  await fs.mkdir(versionDir, { recursive: true });
  let oldProject: unknown;
  let newProject: unknown;
  try {
    oldProject = JSON.parse(oldText);
  } catch {
    oldProject = { rawText: oldText };
  }
  try {
    newProject = JSON.parse(newText);
  } catch {
    newProject = { rawText: newText };
  }
  await fs.writeFile(path.join(versionDir, "old_project.json"), JSON.stringify(oldProject, null, 2) + "\n", "utf-8");
  await fs.writeFile(path.join(versionDir, "new_project.json"), JSON.stringify(newProject, null, 2) + "\n", "utf-8");
  const changeSummary = {
    id: versionId,
    timestamp: new Date().toISOString(),
    projectPath: path.resolve(targetPath),
    name: String(summary.name || summary.summary || "Restore point"),
    summary: "AI plan applied",
    ...summary
  };
  await fs.writeFile(path.join(versionDir, "change_summary.json"), JSON.stringify(changeSummary, null, 2) + "\n", "utf-8");
  return changeSummary;
}

function historyVersionDir(projectPath: string, versionId: string) {
  return path.join(path.dirname(projectPath), ".ave_history", versionId);
}

export async function duplicateHistoryVersion(projectPath: string, versionId: string, generatedDir: string) {
  const versionDir = historyVersionDir(projectPath, versionId);
  const sourcePath = path.join(versionDir, "new_project.json");
  if (!fsSync.existsSync(sourcePath)) throw new Error(`Version ${versionId} is missing its project snapshot.`);
  const text = await fs.readFile(sourcePath, "utf-8");
  const targetDir = path.join(generatedDir, `version-${safeAssetKey(versionId)}-${Date.now()}`);
  const targetPath = path.join(targetDir, "project.json");
  await fs.mkdir(targetDir, { recursive: true });
  await fs.writeFile(targetPath, text, "utf-8");
  return targetPath;
}

export async function compareHistoryVersion(projectPath: string, versionId: string) {
  const versionDir = historyVersionDir(projectPath, versionId);
  const oldPath = path.join(versionDir, "old_project.json");
  const newPath = path.join(versionDir, "new_project.json");
  if (!fsSync.existsSync(oldPath) || !fsSync.existsSync(newPath)) throw new Error(`Version ${versionId} cannot be compared.`);
  const oldText = await fs.readFile(oldPath, "utf-8");
  const newText = await fs.readFile(newPath, "utf-8");
  const oldProject = JSON.parse(oldText);
  const newProject = JSON.parse(newText);
  const oldTimeline = Array.isArray(oldProject.timeline) ? oldProject.timeline : [];
  const newTimeline = Array.isArray(newProject.timeline) ? newProject.timeline : [];
  const oldAssets = oldProject.assets && typeof oldProject.assets === "object" ? Object.keys(oldProject.assets).length : 0;
  const newAssets = newProject.assets && typeof newProject.assets === "object" ? Object.keys(newProject.assets).length : 0;
  const oldDuration = projectDurationSeconds(oldProject);
  const newDuration = projectDurationSeconds(newProject);
  return {
    versionId,
    old: { scenes: oldTimeline.length, assets: oldAssets, duration: oldDuration },
    new: { scenes: newTimeline.length, assets: newAssets, duration: newDuration },
    changes: [
      `Scenes: ${oldTimeline.length} -> ${newTimeline.length}`,
      `Assets: ${oldAssets} -> ${newAssets}`,
      `Duration: ${oldDuration.toFixed(1)}s -> ${newDuration.toFixed(1)}s`
    ],
    oldText,
    newText
  };
}

export function projectDurationSeconds(project: { project?: Record<string, unknown>; timeline?: Array<Record<string, unknown>> }) {
  const explicit = Number(project.project?.duration || 0);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  return Math.max(0, ...(project.timeline || []).map((scene) => Number(scene.start || 0) + Number(scene.duration || 0)));
}
