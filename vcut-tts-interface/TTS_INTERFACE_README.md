# vcut TTS 工作流接口文档

## 📋 概述

本目录包含 vcut 项目中 **TTS (文本转语音)** 工作流的完整接口定义。可以直接用于接入其他工具或系统，无需深入了解 vcut 的内部实现。

## 📁 文件清单

### 1. **TTS_INTERFACE.json** (核心规范)
完整的 TTS 工作流接口规范，JSON 格式，包含：
- 支持的 TTS 模式（曼波 AI、Fish Audio、本地音频）
- 环境变量配置
- API 请求/响应格式
- 文本分段策略
- 输出文件结构
- 错误处理

**适用场景：** 
- API 文档参考
- 接口规范文档
- 自动化工具集成
- 系统间数据交换

### 2. **TTS_INTEGRATION_GUIDE.md** (集成指南)
详细的集成步骤和示例，包含：
- 快速开始指南
- 环境配置说明
- job.json 配置示例
- 输出文件格式详解
- 常见错误及解决方案
- 与其他工具的集成方式

**适用场景：**
- 新用户入门
- 集成到其他工作流
- 调试和故障排查
- 扩展功能

### 3. **TTS_API.py** (Python 接口)
Python 数据类和接口定义，包含：
- `VoiceConfig`: 语音配置数据类
- `VoiceSegment`: 分段元数据
- `VoiceoverResult`: TTS 处理结果
- `TTSRequest`: TTS 请求
- `TTSResponse`: TTS 响应
- `TTSAPIInterface`: 接口基类
- `EnvConfig`: 环境变量配置
- 配置示例函数

**适用场景：**
- Python 项目集成
- 类型提示和验证
- 数据序列化/反序列化
- IDE 自动补全

### 4. **TTS_INTERFACE_README.md** (本文件)
快速导航和使用说明

## 🚀 快速开始

### 方案 A：直接使用 vcut CLI

```bash
# 1. 配置环境变量
echo 'MBAISCVIP_API_KEY=your_key' > .env

# 2. 创建 job.json
cat > job.json << 'EOF'
{
  "script_file": "inputs/script.txt",
  "title": "My Video",
  "voice": {
    "mode": "mbaiscvip",
    "format": "mp3",
    "speed": "0"
  }
}
EOF

# 3. 运行 TTS 工作流
python -m vcut render --job job.json
```

**输出：**
```
audio/
  voiceover.wav              # 最终音轨
  voice_segments.json        # 分段元数据
  raw_segments/             # 原始音频
  wav_segments/             # 转换后的音频
```

### 方案 B：在 Python 项目中集成

```python
import os
from pathlib import Path
from vcut.audio import prepare_voiceover
from vcut.job import Job

# 配置环境
os.environ['MBAISCVIP_API_KEY'] = 'your_key'

# 创建任务配置
job = Job(
    path="job.json",
    base_dir=Path("projects/demo"),
    script_zh="这是示例脚本",
    title="示例视频",
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

# 生成语音
result = prepare_voiceover(job, Path("output"))

# 使用结果
print(f"Voiceover: {result.path}")
for segment in result.segments:
    print(f"  Segment {segment.index}: {segment.text} ({segment.duration}s)")
```

### 方案 C：使用数据类进行类型检查

```python
from TTS_API import VoiceConfig, AudioFormat, TTSMode, JobVoiceConfig

# 创建配置
config = VoiceConfig(
    mode=TTSMode.MBAISCVIP,
    format=AudioFormat.MP3,
    speed="0"
)

# 转换为 job.json 格式
job_config = config.to_dict()
print(job_config)
# {'mode': 'mbaiscvip', 'format': 'mp3', 'speed': '0'}
```

## 📚 详细使用

### TTS 模式对比

| 功能 | 曼波 AI | Fish Audio | 本地音频 |
|------|---------|-----------|--------|
| **模式** | `mbaiscvip` | `fish_audio` | `manual_audio` |
| **优势** | 自动生成语音 | 高质量语音 | 无网络依赖 |
| **需要 API** | ✓ | ✓ | ✗ |
| **支持分段** | ✓ | ✗ | ✗ |
| **最大文本长度** | 200 字/段 | 无限 | N/A |
| **推荐** | 自动化流程 | 专业配音 | 快速测试 |

### 环境变量配置

创建 `.env` 文件（在项目根目录）：

```env
# 曼波 AI 配置（必需）
MBAISCVIP_API_KEY=your_api_key_here
MBAISCVIP_BASE_URL=https://api.milorapart.top/apis/mbAIscvip

# Fish Audio 配置（可选）
FISH_AUDIO_API_KEY=your_api_key_here
FISH_AUDIO_BASE_URL=https://api.fish.audio

# Pixabay 配置（图片检索）
PIXABAY_API_KEY=your_api_key_here

# Jamendo 配置（BGM 检索）
JAMENDO_CLIENT_ID=your_client_id_here
JAMENDO_BASE_URL=https://api.jamendo.com/v3.0
```

### job.json 完整示例

```json
{
  "script_file": "inputs/script.txt",
  "title": "AI 生产力工具对比",
  "voice": {
    "mode": "mbaiscvip",
    "format": "mp3",
    "speed": "0"
  },
  "images": [
    "inputs/images/claude_logo.png",
    "inputs/images/workflow.png"
  ],
  "target": {
    "aspect_ratio": "9:16",
    "width": 1080,
    "height": 1920,
    "fps": 30
  },
  "pixabay": {
    "enabled": true
  },
  "bgm": {
    "uri": "inputs/bgm/background_music.mp3",
    "volume": 0.12,
    "source": "local"
  }
}
```

## 🔗 集成到其他工具

### 作为 HTTP API

需要在 vcut 基础上开发包装层：

```python
from flask import Flask, request
from pathlib import Path
import json

app = Flask(__name__)

@app.route('/api/tts', methods=['POST'])
def synthesize_tts():
    data = request.json
    text = data.get('text')
    mode = data.get('mode', 'mbaiscvip')
    
    # 调用 vcut
    from vcut.audio import prepare_voiceover
    result = prepare_voiceover(job, Path("output"))
    
    return {
        'success': True,
        'audio_url': str(result.path),
        'segments': [s.to_dict() for s in result.segments]
    }

if __name__ == '__main__':
    app.run(port=5000)
```

### 作为 CI/CD Pipeline

```yaml
# GitHub Actions 示例
- name: Generate TTS
  run: |
    python -m vcut render \
      --job projects/${{ env.VIDEO_ID }}/job.json \
      --out projects/${{ env.VIDEO_ID }}/outputs/latest
      
- name: Upload Audio Artifacts
  uses: actions/upload-artifact@v2
  with:
    name: audio-output
    path: projects/${{ env.VIDEO_ID }}/outputs/latest/audio/voiceover.wav
```

## 📖 API 详细规范

### 曼波 AI TTS API

**端点：** `GET {MBAISCVIP_BASE_URL}`

**参数：**
```
text=<中文文本，最多200字>&format=<mp3|wav>&speed=<语速>&key=<API_KEY>
```

**请求示例：**
```
GET https://api.milorapart.top/apis/mbAIscvip?text=Hello+World&format=mp3&speed=0&key=xxxxx
Authorization: Bearer xxxxx
User-Agent: vcut/0.1
```

**响应示例：**
```json
{
  "code": 200,
  "url": "https://cdn.example.com/audio/xxxxx.mp3",
  "msg": "success"
}
```

**重试策略：**
- 最多 3 次
- 指数退避（1.5 倍乘数）
- 单次超时 120 秒

### voice_segments.json 格式

```json
[
  {
    "index": 1,
    "text": "分段的原始文本",
    "raw_path": "audio/raw_segments/segment_001.mp3",
    "wav_path": "audio/wav_segments/segment_001.wav",
    "duration": 2.345,
    "source_url": "https://cdn.example.com/audio/xxxxx.mp3"
  }
]
```

## 🛠️ 常见问题

### Q1: 如何处理超长文本？

**A:** 系统会自动按 200 字分段。如果需要自定义分段长度：

```python
from vcut.audio import _split_text_for_tts

segments = _split_text_for_tts("长文本...", max_chars=150)
```

### Q2: 支持哪些音频格式？

**A:** 
- **TTS 输出：** mp3, wav
- **输入（manual_audio）：** mp3, wav, m4a, aac, flac, ogg, opus

### Q3: 如何重新生成某个分段？

**A:** 删除对应的 `raw_segments/` 和 `wav_segments/` 中的文件，重新运行 render 命令。

### Q4: 音频采样率是多少？

**A:** 统一转换为 **48kHz, 16-bit PCM, 2-channel**

### Q5: 支持并发 TTS 请求吗？

**A:** 当前实现是逐段顺序处理，每段请求之间有 1-3 秒的重试退避间隔。

## 📞 联系与支持

- **文档问题：** 查看 `WORKFLOW.md` 的完整流程说明
- **实现细节：** 参考 `vcut/audio.py` 的源代码
- **API 问题：** 检查 `.env` 配置和网络连接
- **集成帮助：** 参考 `TTS_INTEGRATION_GUIDE.md` 的集成示例

## 📄 许可证

与 vcut 项目同级别许可证

---

**最后更新：** 2026-06-11
