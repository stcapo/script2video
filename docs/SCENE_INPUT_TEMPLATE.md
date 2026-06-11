# Scene Input Template

Use this template when creating a new video with the current workflow.

## Recommended Input Shape

Prepare 6 to 10 scenes. Each scene should include:

- Page title
- Big headline
- Supporting body copy
- Spoken narration
- Visual type
- Accent color

## Copywriting Rules

- One scene should express one idea.
- `headline` should be short enough for 2 lines.
- `body` should be one compact sentence.
- `narration` can be longer, but should stay focused.
- Avoid very long subtitle lines; the script will split narration automatically, but cleaner punctuation helps.
- Use Chinese punctuation: `，。？！；：、`

## Python Scene Template

```python
Scene(
    slug="01_topic",
    label="01 / 08",
    title="页面小标题",
    headline="第一行标题\n第二行标题",
    body="屏幕上显示的一句补充说明。",
    narration=(
        "这里写完整口播第一句。"
        "这里写完整口播第二句，尽量用清晰标点。"
        "这里写完整口播第三句。"
    ),
    accent=(57, 220, 198),
    visual="question",
),
```

## Visual Selection Guide

- `question`: 开场问题、反常识提问
- `calendar`: 记录、周期、实验
- `three_nodes`: 三类结果、三点结论
- `pipeline`: 流程、瓶颈、系统
- `checklist`: 判断标准、步骤
- `gates`: 是/否门槛、筛选条件
- `five_tasks`: 当天任务、行动清单
- `quote`: 结尾金句、核心观点

## Reuse Prompt

When preparing a new script, use this structure:

```text
主题：
目标观众：
核心观点：
视频长度：约 2-3 分钟
场景数量：8
风格：克制、清晰、有观点，不做营销感

请输出 8 个 Scene 所需字段：
slug, label, title, headline, body, narration, accent, visual

要求：
1. headline 每个场景最多两行。
2. body 一句话。
3. narration 适合中文口播，标点清楚。
4. 每个场景只讲一个点。
5. 结尾要有一句能收住的观点。
```

## Generation Command

```powershell
python .\make_video.py
```

Output:

```text
dist\ai_workflow_nodes.mp4
```

