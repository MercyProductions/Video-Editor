from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from media.compat import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from utils.media import media_duration, run_ffmpeg


TEMPLATE_EXTENSIONS = {".templatepack", ".json"}
EFFECT_EXTENSIONS = {".effectpack", ".transitionpack", ".motionpack"}
CAPTION_EXTENSIONS = {".srt", ".vtt", ".txt", ".captionpack"}
PROFILE_EXTENSIONS = {".creatorpack", ".brandkitpack"}
THUMBNAIL_EXTENSIONS = {".thumb.png", ".thumb.jpg", ".thumbnail.png", ".thumbnail.jpg"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | TEMPLATE_EXTENSIONS | EFFECT_EXTENSIONS | CAPTION_EXTENSIONS | PROFILE_EXTENSIONS


def default_db_path() -> Path:
    return Path(__file__).resolve().parents[2] / "output" / "asset_database" / "assets.sqlite"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    _init(con)
    return con


def index_folder(folder: Path, *, db_path: Path | None = None, previews: bool = True) -> dict[str, Any]:
    con = connect(db_path)
    scanned = 0
    indexed = 0
    errors: list[dict[str, str]] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        scanned += 1
        try:
            row = index_asset(path, con=con, previews=previews)
            indexed += 1 if row else 0
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})
    con.commit()
    return {"database": str((db_path or default_db_path()).resolve()), "folder": str(folder.resolve()), "scanned": scanned, "indexed": indexed, "errors": errors}


def index_asset(path: Path, *, con: sqlite3.Connection | None = None, previews: bool = True) -> dict[str, Any]:
    owns_connection = con is None
    con = con or connect()
    path = path.resolve()
    stat = path.stat()
    existing = con.execute("select * from assets where path = ?", (str(path),)).fetchone()
    if existing and float(existing["mtime"]) == stat.st_mtime and int(existing["size"]) == stat.st_size:
        row = _row(existing)
        if owns_connection:
            con.commit()
        return row
    asset_type = _asset_type(path)
    digest = _hash_file(path)
    metadata = _metadata(path, asset_type)
    preview_path = _generate_preview(path, digest, asset_type) if previews else None
    tags = _tags(path, asset_type, metadata)
    category = _category(path, asset_type)
    payload = {
        "path": str(path),
        "type": asset_type,
        "hash": digest,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "duration": metadata.get("duration"),
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "fps": metadata.get("fps"),
        "codec": metadata.get("codec"),
        "tags": json.dumps(tags),
        "category": category,
        "previewPath": str(preview_path) if preview_path else None,
        "indexedAt": _now(),
    }
    con.execute(
        """
        insert into assets(path,type,hash,size,mtime,duration,width,height,fps,codec,tags,category,preview_path,indexed_at)
        values(:path,:type,:hash,:size,:mtime,:duration,:width,:height,:fps,:codec,:tags,:category,:previewPath,:indexedAt)
        on conflict(path) do update set
            type=excluded.type,
            hash=excluded.hash,
            size=excluded.size,
            mtime=excluded.mtime,
            duration=excluded.duration,
            width=excluded.width,
            height=excluded.height,
            fps=excluded.fps,
            codec=excluded.codec,
            tags=excluded.tags,
            category=excluded.category,
            preview_path=excluded.preview_path,
            indexed_at=excluded.indexed_at
        """,
        payload,
    )
    if owns_connection:
        con.commit()
    return payload


def search_assets(query: str = "", *, asset_type: str | None = None, category: str | None = None, db_path: Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    con = connect(db_path)
    clauses = []
    values: list[Any] = []
    if query:
        clauses.append("(path like ? or tags like ? or category like ?)")
        like = f"%{query}%"
        values.extend([like, like, like])
    if asset_type:
        clauses.append("type = ?")
        values.append(asset_type)
    if category:
        clauses.append("category = ?")
        values.append(category)
    sql = "select * from assets"
    if clauses:
        sql += " where " + " and ".join(clauses)
    sql += " order by case when preview_path is not null then 0 else 1 end, indexed_at desc limit ?"
    values.append(limit)
    return [_row(row) for row in con.execute(sql, values)]


def duplicate_assets(*, db_path: Path | None = None) -> list[dict[str, Any]]:
    con = connect(db_path)
    rows = con.execute(
        """
        select hash, count(*) as count, sum(size) as bytes
        from assets
        group by hash
        having count(*) > 1
        order by bytes desc
        """
    ).fetchall()
    groups = []
    for row in rows:
        items = [_row(item) for item in con.execute("select * from assets where hash = ? order by path", (row["hash"],))]
        groups.append({"hash": row["hash"], "count": row["count"], "bytes": row["bytes"], "assets": items})
    return groups


def track_project_usage(project_path: Path, *, db_path: Path | None = None) -> dict[str, Any]:
    con = connect(db_path)
    data = json.loads(project_path.read_text(encoding="utf-8"))
    assets = data.get("assets", {})
    usage: dict[str, int] = {}
    missing: list[dict[str, str]] = []
    for scene in data.get("timeline", []):
        for layer in scene.get("layers", []):
            asset_key = layer.get("asset")
            if asset_key and asset_key in assets:
                resolved = _resolve(project_path, assets[asset_key])
                usage[str(resolved)] = usage.get(str(resolved), 0) + 1
                if not resolved.exists():
                    missing.append({"asset": str(asset_key), "path": str(resolved), "scene": str(scene.get("id", ""))})
    for track in data.get("audio", []):
        asset_key = track.get("asset")
        if asset_key and asset_key in assets:
            resolved = _resolve(project_path, assets[asset_key])
            usage[str(resolved)] = usage.get(str(resolved), 0) + 1
            if not resolved.exists():
                missing.append({"asset": str(asset_key), "path": str(resolved), "scene": "audio"})
    for path, count in usage.items():
        con.execute(
            "insert into usage(asset_path, project_path, count, updated_at) values(?,?,?,?) "
            "on conflict(asset_path, project_path) do update set count=excluded.count, updated_at=excluded.updated_at",
            (path, str(project_path.resolve()), count, _now()),
        )
    con.commit()
    return {"project": str(project_path.resolve()), "assetCount": len(usage), "usage": usage, "missingAssets": missing}


def database_report(*, db_path: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    con = connect(db_path)
    type_counts = {row["type"]: row["count"] for row in con.execute("select type, count(*) as count from assets group by type")}
    category_counts = {row["category"]: row["count"] for row in con.execute("select category, count(*) as count from assets group by category")}
    duplicates = duplicate_assets(db_path=db_path)
    usage_rows = [dict(row) for row in con.execute("select asset_path, sum(count) as count from usage group by asset_path order by count desc limit 20")]
    report = {
        "database": str((db_path or default_db_path()).resolve()),
        "assetCount": sum(type_counts.values()),
        "typeCounts": type_counts,
        "categoryCounts": category_counts,
        "duplicateGroupCount": len(duplicates),
        "duplicateBytes": sum(group.get("bytes") or 0 for group in duplicates),
        "topUsage": usage_rows,
        "missingFiles": _missing_files(con),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _init(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table if not exists assets (
            path text primary key,
            type text not null,
            hash text not null,
            size integer not null,
            mtime real not null,
            duration real,
            width integer,
            height integer,
            fps real,
            codec text,
            tags text not null,
            category text,
            preview_path text,
            indexed_at text not null
        );
        create index if not exists idx_assets_type on assets(type);
        create index if not exists idx_assets_hash on assets(hash);
        create index if not exists idx_assets_category on assets(category);
        create table if not exists usage (
            asset_path text not null,
            project_path text not null,
            count integer not null,
            updated_at text not null,
            primary key(asset_path, project_path)
        );
        """
    )


def _asset_type(path: Path) -> str:
    ext = path.suffix.lower()
    name = path.name.lower()
    if any(name.endswith(value) for value in THUMBNAIL_EXTENSIONS):
        return "thumbnail"
    if ext in VIDEO_EXTENSIONS:
        return "clip"
    if ext in IMAGE_EXTENSIONS:
        return "thumbnail" if "thumb" in path.stem.lower() else "image"
    if ext in AUDIO_EXTENSIONS:
        lowered = str(path).lower()
        return "music" if "music" in lowered or "song" in lowered else "sound_effect"
    if ext == ".templatepack" or (ext == ".json" and "template" in str(path).lower()):
        return "template"
    if ext in EFFECT_EXTENSIONS:
        return "effect"
    if ext in CAPTION_EXTENSIONS:
        return "caption"
    if ext in PROFILE_EXTENSIONS:
        return "creator_profile"
    if ext == ".json" and "brand" in str(path).lower():
        return "brand_kit"
    return "unknown"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(path: Path, asset_type: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {"duration": media_duration(path) if asset_type in {"clip", "music", "sound_effect"} else None}
    result = run_ffmpeg(["-hide_banner", "-i", str(path)])
    text = (result.stderr or "") + (result.stdout or "")
    codec_match = re.search(r"(Video|Audio):\s*([^,\s]+)", text)
    if codec_match:
        metadata["codec"] = codec_match.group(2)
    resolution_match = re.search(r"(\d{2,5})x(\d{2,5})", text)
    if resolution_match:
        metadata["width"] = int(resolution_match.group(1))
        metadata["height"] = int(resolution_match.group(2))
    fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", text)
    if fps_match:
        metadata["fps"] = float(fps_match.group(1))
    return metadata


def _generate_preview(path: Path, digest: str, asset_type: str) -> Path | None:
    if asset_type not in {"clip", "image", "thumbnail"}:
        return None
    target = Path(__file__).resolve().parents[2] / "output" / "asset_database" / "previews" / f"{digest[:16]}.jpg"
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    result = run_ffmpeg(["-y", "-hide_banner", "-loglevel", "error", "-i", str(path), "-frames:v", "1", "-vf", "scale=320:-1", str(target)])
    return target if result.returncode == 0 and target.exists() else None


def _tags(path: Path, asset_type: str, metadata: dict[str, Any]) -> list[str]:
    tags = {asset_type, path.suffix.lower().lstrip(".")}
    tags.update(part.lower() for part in path.stem.replace("-", "_").split("_") if part)
    if metadata.get("width") and metadata.get("height"):
        tags.add("vertical" if metadata["height"] > metadata["width"] else "landscape")
    return sorted(tags)


def _category(path: Path, asset_type: str) -> str:
    lowered = str(path).lower()
    if "music" in lowered or "song" in lowered:
        return "music"
    if "logo" in lowered or "brand" in lowered:
        return "brand"
    if asset_type in {"music", "sound_effect"}:
        return "sound"
    if asset_type in {"image", "thumbnail"}:
        return "image"
    if asset_type in {"template", "effect", "caption", "creator_profile", "brand_kit"}:
        return asset_type
    return "clip"


def _missing_files(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = []
    for row in con.execute("select path, type, category from assets"):
        if not Path(row["path"]).exists():
            rows.append({"path": row["path"], "type": row["type"], "category": row["category"]})
    return rows


def _resolve(project_path: Path, asset_value: str) -> Path:
    raw = Path(str(asset_value))
    return raw if raw.is_absolute() else (project_path.parent / raw).resolve()


def _row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["tags"] = json.loads(data.get("tags") or "[]")
    data["previewPath"] = data.pop("preview_path")
    data["indexedAt"] = data.pop("indexed_at")
    return data


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
