from __future__ import annotations

from copy import deepcopy
from typing import Any

from presets.export_presets import get_export_preset


TemplateDict = dict[str, Any]


def _text(text: str, x: Any, y: Any, size: int, color: str = "#ffffff", **extra: Any) -> dict[str, Any]:
    layer = {
        "type": "text",
        "text": text,
        "x": x,
        "y": y,
        "fontSize": size,
        "color": color,
        "strokeColor": "#000000",
        "strokeWidth": 2,
    }
    layer.update(extra)
    return layer


def _video(asset: str, width: int | None = None, height: int | None = None, **extra: Any) -> dict[str, Any]:
    layer: dict[str, Any] = {"type": "video", "asset": asset, "x": 0, "y": 0}
    if width:
        layer["width"] = width
    if height:
        layer["height"] = height
    layer.update(extra)
    return layer


def _image(asset: str, x: Any = "center", y: Any = "center", scale: float = 0.7, **extra: Any) -> dict[str, Any]:
    layer: dict[str, Any] = {"type": "image", "asset": asset, "x": x, "y": y, "scale": scale}
    layer.update(extra)
    return layer


def _caption(items: list[dict[str, Any]], y: Any = "bottom", size: int = 44) -> dict[str, Any]:
    return {
        "type": "caption",
        "x": "center",
        "y": y,
        "fontSize": size,
        "color": "#ffffff",
        "strokeColor": "#000000",
        "strokeWidth": 3,
        "box": True,
        "boxColor": "#00000099",
        "boxPadding": 14,
        "items": items,
    }


TEMPLATES: dict[str, TemplateDict] = {
    "youtube_intro": {
        "name": "YouTube Intro",
        "exportPreset": "youtube_1080p",
        "requiredAssets": {
            "logo": "image",
            "intro_bg": "video",
            "music": "audio",
            "whoosh": "audio"
        },
        "transitionStyle": "crossfade",
        "musicSlots": ["music"],
        "sfxSlots": ["whoosh"],
        "placeholders": {
            "title": "Welcome Back",
            "subtitle": "New video starts now"
        },
        "project": {
            "project": {"width": 1920, "height": 1080, "fps": 60, "duration": 8, "background": "#05070d"},
            "assets": {
                "logo": "assets/logo.png",
                "intro_bg": "assets/intro_bg.mp4",
                "music": "assets/music.wav",
                "whoosh": "assets/whoosh.wav"
            },
            "timeline": [
                {
                    "id": "brand_reveal",
                    "start": 0,
                    "duration": 4,
                    "layers": [
                        _video("intro_bg", 1920, 1080, opacity=0.55, blur=2),
                        _image("logo", scale=0.42, animation={"in": "zoomIn", "out": "fade", "duration": 0.7}),
                        _text("Welcome Back", "center", 820, 72, animation={"in": "slideUp", "out": "fade", "duration": 0.6})
                    ],
                    "transitionOut": {"type": "crossfade", "duration": 0.7}
                },
                {
                    "id": "title_card",
                    "start": 4,
                    "duration": 4,
                    "layers": [
                        _text("New video starts now", "center", "center", 78, box=True, boxColor="#00000099", boxPadding=22, animation={"in": "typewriter", "out": "fade", "duration": 0.6})
                    ]
                }
            ],
            "audio": [
                {"asset": "music", "start": 0, "volume": 0.35, "fadeIn": 0.5, "fadeOut": 1},
                {"asset": "whoosh", "start": 0.3, "duration": 1, "volume": 0.35}
            ]
        }
    },
    "tiktok_reels_short": {
        "name": "TikTok/Reels Short",
        "exportPreset": "tiktok_reels",
        "requiredAssets": {"clip1": "video", "clip2": "video", "music": "audio", "pop": "audio"},
        "transitionStyle": "slide",
        "musicSlots": ["music"],
        "sfxSlots": ["pop"],
        "placeholders": {"hook": "Stop scrolling", "payoff": "Here is the result"},
        "project": {
            "project": {"width": 1080, "height": 1920, "fps": 60, "duration": 12, "background": "#050505"},
            "assets": {"clip1": "assets/clip1.mp4", "clip2": "assets/clip2.mp4", "music": "assets/music.wav", "pop": "assets/pop.wav"},
            "timeline": [
                {"id": "hook", "start": 0, "duration": 4, "layers": [_video("clip1", 1080, 1920, contrast=1.15), _text("Stop scrolling", "center", 180, 72, box=True, boxColor="#ff004499", animation={"in": "pulse", "out": "fade", "duration": 0.4})], "transitionOut": {"type": "slide", "duration": 0.35, "direction": "left"}},
                {"id": "payoff", "start": 4, "duration": 8, "layers": [_video("clip2", 1080, 1920), _caption([{"text": "Here is the result", "start": 0.3, "duration": 2.5}, {"text": "Built automatically from JSON", "start": 3.1, "duration": 3}], y=1580, size=54)]}
            ],
            "audio": [
                {"asset": "music", "start": 0, "volume": 0.45, "fadeIn": 0.2, "fadeOut": 0.8},
                {"asset": "pop", "start": 0.2, "duration": 0.5, "volume": 0.45},
                {"asset": "pop", "start": 4, "duration": 0.5, "volume": 0.35}
            ]
        }
    },
    "gaming_montage": {
        "name": "Gaming Montage",
        "exportPreset": "youtube_1080p",
        "requiredAssets": {"clip1": "video", "clip2": "video", "clip3": "video", "music": "audio", "impact": "audio"},
        "transitionStyle": "zoom",
        "musicSlots": ["music"],
        "sfxSlots": ["impact"],
        "placeholders": {"title": "Top Plays", "caption": "Clutch moment"},
        "project": {
            "project": {"width": 1920, "height": 1080, "fps": 60, "duration": 18, "background": "#050000"},
            "assets": {"clip1": "assets/clip1.mp4", "clip2": "assets/clip2.mp4", "clip3": "assets/clip3.mp4", "music": "assets/music.wav", "impact": "assets/impact.wav"},
            "timeline": [
                {"id": "open", "start": 0, "duration": 3, "layers": [_text("TOP PLAYS", "center", "center", 96, "#ff2d2d", effects=["shake"], animation={"in": "zoomIn", "out": "fade", "duration": 0.5})], "transitionOut": {"type": "zoom", "duration": 0.35}},
                {"id": "clip_1", "start": 3, "duration": 5, "layers": [_video("clip1", 1920, 1080, contrast=1.2), _caption([{"text": "Clutch moment", "start": 1, "duration": 2.5}], y=930)], "transitionOut": {"type": "zoom", "duration": 0.3}},
                {"id": "clip_2", "start": 8, "duration": 5, "layers": [_video("clip2", 1920, 1080, speed=1.08), _text("+250 XP", 80, 80, 54, "#ff2d2d", animation={"in": "slideRight", "out": "fade", "duration": 0.35})], "transitionOut": {"type": "crossfade", "duration": 0.4}},
                {"id": "clip_3", "start": 13, "duration": 5, "layers": [_video("clip3", 1920, 1080), _text("VICTORY", "center", 120, 78, "#ffffff", box=True, boxColor="#9f123999", animation={"in": "pulse", "out": "fade", "duration": 0.45})]}
            ],
            "audio": [
                {"asset": "music", "start": 0, "volume": 0.48, "fadeIn": 0.2, "fadeOut": 1},
                {"asset": "impact", "start": 3, "duration": 0.5, "volume": 0.5},
                {"asset": "impact", "start": 8, "duration": 0.5, "volume": 0.45},
                {"asset": "impact", "start": 13, "duration": 0.5, "volume": 0.45}
            ]
        }
    },
    "product_promo": {
        "name": "Product Promo",
        "exportPreset": "square",
        "requiredAssets": {"product": "image", "broll": "video", "music": "audio"},
        "transitionStyle": "fadeToBlack",
        "musicSlots": ["music"],
        "sfxSlots": [],
        "placeholders": {"productName": "Aegis Pro", "tagline": "Built for speed"},
        "project": {
            "project": {"width": 1080, "height": 1080, "fps": 30, "duration": 14, "background": "#f8fafc"},
            "assets": {"product": "assets/product.png", "broll": "assets/broll.mp4", "music": "assets/music.wav"},
            "timeline": [
                {"id": "hero", "start": 0, "duration": 5, "layers": [_image("product", scale=0.72, animation={"in": "zoomIn", "out": "fade", "duration": 0.6}), _text("Aegis Pro", "center", 820, 70, "#0f172a")], "transitionOut": {"type": "crossfade", "duration": 0.6}},
                {"id": "benefits", "start": 5, "duration": 5, "layers": [_video("broll", 1080, 1080, opacity=0.75), _text("Built for speed", "center", "center", 66, "#ffffff", box=True, boxColor="#0f172acc", boxPadding=20)], "transitionOut": {"type": "fadeToBlack", "duration": 0.5}},
                {"id": "cta", "start": 10, "duration": 4, "layers": [_text("Launch-ready today", "center", "center", 68, "#0f172a"), _text("Try it now", "center", 690, 42, "#2563eb")]}
            ],
            "audio": [{"asset": "music", "start": 0, "volume": 0.35, "fadeIn": 0.4, "fadeOut": 1}]
        }
    },
    "lyric_video": {
        "name": "Lyric Video",
        "exportPreset": "youtube_1080p",
        "requiredAssets": {"background": "video", "music": "audio"},
        "transitionStyle": "crossfade",
        "musicSlots": ["music"],
        "sfxSlots": [],
        "placeholders": {"line1": "First lyric line", "line2": "Second lyric line"},
        "project": {
            "project": {"width": 1920, "height": 1080, "fps": 60, "duration": 16, "background": "#05070d"},
            "assets": {"background": "assets/background.mp4", "music": "assets/music.wav"},
            "timeline": [
                {"id": "lyrics", "start": 0, "duration": 16, "layers": [_video("background", 1920, 1080, blur=1, opacity=0.7), _caption([{"text": "First lyric line", "start": 1, "duration": 3}, {"text": "Second lyric line", "start": 5, "duration": 3}, {"text": "Final chorus line", "start": 10, "duration": 4}], y="center", size=72)]}
            ],
            "audio": [{"asset": "music", "start": 0, "volume": 0.8, "fadeIn": 0.3, "fadeOut": 1}]
        }
    },
    "slideshow": {
        "name": "Slideshow",
        "exportPreset": "youtube_1080p",
        "requiredAssets": {"photo1": "image", "photo2": "image", "photo3": "image", "music": "audio"},
        "transitionStyle": "crossfade",
        "musicSlots": ["music"],
        "sfxSlots": [],
        "placeholders": {"title": "Memories", "caption": "A simple slideshow"},
        "project": {
            "project": {"width": 1920, "height": 1080, "fps": 30, "duration": 15, "background": "#111827"},
            "assets": {"photo1": "assets/photo1.png", "photo2": "assets/photo2.png", "photo3": "assets/photo3.png", "music": "assets/music.wav"},
            "timeline": [
                {"id": "photo_1", "start": 0, "duration": 5, "layers": [_image("photo1", scale=1.25, animation={"in": "zoomIn", "out": "fade", "duration": 0.7}), _text("Memories", "center", 820, 64)], "transitionOut": {"type": "crossfade", "duration": 0.8}},
                {"id": "photo_2", "start": 5, "duration": 5, "layers": [_image("photo2", scale=1.25, animation={"in": "zoomOut", "out": "fade", "duration": 0.7})], "transitionOut": {"type": "crossfade", "duration": 0.8}},
                {"id": "photo_3", "start": 10, "duration": 5, "layers": [_image("photo3", scale=1.25), _text("A simple slideshow", "center", 850, 52)]}
            ],
            "audio": [{"asset": "music", "start": 0, "volume": 0.35, "fadeIn": 0.8, "fadeOut": 1.2}]
        }
    },
    "meme_edit": {
        "name": "Meme Edit",
        "exportPreset": "square",
        "requiredAssets": {"clip": "video", "reaction": "image", "music": "audio", "hit": "audio"},
        "transitionStyle": "cut",
        "musicSlots": ["music"],
        "sfxSlots": ["hit"],
        "placeholders": {"topText": "WHEN THE JSON RENDERS", "bottomText": "FIRST TRY"},
        "project": {
            "project": {"width": 1080, "height": 1080, "fps": 30, "duration": 9, "background": "#000000"},
            "assets": {"clip": "assets/clip.mp4", "reaction": "assets/reaction.png", "music": "assets/music.wav", "hit": "assets/hit.wav"},
            "timeline": [
                {"id": "setup", "start": 0, "duration": 5, "layers": [_video("clip", 1080, 1080), _text("WHEN THE JSON RENDERS", "center", 70, 52, "#ffffff", strokeWidth=4)], "transitionOut": {"type": "cut", "duration": 0}},
                {"id": "punchline", "start": 5, "duration": 4, "layers": [_image("reaction", scale=1.15, effects=["shake"]), _text("FIRST TRY", "center", 890, 60, "#ffffff", strokeWidth=5, animation={"in": "pulse", "duration": 0.2})]}
            ],
            "audio": [
                {"asset": "music", "start": 0, "volume": 0.32, "fadeOut": 0.8},
                {"asset": "hit", "start": 5, "duration": 0.5, "volume": 0.65}
            ]
        }
    },
    "tutorial_video": {
        "name": "Tutorial Video",
        "exportPreset": "youtube_1080p",
        "requiredAssets": {"screen": "video", "music": "audio", "click": "audio"},
        "transitionStyle": "slide",
        "musicSlots": ["music"],
        "sfxSlots": ["click"],
        "placeholders": {"title": "How to build an edit", "step1": "Step 1: choose a template"},
        "project": {
            "project": {"width": 1920, "height": 1080, "fps": 60, "duration": 20, "background": "#0f172a"},
            "assets": {"screen": "assets/screen.mp4", "music": "assets/music.wav", "click": "assets/click.wav"},
            "timeline": [
                {"id": "title", "start": 0, "duration": 4, "layers": [_text("How to build an edit", "center", "center", 76, "#ffffff", box=True, boxColor="#0f172acc", animation={"in": "typewriter", "out": "fade", "duration": 0.6})], "transitionOut": {"type": "slide", "direction": "left", "duration": 0.5}},
                {"id": "walkthrough", "start": 4, "duration": 12, "layers": [_video("screen", 1920, 1080), _caption([{"text": "Step 1: choose a template", "start": 0.5, "duration": 3}, {"text": "Step 2: add your clips", "start": 4.5, "duration": 3}, {"text": "Step 3: render the MP4", "start": 8.5, "duration": 3}], y=920)], "transitionOut": {"type": "crossfade", "duration": 0.6}},
                {"id": "outro", "start": 16, "duration": 4, "layers": [_text("Done.", "center", "center", 88, "#ffffff", animation={"in": "zoomIn", "duration": 0.5})]}
            ],
            "audio": [
                {"asset": "music", "start": 0, "volume": 0.25, "fadeIn": 0.5, "fadeOut": 1},
                {"asset": "click", "start": 4.6, "duration": 0.3, "volume": 0.4},
                {"asset": "click", "start": 8.6, "duration": 0.3, "volume": 0.35},
                {"asset": "click", "start": 12.6, "duration": 0.3, "volume": 0.35}
            ]
        }
    },
}


def template_names() -> list[str]:
    return sorted(TEMPLATES)


def list_templates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in template_names():
        item = TEMPLATES[key]
        rows.append(
            {
                "key": key,
                "name": item["name"],
                "exportPreset": item["exportPreset"],
                "requiredAssets": item["requiredAssets"],
                "transitionStyle": item["transitionStyle"],
                "musicSlots": item["musicSlots"],
                "sfxSlots": item["sfxSlots"],
            }
        )
    return rows


def create_project_from_template(name: str, *, preset: str | None = None) -> dict[str, Any]:
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in TEMPLATES:
        valid = ", ".join(template_names())
        raise ValueError(f"Unknown template '{name}'. Valid templates: {valid}")

    template = TEMPLATES[key]
    project = deepcopy(template["project"])
    export_preset = get_export_preset(preset).key if preset else template["exportPreset"]
    project["exportPreset"] = export_preset
    project["metadata"] = {
        "template": key,
        "templateName": template["name"],
        "requiredAssets": template["requiredAssets"],
        "transitionStyle": template["transitionStyle"],
        "musicSlots": template["musicSlots"],
        "sfxSlots": template["sfxSlots"],
        "placeholders": template["placeholders"],
    }
    return project
