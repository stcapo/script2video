from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 1080
HEIGHT = 1920
FPS = 30
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "+8%"
TTS_BACKEND = "vcut"
VCUT_TTS_MODE = "mbaiscvip"
VCUT_TTS_FORMAT = "mp3"
VCUT_TTS_SPEED = "0"
VCUT_TTS_MAX_ATTEMPTS = 3
VCUT_TTS_TIMEOUT_SECONDS = 120
TTS_REQUEST_MAX_CHARS = 299
TTS_CHUNKING_MODE = "max_request_length"
TTS_CHUNKING_SCOPE = "scene"
TTS_CHUNKING_TIMING = "weighted_estimate"
SUBTITLE_LEAD_SECONDS = 0.04
SUBTITLE_HOLD_SECONDS = 0.18
SUBTITLE_MIN_DURATION_SECONDS = 0.35
TIMING_CALIBRATION_LIMIT_SECONDS = 0.5
SUBTITLE_FONT_SIZE = 92
SUBTITLE_MARGIN_V = 300
SUBTITLE_MIN_CHARS = 8
SUBTITLE_MAX_CHARS = 16
SUBTITLE_DISPLAY_MAX_CHARS = 10
VALID_VISUALS = {
    "question",
    "calendar",
    "three_nodes",
    "pipeline",
    "checklist",
    "gates",
    "five_tasks",
    "quote",
}

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
FRAME_DIR = BUILD_DIR / "frames"
DIST_DIR = ROOT / "dist"
OUTPUT_VIDEO = DIST_DIR / "ai_workflow_nodes.mp4"
NARRATION_FILE = BUILD_DIR / "narration.wav"
SUBTITLE_FILE = BUILD_DIR / "subtitles.ass"
CONCAT_FILE = BUILD_DIR / "frames.txt"
AUDIO_CHUNK_DIR = BUILD_DIR / "audio_chunks"
AUDIO_CONCAT_FILE = BUILD_DIR / "audio_chunks.txt"
FOOTER_TEXT = "关系边界：不安本身值得被看见"

FONT_REGULAR = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")
FONT_LIGHT = Path("C:/Windows/Fonts/msyhl.ttc")


@dataclass(frozen=True)
class Scene:
    slug: str
    label: str
    title: str
    headline: str
    body: str
    narration: str
    accent: tuple[int, int, int]
    visual: str
    visual_texts: tuple[str, ...] = ()


@dataclass(frozen=True)
class WordTiming:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class SubtitleEntry:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class TTSGroup:
    subtitle_lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "".join(self.subtitle_lines)


SCENES = [
    Scene(
        slug="01_open",
        label="01 / 08",
        title="开场问题",
        headline="感觉快了\n真的快了吗？",
        body="很多人说自己在用 AI 提效，但真问每天到底省了多少时间，往往答不上来。",
        narration=(
            "很多人说自己在用 AI 提效，但真问每天到底省了多少时间，往往答不上来。"
            "大多数回答其实都是，感觉快了不少。可感觉快了，和真的快了，中间差着一整个工作流。"
            "你一直在点按钮、改提示词、看输出，会很容易误以为自己一直处在高效状态。"
        ),
        accent=(57, 220, 198),
        visual="question",
    ),
    Scene(
        slug="02_log",
        label="02 / 08",
        title="两周记录",
        headline="我做了一个\n有点笨的实验",
        body="连续两周，每天晚上花十分钟，记录 AI 到底帮我省了多少时间。",
        narration=(
            "我曾经连续两周记录每天用 AI 做了什么、实际省了多少时间。"
            "注意，不是计划省多少，也不是主观觉得快多少，而是这件事最后真的少花了多少时间。"
            "这个动作有点笨，但它会把很多模糊的感觉，变成一张能看的表。"
        ),
        accent=(255, 209, 102),
        visual="calendar",
    ),
    Scene(
        slug="03_result",
        label="03 / 08",
        title="意外发现",
        headline="真正省时的\n只有三类节点",
        body="结构清楚、标准明确、我能快速判断对错。其余很多时候都在调提示词和改半成品。",
        narration=(
            "两周后我再看那张表，结果挺反直觉。"
            "我以为 AI 是全方位提效，实际上真正稳定省时间的只有几类任务。"
            "这些任务通常结构清楚、标准明确、我能快速判断对错。"
            "其他时候，时间花在调提示词、查它编出来的内容、把半成品改成能用的版本上，甚至比自己做还慢。"
        ),
        accent=(255, 130, 112),
        visual="three_nodes",
    ),
    Scene(
        slug="04_bottleneck",
        label="04 / 08",
        title="系统瓶颈",
        headline="瓶颈不是工具\n而是节点",
        body="一个系统想提速，不能哪儿都使劲，要先找到真正卡住整体速度的环节。",
        narration=(
            "后来我换了个思路：提效不是把所有事交给 AI，"
            "而是先找到工作流里的瓶颈节点。"
            "一个系统想提速，不能哪儿都使劲。你得先知道到底是哪个环节拖慢了整体速度。"
            "工作流也是一样，一天不是一个任务，而是十几个节点串起来。"
        ),
        accent=(96, 165, 250),
        visual="pipeline",
    ),
    Scene(
        slug="05_questions",
        label="05 / 08",
        title="三问框架",
        headline="值不值得交给 AI\n先问三个问题",
        body="交付标准能不能一句话说清楚？验证输出快不快？这个任务出现频率高不高？",
        narration=(
            "判断一个任务值不值得交给 AI，我只问三个问题："
            "交付标准能不能一句话说清楚？验证输出快不快？这个任务出现频率高不高？"
            "说不清交付标准，AI 就只能猜，你会陷进反复调整。"
            "验证太慢，检查成本会吃掉全部收益。"
            "频率太低，就算能省一点时间，也不值得优先优化。"
        ),
        accent=(57, 220, 198),
        visual="checklist",
    ),
    Scene(
        slug="06_boundary",
        label="06 / 08",
        title="边界条件",
        headline="三个都是“是”\n才值得接 AI",
        body="有一个明显不是，就先别急。创造性强、标准模糊的任务，AI 更像思考伙伴。",
        narration=(
            "三个都是是，就值得接 AI。有一个明显不是，就先别急。"
            "这个方法适合边界清楚的工作，比如代码、文档、翻译、数据整理。"
            "但如果任务高度创造性、标准本来就模糊，比如想一个全新的策略，或者做需要大量试错的设计，"
            "AI 更适合当陪你想的对手，而不是替你交付的工具。"
        ),
        accent=(196, 181, 253),
        visual="gates",
    ),
    Scene(
        slug="07_action",
        label="07 / 08",
        title="行动建议",
        headline="明天先做\n一件小事",
        body="拿今天做过的五件事，用这三个问题过一遍，找出真正适合交给 AI 的节点。",
        narration=(
            "还有一点，记录本身也有成本。"
            "我建议记录两周，是因为人对自己时间的估计经常不准，需要用数据校正一次。"
            "校正完，形成判断，就可以停了。"
            "明天你可以先拿今天做过的五件事，用这三个问题过一遍。"
        ),
        accent=(255, 209, 102),
        visual="five_tasks",
    ),
    Scene(
        slug="08_close",
        label="08 / 08",
        title="结尾金句",
        headline="别追十个新工具\n先摸清你的工作流",
        body="真正该优化的，不是工具数量，而是你一天里那几个关键节点。",
        narration=(
            "你会更清楚，真正该优化的，不是工具数量，而是那几个关键节点。"
            "工具会一直更新，这是学不完的。"
            "但你自己的工作流就那么长，节点就那么多。"
            "把它摸清楚一次，比追十个新工具都值。"
        ),
        accent=(57, 220, 198),
        visual="quote",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a vertical narrated video from scene JSON.")
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to a JSON file containing video settings and scenes.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Override output video path. Relative paths are resolved from the project root.",
    )
    return parser.parse_args()


def as_text(value: object, field: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "".join(value)
    raise SystemExit(f"Invalid scene field '{field}': expected string or list of strings.")


def as_text_tuple(value: object, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise SystemExit(f"Invalid scene field '{field}': expected string or list of strings.")


def parse_accent(value: object, scene_slug: str) -> tuple[int, int, int]:
    if (
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(item, int) and 0 <= item <= 255 for item in value)
    ):
        return (value[0], value[1], value[2])
    raise SystemExit(f"Invalid accent for scene '{scene_slug}': expected [r, g, b] integers.")


def scene_from_dict(data: dict[str, object], index: int, total: int) -> Scene:
    slug = str(data.get("slug") or f"{index + 1:02d}_scene")
    visual = str(data.get("visual") or "")
    if visual not in VALID_VISUALS:
        raise SystemExit(
            f"Invalid visual '{visual}' for scene '{slug}'. "
            f"Valid values: {', '.join(sorted(VALID_VISUALS))}"
        )

    return Scene(
        slug=slug,
        label=str(data.get("label") or f"{index + 1:02d} / {total:02d}"),
        title=str(data.get("title") or ""),
        headline=as_text(data.get("headline"), "headline"),
        body=as_text(data.get("body"), "body"),
        narration=as_text(data.get("narration"), "narration"),
        accent=parse_accent(data.get("accent"), slug),
        visual=visual,
        visual_texts=as_text_tuple(data.get("visual_texts"), "visual_texts"),
    )


def resolve_project_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def read_dotenv(path: Path = ROOT / ".env") -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_value(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key) or read_dotenv().get(key) or default


def load_input_json(path: Path) -> None:
    global FOOTER_TEXT, OUTPUT_VIDEO, RATE, SCENES, TTS_BACKEND, TTS_CHUNKING_MODE, TTS_CHUNKING_SCOPE, TTS_CHUNKING_TIMING, TTS_REQUEST_MAX_CHARS, VCUT_TTS_FORMAT, VCUT_TTS_MODE, VCUT_TTS_SPEED, VOICE

    input_path = resolve_project_path(path)
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Unable to read input JSON: {input_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {input_path}: {exc}") from exc

    if isinstance(payload, list):
        video_settings: dict[str, object] = {}
        scene_items = payload
    elif isinstance(payload, dict):
        video_settings = payload.get("video") if isinstance(payload.get("video"), dict) else {}
        scene_items = payload.get("scenes")
    else:
        raise SystemExit("Input JSON must be an object with 'scenes' or a scene array.")

    if not isinstance(scene_items, list) or not scene_items:
        raise SystemExit("Input JSON must contain a non-empty 'scenes' array.")
    if not all(isinstance(item, dict) for item in scene_items):
        raise SystemExit("Every item in 'scenes' must be an object.")

    VOICE = str(video_settings.get("voice") or VOICE)
    RATE = str(video_settings.get("rate") or RATE)
    TTS_BACKEND = str(video_settings.get("tts_backend") or TTS_BACKEND)
    if isinstance(video_settings.get("vcut"), dict):
        vcut_settings = video_settings["vcut"]
        VCUT_TTS_MODE = str(vcut_settings.get("mode") or VCUT_TTS_MODE)
        VCUT_TTS_FORMAT = str(vcut_settings.get("format") or VCUT_TTS_FORMAT)
        VCUT_TTS_SPEED = str(vcut_settings.get("speed") or VCUT_TTS_SPEED)
    if isinstance(video_settings.get("tts_chunking"), dict):
        chunking_settings = video_settings["tts_chunking"]
        TTS_CHUNKING_MODE = str(chunking_settings.get("mode") or TTS_CHUNKING_MODE)
        TTS_CHUNKING_SCOPE = str(chunking_settings.get("scope") or TTS_CHUNKING_SCOPE)
        TTS_CHUNKING_TIMING = str(chunking_settings.get("timing") or TTS_CHUNKING_TIMING)
        if chunking_settings.get("max_chars") is not None:
            TTS_REQUEST_MAX_CHARS = int(chunking_settings["max_chars"])
    FOOTER_TEXT = str(video_settings.get("footer") or FOOTER_TEXT)
    if video_settings.get("output"):
        OUTPUT_VIDEO = resolve_project_path(Path(str(video_settings["output"])))

    SCENES = [scene_from_dict(item, index, len(scene_items)) for index, item in enumerate(scene_items)]


def apply_cli_overrides(args: argparse.Namespace) -> None:
    global OUTPUT_VIDEO

    if args.input:
        load_input_json(args.input)
    if args.output:
        OUTPUT_VIDEO = resolve_project_path(args.output)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def ensure_tools() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise SystemExit(f"Missing required command: {', '.join(missing)}")


def ensure_dirs() -> None:
    BUILD_DIR.mkdir(exist_ok=True)
    FRAME_DIR.mkdir(exist_ok=True)
    AUDIO_CHUNK_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)
    OUTPUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    for file in FRAME_DIR.glob("*.png"):
        file.unlink()
    for pattern in ("*.mp3", "*.wav"):
        for file in AUDIO_CHUNK_DIR.glob(pattern):
            file.unlink()


def font(size: int, bold: bool = False, light: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_LIGHT if light else FONT_REGULAR
    if not path.exists():
        raise SystemExit(f"Missing Chinese font: {path}")
    return ImageFont.truetype(str(path), size=size)


def text_bbox(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int, int, int]:
    return draw.textbbox(xy, text, font=fnt)


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> int:
    box = text_bbox(draw, (0, 0), text, fnt)
    return box[2] - box[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and text_width(draw, candidate, fnt) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_multiline(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    x: int,
    y: int,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    spacing: int,
    anchor: str = "la",
) -> int:
    cursor = y
    for line in lines:
        draw.text((x, cursor), line, font=fnt, fill=fill, anchor=anchor)
        box = text_bbox(draw, (x, cursor), line, fnt)
        cursor += (box[3] - box[1]) + spacing
    return cursor


def make_background(scene: Scene, index: int) -> Image.Image:
    top = np.array([9, 16, 29], dtype=np.float32)
    bottom = np.array([17, 24, 39], dtype=np.float32)
    y = np.linspace(0, 1, HEIGHT, dtype=np.float32)[:, None]
    gradient = top * (1 - y) + bottom * y
    bg = np.repeat(gradient[:, None, :], WIDTH, axis=1)

    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    for cx, cy, radius, strength in [
        (180 + index * 47 % 760, 330, 460, 0.22),
        (900 - index * 31 % 620, 1280, 520, 0.14),
    ]:
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        mask = np.clip(1 - dist / radius, 0, 1)[:, :, None]
        color = np.array(scene.accent, dtype=np.float32)
        bg = bg * (1 - mask * strength) + color * mask * strength

    noise = np.random.default_rng(42 + index).normal(0, 1.9, bg.shape)
    bg = np.clip(bg + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(bg, "RGB").filter(ImageFilter.GaussianBlur(0.25))


def draw_header(draw: ImageDraw.ImageDraw, scene: Scene, index: int) -> None:
    accent = scene.accent
    small = font(32, bold=True)
    label_w = text_width(draw, scene.label, small) + 46
    draw.rounded_rectangle((70, 86, 70 + label_w, 142), radius=22, fill=(*accent, 38), outline=(*accent, 170), width=2)
    draw.text((93, 99), scene.label, font=small, fill=(225, 245, 250))
    draw.text((70, 169), scene.title, font=font(42, bold=True), fill=accent)

    progress_x = 70
    progress_y = 1788
    progress_w = 940
    draw.rounded_rectangle((progress_x, progress_y, progress_x + progress_w, progress_y + 10), radius=5, fill=(255, 255, 255, 35))
    draw.rounded_rectangle(
        (progress_x, progress_y, progress_x + progress_w * (index + 1) / len(SCENES), progress_y + 10),
        radius=5,
        fill=accent,
    )


def scene_visual_texts(scene: Scene, defaults: list[str], count: int | None = None) -> list[str]:
    texts = list(scene.visual_texts) + defaults
    return texts[:count] if count is not None else texts


def draw_question_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    center_x = 540
    y = 760
    texts = scene_visual_texts(scene, ["说不上来的不安", "本身就是答案"], 2)
    draw.rounded_rectangle((170, y, 910, y + 310), radius=36, fill=(255, 255, 255, 22), outline=(*scene.accent, 180), width=3)
    draw.text((center_x, y + 62), texts[0], font=font(60, bold=True), fill=(245, 250, 255), anchor="ma")
    draw.text((center_x, y + 166), texts[1], font=font(52, bold=True), fill=scene.accent, anchor="ma")
    draw.line((260, y + 245, 820, y + 245), fill=(255, 255, 255, 70), width=3)
    for x in (290, 540, 790):
        draw.ellipse((x - 14, y + 231, x + 14, y + 259), fill=scene.accent)


def draw_calendar_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    texts = scene_visual_texts(scene, ["先观察，再交付隐私"], 1)
    start_x, start_y = 190, 775
    cell = 86
    for row in range(2):
        for col in range(7):
            x = start_x + col * (cell + 14)
            y = start_y + row * (cell + 18)
            fill = (*scene.accent, 70) if (row, col) in [(0, 1), (0, 4), (1, 2), (1, 5)] else (255, 255, 255, 25)
            draw.rounded_rectangle((x, y, x + cell, y + cell), radius=18, fill=fill, outline=(255, 255, 255, 55), width=2)
            draw.text((x + cell / 2, y + 25), str(row * 7 + col + 1), font=font(30, bold=True), fill=(232, 240, 248), anchor="ma")
            draw.text((x + cell / 2, y + 56), "day", font=font(18), fill=(180, 195, 210), anchor="ma")
    draw.text((540, 1068), texts[0], font=font(44, bold=True), fill=scene.accent, anchor="ma")


def draw_three_nodes_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    items = scene_visual_texts(scene, ["认识不久", "情绪不稳", "急要地址"], 3)
    for idx, item in enumerate(items):
        x = 140 + idx * 270
        y = 820
        draw.ellipse((x, y, x + 170, y + 170), fill=(*scene.accent, 42), outline=scene.accent, width=4)
        draw.text((x + 85, y + 60), f"{idx + 1}", font=font(48, bold=True), fill=scene.accent, anchor="ma")
        draw.text((x + 85, y + 205), item, font=font(36, bold=True), fill=(245, 248, 255), anchor="ma")
        if idx < 2:
            draw.line((x + 178, y + 85, x + 260, y + 85), fill=(255, 255, 255, 80), width=4)


def draw_pipeline_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    y = 850
    labels = scene_visual_texts(scene, ["认识", "观察", "边界", "确认", "再敞开"], 6)
    nodes = [
        (85, 110, labels[0]),
        (275, 110, labels[1]),
        (475, 190, labels[2]),
        (745, 110, labels[3]),
        (925, 110, labels[4]),
    ]
    for idx, (x, w, label) in enumerate(nodes):
        is_focus = idx == 2
        fill = (*scene.accent, 80) if is_focus else (255, 255, 255, 24)
        outline = scene.accent if is_focus else (255, 255, 255, 60)
        draw.rounded_rectangle((x, y, x + w, y + 128), radius=24, fill=fill, outline=outline, width=3)
        draw.text((x + w / 2, y + 44), label, font=font(35, bold=True), fill=(245, 250, 255), anchor="ma")
        if is_focus:
            draw.text((x + w / 2, y + 88), "先暂停", font=font(25), fill=(230, 240, 255), anchor="ma")
        if idx < len(nodes) - 1:
            next_x = nodes[idx + 1][0]
            line_start = x + w + 18
            line_end = next_x - 22
            draw.line((line_start, y + 64, line_end, y + 64), fill=scene.accent, width=5)
            draw.polygon([(line_end, y + 64), (line_end - 18, y + 51), (line_end - 18, y + 77)], fill=scene.accent)
    draw.text((540, 1100), labels[5], font=font(46, bold=True), fill=scene.accent, anchor="ma")


def draw_checklist_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    items = scene_visual_texts(scene, ["真的了解他吗？", "情绪稳定吗？", "我愿意给吗？"], 3)
    y = 760
    for idx, item in enumerate(items):
        top = y + idx * 148
        draw.rounded_rectangle((130, top, 950, top + 108), radius=24, fill=(255, 255, 255, 25), outline=(255, 255, 255, 58), width=2)
        box_x = 170
        draw.rounded_rectangle((box_x, top + 30, box_x + 48, top + 78), radius=12, fill=(*scene.accent, 50), outline=scene.accent, width=3)
        draw.line((box_x + 12, top + 54, box_x + 23, top + 68), fill=scene.accent, width=5)
        draw.line((box_x + 23, top + 68, box_x + 39, top + 41), fill=scene.accent, width=5)
        draw.text((250, top + 31), item, font=font(46, bold=True), fill=(245, 250, 255))


def draw_gates_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    x = 170
    labels = scene_visual_texts(scene, ["安全", "稳定", "自愿", "有一个不是，就先别急"], 4)
    for idx, label in enumerate(labels[:3]):
        top = 770 + idx * 130
        draw.rounded_rectangle((x, top, x + 740, top + 82), radius=18, fill=(*scene.accent, 44), outline=scene.accent, width=2)
        draw.text((x + 52, top + 21), "YES", font=font(30, bold=True), fill=scene.accent)
        draw.text((x + 184, top + 17), label, font=font(38, bold=True), fill=(245, 248, 255))
    draw.rounded_rectangle((262, 1190, 818, 1294), radius=26, fill=(255, 255, 255, 25), outline=(255, 255, 255, 70), width=2)
    draw.text((540, 1222), labels[3], font=font(40, bold=True), fill=(250, 250, 255), anchor="ma")


def draw_five_tasks_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    labels = scene_visual_texts(scene, ["停一下", "不解释", "不交出", "找支持", "保留证据", "先保护自己"], 6)
    start_y = 765
    for idx in range(5):
        top = start_y + idx * 86
        alpha = 55 if idx in (1, 3) else 24
        draw.rounded_rectangle((185, top, 895, top + 56), radius=16, fill=(*scene.accent, alpha), outline=(255, 255, 255, 45), width=2)
        draw.text((220, top + 13), labels[idx], font=font(28, bold=True), fill=(235, 242, 250))
        if idx in (1, 3):
            draw.text((785, top + 13), "优先", font=font(28, bold=True), fill=scene.accent)
    draw.text((540, 1260), labels[5], font=font(40, bold=True), fill=scene.accent, anchor="ma")


def draw_quote_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    draw.rounded_rectangle((120, 725, 960, 1180), radius=36, fill=(255, 255, 255, 23), outline=(*scene.accent, 150), width=3)
    draw.text((185, 785), "“", font=font(118, bold=True), fill=scene.accent)
    texts = scene_visual_texts(scene, ["害怕不是矫情", "边界不是冷漠", "先保护自己", "说不上来的不安，本身就是答案"], 4)
    quote_lines = texts[:3]
    draw_multiline(draw, quote_lines, 540, 850, font(60, bold=True), (246, 250, 255), 24, anchor="ma")
    draw.text((540, 1118), texts[3], font=font(35, bold=True), fill=scene.accent, anchor="ma")


def draw_scene_visual(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    visuals = {
        "question": draw_question_visual,
        "calendar": draw_calendar_visual,
        "three_nodes": draw_three_nodes_visual,
        "pipeline": draw_pipeline_visual,
        "checklist": draw_checklist_visual,
        "gates": draw_gates_visual,
        "five_tasks": draw_five_tasks_visual,
        "quote": draw_quote_visual,
    }
    visuals[scene.visual](draw, scene)


def render_scene(scene: Scene, index: int) -> Path:
    image = make_background(scene, index).convert("RGBA")
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw_header(draw, scene, index)

    headline_font = font(78 if index not in (4, 7) else 70, bold=True)
    headline_lines = scene.headline.splitlines()
    draw_multiline(draw, headline_lines, 70, 275, headline_font, (248, 252, 255), 20)

    body_font = font(38)
    body_lines = wrap_text(draw, scene.body, body_font, 865)
    draw_multiline(draw, body_lines, 73, 505, body_font, (196, 210, 226), 14)

    draw_scene_visual(draw, scene)

    draw.text((70, 1708), FOOTER_TEXT, font=font(30, bold=True), fill=(142, 157, 175))
    image = Image.alpha_composite(image, overlay).convert("RGB")
    out = FRAME_DIR / f"{index + 1:02d}_{scene.slug}.png"
    image.save(out, quality=95)
    return out


def normalize_for_timing(text: str) -> str:
    return "".join(char.lower() for char in text if char.isalnum())


async def generate_narration(text: str) -> list[WordTiming]:
    try:
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
        timings: list[WordTiming] = []
        with NARRATION_FILE.open("wb") as audio:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 10_000_000
                    end = (chunk["offset"] + chunk["duration"]) / 10_000_000
                    timings.append(WordTiming(text=chunk["text"], start=start, end=end))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "edge-tts failed to generate narration. "
            "Please check network access and install dependencies with: "
            "python -m pip install -r requirements.txt\n"
            f"Original error: {exc}"
        ) from exc
    if not timings:
        raise SystemExit("edge-tts generated audio but did not return WordBoundary timings.")
    return timings


async def synthesize_speech(text: str, output_path: Path) -> None:
    if TTS_BACKEND == "vcut":
        synthesize_speech_with_vcut(text, output_path)
        return
    if TTS_BACKEND != "edge":
        raise SystemExit(f"Unsupported tts_backend '{TTS_BACKEND}'. Use 'vcut' or 'edge'.")

    try:
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
        with output_path.open("wb") as audio:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio.write(chunk["data"])
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "edge-tts failed to generate narration. "
            "Please check network access and install dependencies with: "
            "python -m pip install -r requirements.txt\n"
            f"Original error: {exc}"
        ) from exc


def request_vcut_mbaiscvip_audio(text: str) -> str:
    api_key = env_value("MBAISCVIP_API_KEY")
    if not api_key:
        raise SystemExit(
            "vcut TTS requires MBAISCVIP_API_KEY. "
            "Set it in the environment or in .env at the project root."
        )

    base_url = env_value("MBAISCVIP_BASE_URL", "https://api.milorapart.top/apis/mbAIscvip")
    assert base_url is not None
    query = urllib.parse.urlencode(
        {
            "text": text,
            "format": VCUT_TTS_FORMAT,
            "speed": VCUT_TTS_SPEED,
            "key": api_key,
        }
    )
    url = f"{base_url}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "vcut/0.1",
        },
    )

    last_error: Exception | None = None
    for attempt in range(1, VCUT_TTS_MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=VCUT_TTS_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if int(payload.get("code", 0)) == 200 and payload.get("url"):
                return str(payload["url"])
            raise RuntimeError(payload.get("msg") or f"unexpected vcut TTS response: {payload}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < VCUT_TTS_MAX_ATTEMPTS:
                time.sleep(1.5 ** (attempt - 1))

    raise SystemExit(f"vcut mbaiscvip TTS request failed: {last_error}")


def download_audio(url: str, output_path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "vcut/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=VCUT_TTS_TIMEOUT_SECONDS) as response:
            output_path.write_bytes(response.read())
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Unable to download vcut TTS audio: {url}\nOriginal error: {exc}") from exc


def synthesize_speech_with_vcut(text: str, output_path: Path) -> None:
    if VCUT_TTS_MODE != "mbaiscvip":
        raise SystemExit(
            f"Unsupported vcut TTS mode '{VCUT_TTS_MODE}'. "
            "This workflow currently implements vcut mbaiscvip."
        )
    if len(text) > TTS_REQUEST_MAX_CHARS:
        raise SystemExit(f"vcut mbaiscvip text segment exceeds {TTS_REQUEST_MAX_CHARS} chars: {len(text)}")

    audio_url = request_vcut_mbaiscvip_audio(text)
    download_audio(audio_url, output_path)


def get_duration(path: Path) -> float:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"Unable to read duration: {path}")
    return float(result.stdout.strip())


def trim_chunk_leading_silence(source: Path, target: Path) -> None:
    result = run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-af",
            "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-45dB",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(target),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"Unable to trim audio chunk: {source}")


def write_audio_concat(chunk_paths: list[Path]) -> None:
    lines = [f"file '{path.resolve().as_posix()}'" for path in chunk_paths]
    AUDIO_CONCAT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def concat_audio_chunks(chunk_paths: list[Path]) -> None:
    write_audio_concat(chunk_paths)
    result = run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(AUDIO_CONCAT_FILE),
            "-ar",
            "24000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(NARRATION_FILE),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "Unable to concatenate narration chunks")


def validate_tts_chunking_config() -> None:
    if TTS_CHUNKING_MODE != "max_request_length":
        raise SystemExit(f"Unsupported tts_chunking.mode '{TTS_CHUNKING_MODE}'.")
    if TTS_CHUNKING_SCOPE != "scene":
        raise SystemExit(f"Unsupported tts_chunking.scope '{TTS_CHUNKING_SCOPE}'.")
    if TTS_CHUNKING_TIMING != "weighted_estimate":
        raise SystemExit(f"Unsupported tts_chunking.timing '{TTS_CHUNKING_TIMING}'.")
    if TTS_REQUEST_MAX_CHARS < 1:
        raise SystemExit("tts_chunking.max_chars must be a positive integer.")


def split_tts_groups(subtitle_lines: list[str], max_chars: int | None = None) -> list[TTSGroup]:
    max_chars = max_chars or TTS_REQUEST_MAX_CHARS
    groups: list[TTSGroup] = []
    current: list[str] = []
    current_len = 0

    for line in subtitle_lines:
        line_len = len(line)
        if line_len > max_chars:
            raise SystemExit(f"Subtitle line exceeds TTS request max length ({max_chars}): {line}")

        if current and current_len + line_len > max_chars:
            groups.append(TTSGroup(tuple(current)))
            current = []
            current_len = 0

        current.append(line)
        current_len += line_len

    if current:
        groups.append(TTSGroup(tuple(current)))

    return groups


def subtitle_timing_weight(text: str) -> float:
    light_punctuation = "，、："
    hard_punctuation = "。？！；"
    weight = 0.0

    for char in text:
        if char.isspace():
            continue
        weight += 1.0
        if char in light_punctuation:
            weight += 0.8
        elif char in hard_punctuation:
            weight += 1.8
        elif char == "…":
            weight += 0.8

    return max(weight, 1.0)


def allocate_weighted_durations(weights: list[float], total_duration: float) -> list[float]:
    if not weights:
        return []
    if len(weights) == 1:
        return [total_duration]

    total_weight = sum(weights) or float(len(weights))
    minimum_total = SUBTITLE_MIN_DURATION_SECONDS * len(weights)

    if total_duration <= minimum_total:
        return [total_duration * weight / total_weight for weight in weights]

    remainder = total_duration - minimum_total
    return [
        SUBTITLE_MIN_DURATION_SECONDS + remainder * weight / total_weight
        for weight in weights
    ]


def allocate_subtitle_times(lines: tuple[str, ...], start: float, end: float) -> list[SubtitleEntry]:
    duration = max(0.0, end - start)
    weights = [subtitle_timing_weight(line) for line in lines]
    durations = allocate_weighted_durations(weights, duration)

    entries: list[SubtitleEntry] = []
    cursor = start
    for index, (line, line_duration) in enumerate(zip(lines, durations)):
        entry_end = end if index == len(lines) - 1 else cursor + line_duration
        entries.append(SubtitleEntry(text=line, start=cursor, end=entry_end))
        cursor = entry_end
    return entries


async def generate_narration_from_subtitles() -> tuple[list[list[SubtitleEntry]], float]:
    validate_tts_chunking_config()

    subtitles_by_scene: list[list[SubtitleEntry]] = [[] for _ in SCENES]
    chunk_paths: list[Path] = []
    cursor = 0.0
    chunk_index = 0
    subtitle_line_count = 0
    tts_request_lengths: list[int] = []

    for scene_index, scene in enumerate(SCENES):
        print(f"Generating narration chunks for scene {scene_index + 1}/{len(SCENES)}...")
        subtitle_lines = split_subtitles(scene.narration)
        tts_groups = split_tts_groups(subtitle_lines)
        subtitle_line_count += len(subtitle_lines)

        for tts_group in tts_groups:
            chunk_index += 1
            raw_extension = VCUT_TTS_FORMAT if TTS_BACKEND == "vcut" else "mp3"
            raw_path = AUDIO_CHUNK_DIR / f"raw_{chunk_index:03d}.{raw_extension}"
            wav_path = AUDIO_CHUNK_DIR / f"{chunk_index:03d}.wav"
            request_text = tts_group.text
            tts_request_lengths.append(len(request_text))

            await synthesize_speech(request_text, raw_path)
            trim_chunk_leading_silence(raw_path, wav_path)
            duration = get_duration(wav_path)

            start = cursor
            end = cursor + duration
            subtitles_by_scene[scene_index].extend(allocate_subtitle_times(tts_group.subtitle_lines, start, end))
            chunk_paths.append(wav_path)
            cursor = end

    concat_audio_chunks(chunk_paths)
    audio_duration = get_duration(NARRATION_FILE)
    if subtitles_by_scene and subtitles_by_scene[-1]:
        last = subtitles_by_scene[-1][-1]
        subtitles_by_scene[-1][-1] = SubtitleEntry(text=last.text, start=last.start, end=audio_duration)

    if tts_request_lengths:
        average_request_length = sum(tts_request_lengths) / len(tts_request_lengths)
        savings = 1 - len(tts_request_lengths) / max(subtitle_line_count, 1)
        print(
            "TTS chunking: "
            f"{subtitle_line_count} subtitle lines -> {len(tts_request_lengths)} TTS calls; "
            f"avg {average_request_length:.1f} chars, max {max(tts_request_lengths)} chars; "
            f"estimated call reduction {savings:.1%}."
        )
    return subtitles_by_scene, audio_duration


def first_audible_time(path: Path) -> float | None:
    result = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-35dB:d=0.05",
            "-f",
            "null",
            "-",
        ]
    )
    if result.returncode != 0:
        print("Warning: unable to detect leading audio silence; using raw TTS timings.", file=sys.stderr)
        return None

    output = result.stderr
    if "silence_start: 0" not in output:
        return 0.0

    match = re.search(r"silence_end:\s*([0-9.]+)", output)
    return float(match.group(1)) if match else None


def calibrate_timings_to_audio(timings: list[WordTiming]) -> list[WordTiming]:
    first_audible = first_audible_time(NARRATION_FILE)
    if first_audible is None:
        return timings

    offset = first_audible - timings[0].start
    if abs(offset) < 0.025:
        return timings
    if abs(offset) > TIMING_CALIBRATION_LIMIT_SECONDS:
        print(
            f"Warning: detected a large TTS timing offset ({offset:+.3f}s); keeping raw timings.",
            file=sys.stderr,
        )
        return timings

    print(f"Calibrating subtitle timings by {offset:+.3f}s.")
    calibrated: list[WordTiming] = []
    for timing in timings:
        duration = max(0.01, timing.end - timing.start)
        start = max(0.0, timing.start + offset)
        calibrated.append(WordTiming(text=timing.text, start=start, end=start + duration))
    return calibrated


def expand_timings_to_char_units(timings: list[WordTiming]) -> list[WordTiming]:
    units: list[WordTiming] = []
    for timing in timings:
        normalized = normalize_for_timing(timing.text)
        if not normalized:
            continue

        duration = max(0.001, timing.end - timing.start)
        unit_duration = duration / len(normalized)
        for index, char in enumerate(normalized):
            start = timing.start + unit_duration * index
            units.append(WordTiming(text=char, start=start, end=start + unit_duration))

    if not units:
        raise SystemExit("TTS timing data could not be expanded for subtitle alignment.")
    return units


def fix_leading_punctuation(chunks: list[str]) -> list[str]:
    leading_punctuation = "，。？！；：、"
    fixed: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        leading = ""
        while chunk and chunk[0] in leading_punctuation:
            leading += chunk[0]
            chunk = chunk[1:].lstrip()
        if leading and fixed:
            fixed[-1] += leading
        elif leading:
            chunk = leading + chunk

        if chunk:
            fixed.append(chunk)
    return fixed


def split_subtitles(text: str, min_chars: int = SUBTITLE_MIN_CHARS, max_chars: int = SUBTITLE_MAX_CHARS) -> list[str]:
    punctuation = "，。？！；：、"
    hard_punctuation = "。？！；"
    chunks: list[str] = []
    current = ""
    for char in text:
        current += char
        should_split = (
            (char in hard_punctuation and len(current) >= 4)
            or (char in punctuation and len(current) >= min_chars)
            or len(current) >= max_chars
        )
        if should_split:
            chunks.append(current.strip())
            current = ""
    if current.strip():
        if chunks and len(current) < 8:
            chunks[-1] += current.strip()
        else:
            chunks.append(current.strip())
    return fix_leading_punctuation(chunks)


def ass_time(seconds: float) -> str:
    seconds = max(seconds, 0)
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    secs = int(seconds % 60)
    centiseconds = int(round((seconds - int(seconds)) * 100))
    if centiseconds == 100:
        secs += 1
        centiseconds = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def wrap_subtitle_display(text: str, max_chars: int = SUBTITLE_DISPLAY_MAX_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    punctuation = "，。？！；：、"
    midpoint = len(text) / 2
    candidates: list[int] = []

    for index, char in enumerate(text[:-1], start=1):
        if char in punctuation:
            candidates.append(index)

    valid_punctuation_splits = [
        index for index in candidates
        if len(text[:index]) <= max_chars and len(text[index:]) <= max_chars
    ]
    if valid_punctuation_splits:
        split_at = min(valid_punctuation_splits, key=lambda index: abs(index - midpoint))
    else:
        rough_split = math.ceil(midpoint)
        candidates = [
            index for index in range(max(1, rough_split - 3), min(len(text), rough_split + 4))
            if len(text[:index]) <= max_chars and len(text[index:]) <= max_chars
        ]
        awkward_starts = set("，。？！；：、的了着过吗呢吧啊呀么手址候")

        def split_score(index: int) -> float:
            score = abs(index - midpoint)
            if text[index:index + 1] in awkward_starts:
                score += 4
            return score

        split_at = min(candidates or [rough_split], key=split_score)

    first = text[:split_at].strip()
    second = text[split_at:].strip()
    while second and second[0] in punctuation:
        first += second[0]
        second = second[1:].strip()

    return [line for line in (first, second) if line]


def ass_format_text(text: str) -> str:
    return r"\N".join(ass_escape(line) for line in wrap_subtitle_display(text))


def split_timings_by_scene(timings: list[WordTiming]) -> list[list[WordTiming]]:
    scene_timings: list[list[WordTiming]] = []
    timing_index = 0

    for scene in SCENES:
        target_chars = len(normalize_for_timing(scene.narration))
        start_index = timing_index
        timing_index += target_chars

        scene_slice = timings[start_index:timing_index]
        if len(scene_slice) != target_chars:
            raise SystemExit(f"No TTS timing data found for scene: {scene.slug}")
        scene_timings.append(scene_slice)

    if timing_index < len(timings):
        scene_timings[-1].extend(timings[timing_index:])

    return scene_timings


def build_timeline(scene_timings: list[list[WordTiming]], audio_duration: float) -> list[tuple[float, float]]:
    timeline: list[tuple[float, float]] = []
    cursor = 0.0

    for index, words in enumerate(scene_timings):
        start = cursor
        if index < len(scene_timings) - 1:
            next_start = scene_timings[index + 1][0].start
            end = max(start + 1.0, next_start - 0.05)
        else:
            end = max(audio_duration, words[-1].end + 0.25)
        timeline.append((start, end))
        cursor = end

    return timeline


def build_timeline_from_subtitles(
    subtitles_by_scene: list[list[SubtitleEntry]],
    audio_duration: float,
) -> list[tuple[float, float]]:
    timeline: list[tuple[float, float]] = []

    for index, entries in enumerate(subtitles_by_scene):
        if not entries:
            raise SystemExit(f"No subtitles generated for scene: {SCENES[index].slug}")

        start = entries[0].start
        if index < len(subtitles_by_scene) - 1:
            next_entries = subtitles_by_scene[index + 1]
            if not next_entries:
                raise SystemExit(f"No subtitles generated for scene: {SCENES[index + 1].slug}")
            end = next_entries[0].start
        else:
            end = audio_duration

        timeline.append((start, max(start + 1.0, end)))

    return timeline


def subtitle_entries_for_scene(
    text: str,
    timings: list[WordTiming],
    scene_start: float,
    scene_end: float,
) -> list[tuple[float, float, str]]:
    chunks = split_subtitles(text)
    entries: list[dict[str, float | str]] = []
    timing_index = 0

    for chunk in chunks:
        target_chars = len(normalize_for_timing(chunk))
        if target_chars == 0:
            continue

        start_index = timing_index
        timing_index += target_chars

        chunk_timings = timings[start_index:timing_index]
        if len(chunk_timings) != target_chars:
            continue

        entries.append(
            {
                "start": max(scene_start, chunk_timings[0].start - SUBTITLE_LEAD_SECONDS),
                "end": chunk_timings[-1].end + SUBTITLE_HOLD_SECONDS,
                "text": chunk,
            }
        )

    subtitle_entries: list[tuple[float, float, str]] = []
    for index, entry in enumerate(entries):
        start = float(entry["start"])
        end = min(scene_end, float(entry["end"]))
        if index < len(entries) - 1:
            next_start = float(entries[index + 1]["start"])
            end = min(end, next_start - 0.03)

        if end <= start:
            end = min(scene_end, start + SUBTITLE_MIN_DURATION_SECONDS)
        subtitle_entries.append((start, end, str(entry["text"])))

    return subtitle_entries


def write_subtitles(subtitles_by_scene: list[list[SubtitleEntry]]) -> None:
    header = textwrap.dedent(
        f"""
        [Script Info]
        ScriptType: v4.00+
        PlayResX: {WIDTH}
        PlayResY: {HEIGHT}
        ScaledBorderAndShadow: yes

        [V4+ Styles]
        Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        Style: Default, Microsoft YaHei, {SUBTITLE_FONT_SIZE}, &H00FFFFFF, &H000000FF, &H99000000, &HCC000000, -1, 0, 0, 0, 100, 100, 0, 0, 3, 3, 0, 2, 80, 80, {SUBTITLE_MARGIN_V}, 1

        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        """
    ).strip()

    lines = [header]
    subtitle_text: list[str] = []
    for entries in subtitles_by_scene:
        for entry in entries:
            subtitle_text.append(entry.text)
            lines.append(
                "Dialogue: 0,"
                f"{ass_time(entry.start)},{ass_time(entry.end)},Default,,0,0,0,,{ass_format_text(entry.text)}"
            )

    expected = normalize_for_timing("".join(scene.narration for scene in SCENES))
    actual = normalize_for_timing("".join(subtitle_text))
    if actual != expected:
        raise SystemExit("Generated subtitles do not match narration text.")

    SUBTITLE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_concat(frame_paths: list[Path], timeline: list[tuple[float, float]]) -> None:
    lines: list[str] = []
    for frame, (start, end) in zip(frame_paths, timeline):
        duration = end - start
        lines.append(f"file '{frame.as_posix()}'")
        lines.append(f"duration {duration:.3f}")
    lines.append(f"file '{frame_paths[-1].as_posix()}'")
    CONCAT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def subtitle_filter_path(path: Path) -> str:
    value = path.resolve().as_posix()
    if len(value) > 1 and value[1] == ":":
        value = value[0] + r"\:" + value[2:]
    return value.replace("'", r"\'")


def render_video(timeline: list[tuple[float, float]]) -> None:
    total_duration = timeline[-1][1]
    subtitle_path = subtitle_filter_path(SUBTITLE_FILE)
    filters = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},"
        f"subtitles='{subtitle_path}'"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(CONCAT_FILE),
        "-i",
        str(NARRATION_FILE),
        "-vf",
        filters,
        "-t",
        f"{total_duration:.3f}",
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(OUTPUT_VIDEO),
    ]
    result = run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "ffmpeg failed")


def verify_output() -> None:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,codec_name",
            "-of",
            "csv=p=0",
            str(OUTPUT_VIDEO),
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "ffprobe video verification failed")
    video_info = result.stdout.strip()
    if "1080,1920" not in video_info:
        raise SystemExit(f"Unexpected video stream: {video_info}")

    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "csv=p=0",
            str(OUTPUT_VIDEO),
        ]
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit("Missing audio stream in output video")


async def main() -> None:
    args = parse_args()
    apply_cli_overrides(args)

    ensure_tools()
    ensure_dirs()

    print("Generating narration from subtitle chunks...")
    subtitles_by_scene, audio_duration = await generate_narration_from_subtitles()

    print("Rendering scene cards...")
    frame_paths = [render_scene(scene, index) for index, scene in enumerate(SCENES)]

    timeline = build_timeline_from_subtitles(subtitles_by_scene, audio_duration)
    write_subtitles(subtitles_by_scene)
    write_concat(frame_paths, timeline)

    print("Compositing video with ffmpeg...")
    render_video(timeline)
    verify_output()

    print(f"Done: {OUTPUT_VIDEO}")
    print(f"Duration: {get_duration(OUTPUT_VIDEO):.1f}s")


if __name__ == "__main__":
    if os.name != "nt":
        print("Warning: this script was designed around Windows Microsoft YaHei fonts.", file=sys.stderr)
    asyncio.run(main())
