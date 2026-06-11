"""视频处理工具 — ffmpeg 音频提取 / 合成 / 清理"""

import os
import subprocess
import tempfile
import shutil

# ── 可配置的 ffmpeg / ffprobe 路径 ──
_FFMPEG_PATH = "ffmpeg"
_FFPROBE_PATH = "ffprobe"


def set_ffmpeg_paths(ffmpeg_path: str, ffprobe_path: str):
    """手动设置 ffmpeg 和 ffprobe 的可执行文件路径"""
    global _FFMPEG_PATH, _FFPROBE_PATH
    _FFMPEG_PATH = ffmpeg_path
    _FFPROBE_PATH = ffprobe_path


def get_ffmpeg_path() -> str:
    return _FFMPEG_PATH


def get_ffprobe_path() -> str:
    return _FFPROBE_PATH


def _run_ffmpeg(args: list, description: str = ""):
    """运行 ffmpeg，失败时抛出 RuntimeError"""
    cmd = [_FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 失败 ({description}):\n{result.stderr.strip()}"
        )
    return result


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否可用（先查 PATH，再试已配置的自定义路径）"""
    # 1) 如果路径已经是绝对路径且可执行，直接校验
    if os.path.isabs(_FFMPEG_PATH) and os.access(_FFMPEG_PATH, os.X_OK):
        return True
    # 2) 尝试 PATH 中查找
    if shutil.which(_FFMPEG_PATH) is not None:
        return True
    # 3) 尝试当前工作目录
    if os.path.isfile(_FFMPEG_PATH) and os.access(_FFMPEG_PATH, os.X_OK):
        return True
    return False


def _validate_binary(path: str) -> bool:
    """运行 path -version 验证是否是有效的 ffmpeg/ffprobe"""
    try:
        result = subprocess.run(
            [path, "-version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def extract_audio(video_path: str) -> tuple:
    """
    从视频提取音频为临时 WAV。

    返回: (temp_wav_path, sample_rate, duration_seconds)
    """
    # 先获取音频信息
    probe_cmd = [
        _FFPROBE_PATH, "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,duration",
        "-of", "csv=p=0",
        video_path,
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    if probe.returncode != 0 or not probe.stdout.strip():
        raise RuntimeError("无法读取视频音频信息，请确认视频包含音轨")

    info = probe.stdout.strip().split(",")
    sample_rate = int(info[0]) if info[0] else 44100
    duration = float(info[1]) if len(info) > 1 and info[1] else 0.0

    # 如果探测不到 duration，用 ffprobe 另一种方式
    if duration == 0.0:
        probe_cmd2 = [
            _FFPROBE_PATH, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            video_path,
        ]
        probe2 = subprocess.run(probe_cmd2, capture_output=True, text=True)
        if probe2.returncode == 0 and probe2.stdout.strip():
            try:
                duration = float(probe2.stdout.strip())
            except ValueError:
                duration = 0.0

    # 创建临时 WAV 文件
    tmp_wav = tempfile.mktemp(suffix=".wav")

    _run_ffmpeg(
        ["-i", video_path, "-ac", "1", "-ar", str(sample_rate),
         "-sample_fmt", "s16", tmp_wav],
        description="提取音频",
    )

    return tmp_wav, sample_rate, duration


def merge_audio(video_path: str, new_audio_path: str, output_path: str):
    """
    将新音频合成回视频：视频流 copy，音频替换。

    输出格式由 output_path 的扩展名决定。
    """
    # 获取原视频扩展名
    _, ext = os.path.splitext(output_path)
    ext = ext.lower()

    if ext in (".mp4", ".m4v"):
        # MP4: AAC 音频编码
        _run_ffmpeg(
            ["-i", video_path, "-i", new_audio_path,
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-map", "0:v:0", "-map", "1:a:0",
             "-shortest", output_path],
            description="合成视频 (MP4)",
        )
    elif ext in (".mkv", ".webm"):
        _run_ffmpeg(
            ["-i", video_path, "-i", new_audio_path,
             "-c:v", "copy", "-c:a", "libvorbis",
             "-map", "0:v:0", "-map", "1:a:0",
             "-shortest", output_path],
            description="合成视频 (MKV/WEBM)",
        )
    elif ext in (".mov",):
        _run_ffmpeg(
            ["-i", video_path, "-i", new_audio_path,
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-map", "0:v:0", "-map", "1:a:0",
             "-shortest", output_path],
            description="合成视频 (MOV)",
        )
    elif ext in (".avi",):
        _run_ffmpeg(
            ["-i", video_path, "-i", new_audio_path,
             "-c:v", "copy", "-c:a", "mp3",
             "-map", "0:v:0", "-map", "1:a:0",
             "-shortest", output_path],
            description="合成视频 (AVI)",
        )
    else:
        # 兜底：MP4 容器 + AAC
        _run_ffmpeg(
            ["-i", video_path, "-i", new_audio_path,
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-map", "0:v:0", "-map", "1:a:0",
             "-shortest", output_path],
            description="合成视频",
        )


def count_audio_streams(video_path: str) -> int:
    """统计视频中的音轨数量"""
    probe_cmd = [
        _FFPROBE_PATH, "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        video_path,
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    if probe.returncode != 0 or not probe.stdout.strip():
        return 0
    lines = [l for l in probe.stdout.strip().split("\n") if l.strip()]
    return len(lines)


def add_audio_track(video_path: str, new_audio_path: str,
                    output_path: str, track_title: str):
    """
    将降噪音频追加为新的音轨，保留原视频所有音轨。

    - 原视频流全部 copy 不重编码
    - 新音轨按容器选择编码器，metadata title 设为 track_title
    """
    _, ext = os.path.splitext(output_path)
    ext = ext.lower()
    existing = count_audio_streams(video_path)
    new_track_index = existing  # 新音轨在输出中的索引

    # 按容器选编码器
    if ext in (".mkv", ".webm"):
        codec = "libvorbis"
    elif ext in (".avi",):
        codec = "mp3"
    else:
        codec = "aac"

    common = [
        "-i", video_path,
        "-i", new_audio_path,
        "-map", "0",            # 原视频所有流
        "-map", "1:a:0",        # 新音频
        "-c", "copy",          # 所有流默认 copy
        "-c:a:" + str(new_track_index), codec,
        "-b:a:" + str(new_track_index), "192k",
        "-metadata:s:a:" + str(new_track_index),
        "title=" + track_title,
        "-shortest",
        output_path,
    ]
    _run_ffmpeg(common, description="添加音轨")


def cleanup(paths: list):
    """清理临时文件"""
    for p in paths:
        if os.path.exists(p):
            try:
                os.unlink(p)
            except OSError:
                pass
