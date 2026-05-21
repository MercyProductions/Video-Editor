import fsSync from "node:fs";
import path from "node:path";

export type MediaAssetType = "image" | "video" | "audio" | "unknown";

export const videoImportExtensions = ["mp4", "mov", "mkv", "avi", "webm", "flv", "wmv", "mpeg", "mpg", "m4v", "ts", "mts", "m2ts"];
export const imageImportExtensions = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "svg"];
export const audioImportExtensions = ["mp3", "wav", "flac", "ogg", "aac", "m4a"];
export const allMediaImportExtensions = [...videoImportExtensions, ...imageImportExtensions, ...audioImportExtensions];

const videoExtensions = new Set(videoImportExtensions.map((value) => `.${value}`));
const imageExtensions = new Set(imageImportExtensions.map((value) => `.${value}`));
const audioExtensions = new Set(audioImportExtensions.map((value) => `.${value}`));

export function safeAssetKey(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "asset";
}

export function mediaType(filePath: string): MediaAssetType {
  const ext = path.extname(filePath).toLowerCase();
  if (imageExtensions.has(ext)) return "image";
  if (videoExtensions.has(ext)) return "video";
  if (audioExtensions.has(ext)) return "audio";
  return "unknown";
}

export function checkAssets(text: string, projectPath: string | null, fallbackRoot: string) {
  const data = JSON.parse(text);
  const projectDir = projectPath ? path.dirname(projectPath) : fallbackRoot;
  const assets = data.assets && typeof data.assets === "object" ? data.assets : {};
  return Object.entries(assets).map(([key, rawValue]) => {
    const value = String(rawValue);
    const resolved = path.isAbsolute(value) ? value : path.resolve(projectDir, value);
    const exists = fsSync.existsSync(resolved);
    const stat = exists ? fsSync.statSync(resolved) : null;
    return {
      key,
      path: resolved,
      exists,
      type: mediaType(resolved),
      modifiedMs: stat?.mtimeMs || 0,
      fileSize: stat?.size || 0
    };
  });
}
