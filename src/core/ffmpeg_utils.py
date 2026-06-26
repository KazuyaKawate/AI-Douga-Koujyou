from pathlib import Path
from typing import Optional


def get_video_info(video_path: Path) -> dict:
    try:
        import ffmpeg
        probe = ffmpeg.probe(str(video_path))
        info = {"duration": f'{float(probe["format"]["duration"]):.1f} 秒'}
        for stream in probe["streams"]:
            if stream["codec_type"] == "video":
                info["解像度"] = f'{stream["width"]}x{stream["height"]}'
                info["フレームレート"] = stream.get("r_frame_rate", "不明")
            elif stream["codec_type"] == "audio":
                info["音声コーデック"] = stream.get("codec_name", "不明")
        return info
    except Exception:
        return {}


def combine_video_audio_subtitle(
    video: Optional[Path],
    audio: Optional[Path],
    subtitle: Optional[Path],
    output: Path,
) -> bool:
    try:
        import ffmpeg

        output.parent.mkdir(parents=True, exist_ok=True)

        inputs = []
        if video:
            inputs.append(ffmpeg.input(str(video)))
        if audio:
            inputs.append(ffmpeg.input(str(audio)))

        if not inputs:
            return False

        kwargs = {"vcodec": "libx264", "acodec": "aac"}

        if subtitle and subtitle.exists():
            sub_escaped = str(subtitle).replace("\\", "/").replace(":", "\\:")
            kwargs["vf"] = f"subtitles='{sub_escaped}'"

        out = ffmpeg.output(*inputs, str(output), **kwargs)
        ffmpeg.run(out, overwrite_output=True, quiet=True)
        return True
    except Exception as e:
        print(f"FFmpeg error: {e}")
        return False
