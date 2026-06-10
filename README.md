# Video Audio Denoiser

基于深度学习的视频音轨降噪工具，支持两种模型：

- **ZipEnhancer**（阿里通义实验室）— 16kHz 单麦语音降噪，ModelScope pipeline
- **DPDFNet**（CEVA）— 多采样率语音增强，6 个变体可选（baseline / dpdfnet2 / dpdfnet4 / dpdfnet8 / 48kHz 系列）

## 安装

### 1. 安装 ffmpeg

本工具依赖系统 ffmpeg 进行视频音频提取与合成。

- **Windows**：下载 [ffmpeg](https://ffmpeg.org/download.html)，解压后将 `bin` 目录加入 PATH
- **macOS**：`brew install ffmpeg`
- **Ubuntu/Debian**：`sudo apt install ffmpeg`
- 检查是否安装成功：`ffmpeg -version`

### 2. 安装 Python 依赖

```bash
cd video_denoiser
pip install -r requirements.txt
```

> Linux 用户如果 soundfile 报错，需要安装 libsndfile：
> ```bash
> sudo apt install libsndfile1
> ```

## 使用

```bash
python main.py
```

1. 点击「选择视频」按钮选择视频文件
2. 在下拉框选择降噪模型
3. 点击「开始降噪」
4. 等待处理完成，降噪后的视频自动保存为 `原文件名_denoised.扩展名`

首次使用会自动下载模型权重，ZipEnhancer 约 19MB，DPDFNet 按所选模型约 8-18MB。
