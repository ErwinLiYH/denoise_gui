"""降噪引擎 — 统一接口，支持 ZipEnhancer 和 DPDFNet"""

import numpy as np
import io
import tempfile
import os
import soundfile as sf

# ---------------------------------------------------------------------------
# 模型名称常量
# ---------------------------------------------------------------------------
MODEL_NAMES = [
    "zipenhancer",
    "dpdfnet_baseline",
    "dpdfnet2",
    "dpdfnet4",
    "dpdfnet8",
    "dpdfnet2_48khz_hr",
    "dpdfnet8_48khz_hr",
]

# ---------------------------------------------------------------------------
# ZipEnhancer (ModelScope)
# ---------------------------------------------------------------------------
_zipenhancer_pipeline = None  # 懒加载


def _get_zipenhancer():
    global _zipenhancer_pipeline
    if _zipenhancer_pipeline is None:
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks

        _zipenhancer_pipeline = pipeline(
            Tasks.acoustic_noise_suppression,
            model="damo/speech_zipenhancer_ans_multiloss_16k_base",
        )
    return _zipenhancer_pipeline


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """简单重采样：用 scipy 若可用，否则用线性插值"""
    if orig_sr == target_sr:
        return audio
    try:
        from scipy import signal
        # 计算重采样长度
        num_samples = int(len(audio) * target_sr / orig_sr)
        return signal.resample(audio, num_samples)
    except ImportError:
        # 回退：线性插值
        duration = len(audio) / orig_sr
        new_len = int(duration * target_sr)
        old_indices = np.linspace(0, len(audio) - 1, len(audio))
        new_indices = np.linspace(0, len(audio) - 1, new_len)
        return np.interp(new_indices, old_indices, audio)


def _denoise_zipenhancer(audio: np.ndarray, sr: int) -> np.ndarray:
    """ZipEnhancer 降噪：自动处理 16kHz 单声道重采样"""
    # 单声道
    if audio.ndim > 1:
        audio = audio[:, 0]

    audio = audio.astype(np.float64)

    # 重采样到 16kHz
    audio_16k = _resample(audio, sr, 16000)

    # 归一化
    peak = np.max(np.abs(audio_16k))
    if peak > 0:
        audio_16k = audio_16k / peak * 0.95

    # 写入临时 WAV（ModelScope pipeline 需要文件路径或 URL）
    tmp_in = tempfile.mktemp(suffix=".wav")
    tmp_out = tempfile.mktemp(suffix=".wav")

    try:
        sf.write(tmp_in, audio_16k.astype(np.float32), 16000)
        pipeline = _get_zipenhancer()
        pipeline(tmp_in, output_path=tmp_out)
        enhanced, fs = sf.read(tmp_out)
    finally:
        for p in (tmp_in, tmp_out):
            if os.path.exists(p):
                os.unlink(p)

    # 转回原始采样率
    enhanced = _resample(enhanced.astype(np.float64), 16000, sr)
    return enhanced.astype(np.float32)


# ---------------------------------------------------------------------------
# DPDFNet
# ---------------------------------------------------------------------------
def _denoise_dpdfnet(audio: np.ndarray, sr: int, model_name: str) -> np.ndarray:
    """DPDFNet 降噪"""
    import dpdfnet

    # 运行时校验模型是否存在于 dpdfnet 库中
    available = {r["name"] for r in dpdfnet.available_models()}
    if model_name not in available:
        raise ValueError(
            f"DPDFNet 库中不存在模型 '{model_name}'。\n"
            f"可用模型: {sorted(available)}\n"
            f"请先运行 dpdfnet.download('{model_name}') 下载。"
        )

    if audio.ndim > 1:
        audio = audio[:, 0]

    audio = audio.astype(np.float32)
    enhanced = dpdfnet.enhance(audio, sample_rate=sr, model=model_name, attn_limit_db=12)
    return enhanced


# ---------------------------------------------------------------------------
# 统一接口
# ---------------------------------------------------------------------------
def denoise(audio: np.ndarray, sr: int, model_name: str) -> np.ndarray:
    """
    对音频数组降噪。

    参数
    ----
    audio : np.ndarray  输入音频 (shape: (N,) 或 (N, C))
    sr : int            采样率
    model_name : str    模型名称，见 MODEL_NAMES

    返回
    ----
    enhanced : np.ndarray  降噪后音频 (单声道)
    """
    model_name = model_name.strip()
    if model_name == "zipenhancer":
        return _denoise_zipenhancer(audio, sr)
    elif model_name in MODEL_NAMES:  # 精确匹配，避免 startswith 受不可见字符影响
        return _denoise_dpdfnet(audio, sr, model_name)
    else:
        raise ValueError(f"未知模型: {model_name}，可选: {MODEL_NAMES}")


def get_model_display_names():
    """返回用户友好的模型显示名列表"""
    return [
        "ZipEnhancer (16kHz)",
        "DPDFNet - baseline (16kHz, 最快)",
        "DPDFNet - dpdfnet2 (16kHz, 实时)",
        "DPDFNet - dpdfnet4 (16kHz, 均衡)",
        "DPDFNet - dpdfnet8 (16kHz, 最佳)",
        "DPDFNet - dpdfnet2 (48kHz, 均衡)",
        "DPDFNet - dpdfnet8 (48kHz, 最佳)",
    ]
