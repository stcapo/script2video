# script2video

JSON-driven vertical video generator for Chinese narrated short videos.

The workflow turns scene JSON into:

- static 1080x1920 scene cards rendered with Pillow
- vcut mbaiscvip TTS audio chunks, one per subtitle line
- synchronized ASS subtitles burned into the final video
- a 30fps MP4 assembled with ffmpeg

## Setup

```powershell
python -m pip install -r requirements.txt
```

Install `ffmpeg` and `ffprobe`, then create `.env` from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Fill in `MBAISCVIP_API_KEY`.

## Generate A Video

Edit or create a JSON file that follows:

```text
workflow/scene_input.schema.json
```

Example:

```powershell
python .\make_video.py --input .\workflow\example.input.json
```

Override output path:

```powershell
python .\make_video.py --input .\workflow\example.input.json --output .\dist\my_video.mp4
```

## Input Contract

The reusable AI-facing workflow contract is:

```text
workflow/video_generation.workflow.json
```

The visual frame tuning guide is:

```text
workflow/visual_frame_tuning.guide.json
```

## Important Workflow Details

- Default TTS backend is `vcut` using mbaiscvip semantics.
- Each subtitle line maps to exactly one TTS audio chunk.
- Subtitle timing comes from real chunk durations, not word-boundary guessing.
- Static scene cards must be expanded to `fps=30` before burning subtitles.
- The critical ffmpeg filter order is:

```text
scale -> pad -> fps=30 -> subtitles
```

## What The "PPT" Is

This project does not generate `.pptx`.

The "PPT pages" are static PNG scene cards in `build/frames/`, rendered by `make_video.py` with Pillow. They are later assembled into a video by ffmpeg.

Tune page content in JSON first:

- `scenes[].headline`
- `scenes[].body`
- `scenes[].visual`
- `scenes[].visual_texts`
- `scenes[].accent`
- `video.footer`

Tune layout in `make_video.py` only when JSON is not enough.

