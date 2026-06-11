"""
TTS (Text-to-Speech) API Interface for vcut

This module defines the interface for integrating TTS functionality with other tools.
It provides type hints, configuration schemas, and usage examples.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class TTSMode(Enum):
    """Supported TTS modes"""
    MBAISCVIP = "mbaiscvip"
    FISH_AUDIO = "fish_audio"
    MANUAL_AUDIO = "manual_audio"


class AudioFormat(Enum):
    """Supported audio formats"""
    MP3 = "mp3"
    WAV = "wav"
    M4A = "m4a"
    AAC = "aac"
    FLAC = "flac"
    OGG = "ogg"
    OPUS = "opus"


@dataclass
class VoiceConfig:
    """Voice configuration for TTS"""
    mode: TTSMode
    format: AudioFormat | str
    speed: str = "0"
    reference_id: Optional[str] = None  # For fish_audio
    audio_uri: Optional[str] = None  # For manual_audio

    def to_dict(self) -> dict:
        """Convert to dictionary for job.json"""
        result = {
            "mode": self.mode.value,
            "format": self.format if isinstance(self.format, str) else self.format.value,
            "speed": self.speed,
        }
        if self.reference_id:
            result["reference_id"] = self.reference_id
        if self.audio_uri:
            result["audio_uri"] = self.audio_uri
        return result


@dataclass
class VoiceSegment:
    """Metadata for a single TTS segment"""
    index: int
    text: str
    raw_path: str
    wav_path: str
    duration: float
    source_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for voice_segments.json"""
        return {
            "index": self.index,
            "text": self.text,
            "raw_path": self.raw_path,
            "wav_path": self.wav_path,
            "duration": self.duration,
            "source_url": self.source_url,
        }


@dataclass
class VoiceoverResult:
    """Result of TTS processing"""
    path: Path
    segments: list[VoiceSegment]

    def voiceover_duration(self) -> float:
        """Total duration of voiceover in seconds"""
        return sum(s.duration for s in self.segments)

    def segment_count(self) -> int:
        """Number of TTS segments"""
        return len(self.segments)


@dataclass
class TTSRequest:
    """Request for TTS processing"""
    text: str
    mode: TTSMode
    format: AudioFormat | str
    speed: str = "0"
    max_segment_length: int = 200

    def validate(self) -> bool:
        """Validate request parameters"""
        if not self.text or not self.text.strip():
            raise ValueError("Text cannot be empty")
        if self.mode == TTSMode.MBAISCVIP:
            if len(self.text) > self.max_segment_length:
                raise ValueError(
                    f"Text exceeds max length {self.max_segment_length}: {len(self.text)}"
                )
        return True


@dataclass
class TTSResponse:
    """Response from TTS API"""
    success: bool
    audio_url: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[float] = None

    def is_successful(self) -> bool:
        """Check if TTS processing was successful"""
        return self.success and self.audio_url is not None


class TTSAPIInterface:
    """
    Interface for TTS API integration.

    This class defines the contract for integrating different TTS providers
    with the vcut video generation pipeline.
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """
        Initialize TTS API interface.

        Args:
            api_key: API key for the TTS service
            base_url: Optional base URL override for the API endpoint
        """
        self.api_key = api_key
        self.base_url = base_url

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        """
        Synthesize speech from text.

        Args:
            request: TTS request with text and configuration

        Returns:
            TTSResponse with audio URL or error message

        Raises:
            ConfigError: If configuration is invalid
            MediaError: If synthesis fails
        """
        raise NotImplementedError("Subclasses must implement synthesize()")

    def validate_config(self) -> bool:
        """Validate API configuration"""
        raise NotImplementedError("Subclasses must implement validate_config()")


class MBAISCVIPInterface(TTSAPIInterface):
    """Interface for 曼波 AI SVoice VIP TTS API"""

    DEFAULT_BASE_URL = "https://api.milorapart.top/apis/mbAIscvip"

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL)

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        """
        Synthesize speech using 曼波 AI API.

        Request format:
            GET {base_url}?text={text}&format={format}&speed={speed}&key={api_key}

        Response format:
            {
                "code": 200,
                "url": "https://cdn.example.com/audio/xxxxx.mp3",
                "msg": "success"
            }
        """
        # Implementation in vcut.audio._request_mbaiscvip_audio()
        raise NotImplementedError("Use vcut.audio.prepare_voiceover() for actual implementation")

    def validate_config(self) -> bool:
        """Validate that API key is set"""
        return bool(self.api_key)


class FishAudioInterface(TTSAPIInterface):
    """Interface for Fish Audio TTS API (reserved)"""

    DEFAULT_BASE_URL = "https://api.fish.audio"

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url or self.DEFAULT_BASE_URL)

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        """
        Synthesize speech using Fish Audio API.

        Request format:
            POST {base_url}/v1/tts
            {
                "text": "...",
                "reference_id": "...",
                "format": "mp3|wav"
            }
        """
        raise NotImplementedError("Fish Audio integration in progress")

    def validate_config(self) -> bool:
        """Validate that API key is set"""
        return bool(self.api_key)


@dataclass
class JobVoiceConfig:
    """Voice configuration section for job.json"""
    mode: str  # "mbaiscvip" | "fish_audio" | "manual_audio"
    format: Optional[str] = None  # "mp3" | "wav"
    speed: Optional[str] = None  # "0" for normal speed
    reference_id: Optional[str] = None  # For fish_audio
    audio_uri: Optional[str] = None  # For manual_audio

    @staticmethod
    def from_dict(data: dict) -> JobVoiceConfig:
        """Create from dictionary (parsed from job.json)"""
        return JobVoiceConfig(
            mode=data.get("mode"),
            format=data.get("format"),
            speed=data.get("speed", "0"),
            reference_id=data.get("reference_id"),
            audio_uri=data.get("audio_uri"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for job.json"""
        result = {"mode": self.mode}
        if self.format:
            result["format"] = self.format
        if self.speed:
            result["speed"] = self.speed
        if self.reference_id:
            result["reference_id"] = self.reference_id
        if self.audio_uri:
            result["audio_uri"] = self.audio_uri
        return result


@dataclass
class EnvConfig:
    """Environment variables required for TTS"""

    MBAISCVIP_API_KEY: Optional[str] = None
    MBAISCVIP_BASE_URL: str = "https://api.milorapart.top/apis/mbAIscvip"
    FISH_AUDIO_API_KEY: Optional[str] = None
    FISH_AUDIO_BASE_URL: str = "https://api.fish.audio"

    @staticmethod
    def from_env(env: dict) -> EnvConfig:
        """Create from environment variables"""
        return EnvConfig(
            MBAISCVIP_API_KEY=env.get("MBAISCVIP_API_KEY"),
            MBAISCVIP_BASE_URL=env.get("MBAISCVIP_BASE_URL", "https://api.milorapart.top/apis/mbAIscvip"),
            FISH_AUDIO_API_KEY=env.get("FISH_AUDIO_API_KEY"),
            FISH_AUDIO_BASE_URL=env.get("FISH_AUDIO_BASE_URL", "https://api.fish.audio"),
        )

    def validate_for_mode(self, mode: TTSMode) -> bool:
        """Validate environment configuration for a specific TTS mode"""
        if mode == TTSMode.MBAISCVIP:
            return bool(self.MBAISCVIP_API_KEY)
        elif mode == TTSMode.FISH_AUDIO:
            return bool(self.FISH_AUDIO_API_KEY)
        elif mode == TTSMode.MANUAL_AUDIO:
            return True
        return False


# Example usage and integration patterns

def example_mbaiscvip_job_config() -> dict:
    """Example job.json configuration for 曼波 AI"""
    return {
        "script_file": "inputs/script.txt",
        "title": "My Video",
        "voice": {
            "mode": "mbaiscvip",
            "format": "mp3",
            "speed": "0"
        },
        "images": [],
        "target": {
            "aspect_ratio": "9:16",
            "width": 1080,
            "height": 1920,
            "fps": 30
        }
    }


def example_manual_audio_job_config() -> dict:
    """Example job.json configuration for manual audio"""
    return {
        "script_file": "inputs/script.txt",
        "title": "My Video",
        "voice": {
            "mode": "manual_audio",
            "audio_uri": "inputs/voiceover.mp3"
        },
        "images": [],
        "target": {
            "aspect_ratio": "9:16",
            "width": 1080,
            "height": 1920,
            "fps": 30
        }
    }


def example_tts_request(text: str) -> TTSRequest:
    """Example TTS request"""
    return TTSRequest(
        text=text,
        mode=TTSMode.MBAISCVIP,
        format=AudioFormat.MP3,
        speed="0",
        max_segment_length=200
    )


if __name__ == "__main__":
    # Example usage
    config = VoiceConfig(
        mode=TTSMode.MBAISCVIP,
        format=AudioFormat.MP3,
        speed="0"
    )
    print("Voice Config:", config.to_dict())

    segment = VoiceSegment(
        index=1,
        text="Claude Code is a powerful code editor.",
        raw_path="audio/raw_segments/segment_001.mp3",
        wav_path="audio/wav_segments/segment_001.wav",
        duration=2.345,
        source_url="https://example.com/audio/xxxxx.mp3"
    )
    print("Voice Segment:", segment.to_dict())

    result = VoiceoverResult(
        path=Path("audio/voiceover.wav"),
        segments=[segment]
    )
    print("Voiceover Result:")
    print(f"  Path: {result.path}")
    print(f"  Segments: {result.segment_count()}")
    print(f"  Total Duration: {result.voiceover_duration()}s")
