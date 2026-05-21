import {
  Captions,
  CheckCircle2,
  CircleHelp,
  Download,
  Eye,
  FileJson,
  FileText,
  FolderOpen,
  Image,
  Mic,
  MoreVertical,
  Music,
  Pencil,
  Plus,
  RefreshCcw,
  Search,
  Sparkles,
  Trash2,
  Video,
  X
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { type ProjectData } from "../lib/project";

function formatResolution(value: unknown) {
  if (!value || typeof value !== "object") return "-";
  const item = value as { width?: unknown; height?: unknown };
  return `${String(item.width ?? "?")}x${String(item.height ?? "?")}`;
}

type MediaBinCategory = "all" | "videos" | "images" | "audio" | "voiceovers" | "captions" | "generated" | "url" | "project";
type MediaSortMode = "name" | "date" | "duration";
type MediaContextMenu = { x: number; y: number; assetKey: string } | null;

export function AssetLibrary({
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
