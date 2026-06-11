# Script To Video Workflow Snapshot

Date: 2026-06-11

This snapshot records the currently working workflow after fixing subtitle refresh and alignment issues.

## Snapshot Files

- `snapshots/current_workflow_2026-06-11/make_video.py`
- `snapshots/current_workflow_2026-06-11/requirements.txt`
- `snapshots/current_workflow_2026-06-11/subtitles.ass`
- `snapshots/current_workflow_2026-06-11/frames.txt`
- `snapshots/current_workflow_2026-06-11/subtitle_check_strip.png`

Current generated video:

- `dist/ai_workflow_nodes.mp4`

## Output Spec

- Format: vertical short video
- Resolution: 1080 x 1920
- FPS: 30
- Voice: `zh-CN-XiaoxiaoNeural`
- Speech rate: `+8%`
- Subtitle format: ASS burned into video
- Final render path: `dist/ai_workflow_nodes.mp4`

Current verified output:

- Video duration: about `175.967s`
- Audio duration: about `175.957s`
- Frame rate: `30/1`
- Subtitle refresh verified on the same static page with extracted frames at 1s, 4s, and 7s.

## Core Workflow

1. Define scenes in `SCENES`.
2. Each scene contains visual copy and narration copy.
3. Split each scene narration into subtitle chunks with `split_subtitles`.
4. Generate one TTS audio chunk per subtitle line.
5. Trim leading silence from each chunk.
6. Concatenate all audio chunks into `build/narration.wav`.
7. Write ASS subtitles using the exact start/end time of each audio chunk.
8. Render one static image per scene.
9. Build a scene timeline from subtitle/audio chunk times.
10. Concatenate scene frames into a video stream.
11. Important: convert static frames to `fps=30` before applying subtitles.
12. Burn subtitles into the 30fps frame stream.
13. Mux with `build/narration.wav`.

## Important Fixes Preserved In This Snapshot

### Subtitle Timing

The stable path is now chunk-based:

- One subtitle line equals one TTS request.
- One subtitle line equals one generated audio chunk.
- Subtitle start/end equals the real duration of that audio chunk in the concatenated narration.

This avoids relying on Chinese `WordBoundary` timestamps from Edge TTS, which can be too coarse.

### Subtitle Refresh

The subtitle filter must run after static images are expanded into frames:

```text
scale -> pad -> fps=30 -> subtitles
```

If `subtitles` runs before `fps=30`, the subtitle is rendered only on the first frame of each static image. That causes the observed bug where subtitles change only when the page changes.

## Reusing The Workflow

To make a new video with the same quality:

1. Edit only the `SCENES` list in `make_video.py`.
2. Keep `slug` unique and filesystem-safe.
3. Keep `label` in the same style, such as `01 / 08`.
4. Keep `headline` short, ideally 2 lines.
5. Keep `body` to one compact sentence.
6. Put the full spoken script in `narration`.
7. Pick an existing `visual` value unless adding a new renderer.
8. Run:

```powershell
python .\make_video.py
```

## Scene Fields

Each scene has:

- `slug`: filename-safe scene id.
- `label`: visible progress label.
- `title`: small scene title.
- `headline`: large on-screen headline.
- `body`: supporting on-screen copy.
- `narration`: full spoken copy for this scene.
- `accent`: RGB tuple for scene color.
- `visual`: visual renderer key.

Available visual keys in this snapshot:

- `question`
- `calendar`
- `three_nodes`
- `pipeline`
- `checklist`
- `gates`
- `five_tasks`
- `quote`

## Quality Checklist

After generating a new video, check:

```powershell
python -m py_compile .\make_video.py
ffprobe -v error -show_entries stream=index,codec_type,duration,avg_frame_rate -of json .\dist\ai_workflow_nodes.mp4
```

For subtitle refresh, extract same-page frames:

```powershell
ffmpeg -y -hide_banner -loglevel error -ss 00:00:01.000 -i .\dist\ai_workflow_nodes.mp4 -frames:v 1 .\build\check_001s.png
ffmpeg -y -hide_banner -loglevel error -ss 00:00:04.000 -i .\dist\ai_workflow_nodes.mp4 -frames:v 1 .\build\check_004s.png
ffmpeg -y -hide_banner -loglevel error -ss 00:00:07.000 -i .\dist\ai_workflow_nodes.mp4 -frames:v 1 .\build\check_007s.png
```

Expected result:

- Same page should show different subtitles at different timestamps.
- No subtitle should freeze until the next scene.
- Subtitle text should match the spoken chunk.

## Current Design Style

- Dark vertical editorial cards.
- Strong two-line headline.
- One compact body paragraph.
- Accent color per scene.
- Minimal interface-like graphics.
- Subtitle near the lower area with readable white text, dark translucent backing, and 1080x1920 safe margins.

## Known Tradeoff

Because each subtitle line is synthesized as a separate TTS chunk, the final speech can contain slightly more natural pauses between subtitle lines. This is intentional for reliable subtitle sync.

