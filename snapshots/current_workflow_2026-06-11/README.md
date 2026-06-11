# Current Workflow Snapshot - 2026-06-11

This folder freezes the working state after subtitle sync and subtitle refresh were fixed.

## Included Files

- `make_video.py`: current reusable video generation script
- `requirements.txt`: Python dependencies
- `subtitles.ass`: generated subtitle file from the verified run
- `frames.txt`: generated scene frame concat list from the verified run
- `subtitle_check_strip.png`: visual proof that subtitles change within the same static scene
- `workflow/*.json`: machine-readable workflow contract, input schema, example input, and current state snapshot

## Restore

Copy `make_video.py` and `requirements.txt` back to the project root if needed.

## Key Behavior

- Narration is generated per subtitle line.
- Subtitle timing comes from the real duration of each audio chunk.
- Static scene images are converted to `fps=30` before subtitles are burned in.

The critical render filter order is:

```text
scale -> pad -> fps=30 -> subtitles
```

## Main Documentation

See:

- `workflow/video_generation.workflow.json`
- `workflow/scene_input.schema.json`
- `workflow/example.input.json`
- `workflow/current_state.snapshot.json`
- `docs/WORKFLOW_SNAPSHOT_2026-06-11.md`
- `docs/SCENE_INPUT_TEMPLATE.md`
