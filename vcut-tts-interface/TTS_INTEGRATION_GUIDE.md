# vcut TTS 工作流接口集成指南

## 概述

本文档说明如何将 vcut 的 TTS (文本转语音) 工作流集成到其他工具或系统中。所有接口以 `TTS_INTERFACE.json` 中的规范为准。

## 快速开始

### 1. 环境配置

在项目根目录创建或编辑 `.env` 文件：

```env
MBAISCVIP_API_KEY=your_api_key_here
MBAISCVIP_BASE_URL=https://api.milorapart.top/apis/mbAIscvip
```

### 2. 准备 job.json

创建任务配置文件，指定 TTS 模式和脚本：

#### 方式 A：使用曼波 AI (推荐)

```json
{
  "script_file": "inputs/script.txt",
  "title": "我的视频",
  "voice": {
    "mode": "mbaiscvip",
    "format": "mp3",
    "speed": "0"
  }
}
```

#### 方式 B：使用本地音频

```json
{
  "script_file": "inputs/script.txt",
  "title": "我的视频",
  "voice": {
    "mode": "manual_audio",
    "audio_uri": "inputs/my_voiceover.mp3"
  }
}
```

### 3. 运行工作流

```bash
python -m vcut render --job projects/my_video/job.json
```

## 接口规范详解

### TTS 模式

#### mbaiscvip (曼波 AI)

**支持的参数：**
- `format`: `mp3` 或 `wav`
- `speed`: 语速参数，`"0"` 为正常速度

**工作流：**
1. 加载 `.env` 中的 `MBAISCVIP_API_KEY` 和 `MBAISCVIP_BASE_URL`
2. 将脚本按中文标点切分，每段不超过 200 字
3. 对每段调用 API：
   ```
   GET {base_url}?text={segment}&format={format}&speed={speed}&key={api_key}
   ```
4. 获取返回的音频 URL 并下载
5. 转换为 WAV 格式（48kHz, 16-bit PCM, 2ch）
6. 拼接所有段成完整音轨

**API 返回格式：**
```json
{
  "code": 200,
  "url": "https://cdn.example.com/audio/xxxxx.mp3",
  "msg": "success"
}
```

**重试策略：**
- 最多重试 3 次
- 指数退避：1.5 倍乘数
- 单次超时：120 秒

#### manual_audio (本地音频)

**参数：**
- `audio_uri`: 相对于 `inputs/` 的音频文件路径

**支持格式：** mp3, wav, m4a, aac, flac, ogg, opus

**验证：**
- 文件必须存在
- 必须包含有效的音频流
- 时长至少 1 秒

#### fish_audio (预留)

**参数：**
- `reference_id`: 语音参考 ID
- `format`: 输出格式

目前为预留入口，不在主流程中使用。

### 环境变量

| 变量名 | 必需 | 用途 | 默认值 |
|--------|------|------|--------|
| `MBAISCVIP_API_KEY` | ✓ (mbaiscvip) | 曼波 API 认证 | - |
| `MBAISCVIP_BASE_URL` | ✓ (mbaiscvip) | 曼波 API 地址 | `https://api.milorapart.top/apis/mbAIscvip` |
| `FISH_AUDIO_API_KEY` | ✓ (fish_audio) | Fish Audio 认证 | - |
| `FISH_AUDIO_BASE_URL` | ✓ (fish_audio) | Fish Audio 地址 | `https://api.fish.audio` |

## 输出结构

运行工作流后，在 `projects/{video_id}/outputs/latest/` 下生成：

```
audio/
  voiceover.wav                    # 最终完整口播音轨
  voice_segments.json              # 分段元数据
  raw_segments/
    segment_001.mp3
    segment_002.mp3
    ...
  wav_segments/
    segment_001.wav
    segment_002.wav
    ...
```

### voice_segments.json 格式

```json
[
  {
    "index": 1,
    "text": "Claude Code 是一个强大的代码编辑工具。",
    "raw_path": "audio/raw_segments/segment_001.mp3",
    "wav_path": "audio/wav_segments/segment_001.wav",
    "duration": 2.345,
    "source_url": "https://cdn.example.com/audio/xxxxx.mp3"
  },
  {
    "index": 2,
    "text": "它支持多种编程语言。",
    "raw_path": "audio/raw_segments/segment_002.mp3",
    "wav_path": "audio/wav_segments/segment_002.wav",
    "duration": 1.678,
    "source_url": "https://cdn.example.com/audio/yyyyy.mp3"
  }
]
```

## 集成点

### 上游依赖

- **输入脚本：** `inputs/script.txt` (中文文案)
- **配置文件：** `job.json` (voice 部分)
- **环境变量：** `.env` (API 密钥)

### 下游消费

- **Storyboard 生成：** 使用分段的时长和文本作为 shot 边界
- **FFmpeg 渲染：** 混入 `voiceover.wav` 作为音轨
- **质量审查：** 使用 `voice_segments.json` 和原始音频用于语音质量检查

## 错误处理

### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|--------|
| `ConfigError: voice.mode=mbaiscvip requires MBAISCVIP_API_KEY` | 未设置 API 密钥 | 在 `.env` 中设置 `MBAISCVIP_API_KEY` |
| `ConfigError: manual_audio requires voice.audio_uri` | 模式设置为 manual_audio 但未指定文件 | 在 job.json 中指定 `audio_uri` |
| `MediaError: mbAIscvip TTS request failed` | API 调用失败 | 检查网络连接、API 密钥、文本内容是否合法 |
| `MediaError: manual voiceover has no audio stream` | 本地音频文件无效 | 确保文件是有效的音频格式 |

### 失败恢复

当 TTS 工作流失败时：
- 保留 `draft.mp4` 和所有中间产物
- 根据错误原因修复配置或重新生成对应分段
- 无需从零开始，支持局部重做

## 与其他工具的集成

### 1. 作为 Webhook 调用

```bash
curl -X POST http://your-server/tts \
  -H "Content-Type: application/json" \
  -d '{
    "script": "这是一个示例脚本",
    "voice_mode": "mbaiscvip",
    "format": "mp3"
  }'
```

（需要在 vcut 基础上开发 HTTP 包装层）

### 2. 作为 Python 库调用

```python
from vcut.audio import prepare_voiceover
from vcut.job import Job

job = Job(
    path="job.json",
    base_dir="projects/demo",
    script_zh="这是一个示例脚本",
    title="示例",
    voice=type('VoiceConfig', (), {
        'mode': 'mbaiscvip',
        'format': 'mp3',
        'speed': '0'
    })(),
    images=[],
    target=None,
    pixabay=None,
    bgm=None
)

result = prepare_voiceover(job, Path("output"))
print(result.path)  # voiceover.wav 的路径
for segment in result.segments:
    print(f"{segment.index}: {segment.text} ({segment.duration}s)")
```

### 3. 作为 API 端点

在其他系统中实现接口：

**请求：**
```json
{
  "text": "要转换的文本（最大200字符）",
  "format": "mp3",
  "speed": "0",
  "mode": "mbaiscvip"
}
```

**响应：**
```json
{
  "status": "success",
  "duration": 2.345,
  "audio_url": "https://cdn.example.com/audio/xxxxx.mp3",
  "raw_path": "path/to/segment.mp3",
  "wav_path": "path/to/segment.wav"
}
```

## 性能考虑

- **文本切分：** 每段 ≤ 200 字，按中文标点优先分割
- **API 延迟：** 单次请求 ~120 秒超时，支持 3 次自动重试
- **下载：** 并非并发，逐段处理
- **转换：** FFmpeg WAV 转换约 1-2 秒/段

## 扩展点

### 自定义分段策略

修改 `audio.py` 中的 `_split_text_for_tts()` 函数以改变文本切分逻辑。

### 支持新的 TTS 提供商

在 `audio.py` 中添加新的 `_prepare_xxx()` 函数，遵循以下接口：

```python
def _prepare_xxx(job: Job, out_dir: Path) -> VoiceoverResult:
    # 返回 VoiceoverResult(path=voiceover_path, segments=voice_segments)
    pass
```

### 自定义音频处理

修改 `_convert_to_wav()` 以调整采样率、通道数或编码格式。

## 相关文件

- **主工作流文档：** `WORKFLOW.md`
- **接口规范：** `TTS_INTERFACE.json`
- **实现代码：** `vcut/audio.py`
- **配置加载：** `vcut/env.py`
- **任务配置：** `vcut/job.py`

## 支持

- 问题报告：请检查 `.env` 配置和 API 密钥
- 特定错误信息参见 `vcut/errors.py`
- 工作流日志在 CLI 执行时打印到标准输出
