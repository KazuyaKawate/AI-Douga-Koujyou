from pathlib import Path


def transcribe_audio(audio_path: Path, language: str = "ja") -> str:
    import whisper

    model = whisper.load_model("base")
    options = {} if language == "auto" else {"language": language}
    result = model.transcribe(str(audio_path), **options)
    return _to_srt(result["segments"])


def _to_srt(segments: list) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _fmt(seg["start"])
        end = _fmt(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def _fmt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
