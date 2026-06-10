"""Tkinter GUI — 视频音频降噪工具"""

import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 将当前目录加入 path，确保能导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_utils import (
    check_ffmpeg, set_ffmpeg_paths, extract_audio, merge_audio, cleanup,
)
from denoiser import denoise, MODEL_NAMES, get_model_display_names


# ---------------------------------------------------------------------------
# 后台任务消息类型
# ---------------------------------------------------------------------------
MSG_PROGRESS = "progress"   # data = (stage_text,)
MSG_DONE     = "done"       # data = (output_path,)
MSG_ERROR    = "error"      # data = (error_message,)


class DenoiseApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("视频音频降噪工具")
        self.root.geometry("620x360")
        self.root.resizable(True, False)

        # ── ffmpeg 检测 ──
        if not check_ffmpeg():
            if not self._ask_ffmpeg_path():
                self.root.destroy()
                return

        # ── 模型名称映射（显示名 → 内部 key） ──
        self._model_display_names = get_model_display_names()
        self._model_key_of = dict(zip(self._model_display_names, MODEL_NAMES))

        # ── 状态变量 ──
        self.video_path = tk.StringVar()
        self.model_display = tk.StringVar(value=self._model_display_names[2])  # 默认 dpdfnet2
        self.output_path = tk.StringVar()
        self.status_text = tk.StringVar(value="就绪，请选择视频文件")
        self.processing = False

        # 消息队列（后台线程 → UI）
        self.msg_queue = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------
    # ffmpeg 路径配置弹窗
    # ------------------------------------------------------------------
    def _ask_ffmpeg_path(self) -> bool:
        """
        弹出提示让用户手动定位 ffmpeg 可执行文件。
        返回 True 表示配置成功，False 表示用户放弃。
        """
        while True:
            answer = messagebox.askyesno(
                "ffmpeg 未找到",
                "未在系统 PATH 中找到 ffmpeg！\n\n"
                "请手动定位 ffmpeg 可执行文件（如 ffmpeg.exe）。\n"
                "是否现在选择？\n\n"
                "（选「否」将退出程序）",
            )
            if not answer:
                return False

            # 选择 ffmpeg
            ffmpeg_path = filedialog.askopenfilename(
                title="请选择 ffmpeg 可执行文件",
                filetypes=[
                    ("ffmpeg", "ffmpeg.exe ffmpeg"),
                    ("所有文件", "*.*"),
                ],
            )
            if not ffmpeg_path:
                continue  # 用户点了取消，重新问

            # 自动推断 ffprobe 路径（同目录下）
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            ffmpeg_base = os.path.basename(ffmpeg_path)
            # 推断 ffprobe 名称
            if ffmpeg_base.startswith("ffmpeg"):
                ffprobe_name = ffmpeg_base.replace("ffmpeg", "ffprobe", 1)
            else:
                ffprobe_name = "ffprobe.exe" if ffmpeg_base.endswith(".exe") else "ffprobe"
            ffprobe_path = os.path.join(ffmpeg_dir, ffprobe_name)

            # 如果自动推断的 ffprobe 不存在，让用户手动选
            if not (os.path.isfile(ffprobe_path) and os.access(ffprobe_path, os.X_OK)):
                messagebox.showinfo(
                    "请选择 ffprobe",
                    "同目录下未找到 ffprobe，请手动选择 ffprobe 可执行文件。",
                )
                ffprobe_path = filedialog.askopenfilename(
                    title="请选择 ffprobe 可执行文件",
                    filetypes=[
                        ("ffprobe", "ffprobe.exe ffprobe"),
                        ("所有文件", "*.*"),
                    ],
                )
                if not ffprobe_path:
                    continue

            # 验证两个文件是否真正可用
            from video_utils import _validate_binary
            if not _validate_binary(ffmpeg_path):
                messagebox.showerror(
                    "无效的 ffmpeg",
                    f"所选文件不是有效的 ffmpeg：\n{ffmpeg_path}\n\n请重新选择。",
                )
                continue
            if not _validate_binary(ffprobe_path):
                messagebox.showerror(
                    "无效的 ffprobe",
                    f"所选文件不是有效的 ffprobe：\n{ffprobe_path}\n\n请重新选择。",
                )
                continue

            set_ffmpeg_paths(ffmpeg_path, ffprobe_path)
            messagebox.showinfo(
                "配置成功",
                f"ffmpeg 已配置：\n{ffmpeg_path}\nffprobe 已配置：\n{ffprobe_path}\n\n现在可以正常使用了。",
            )
            return True

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = self.root
        pad = {"padx": 12, "pady": 6}

        # ── 菜单栏 ──
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="另存为...", command=self._choose_output)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        root.config(menu=menubar)

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)

        # ── 第 1 行：选择视频 ──
        row1 = ttk.Frame(main)
        row1.pack(fill="x", **pad)
        ttk.Button(row1, text="选择视频", command=self._choose_video).pack(side="left")
        ttk.Label(row1, textvariable=self.video_path, foreground="gray").pack(
            side="left", padx=8, fill="x", expand=True
        )

        # ── 第 2 行：模型选择 ──
        row2 = ttk.Frame(main)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="降噪模型：").pack(side="left")
        self.model_combo = ttk.Combobox(
            row2,
            textvariable=self.model_display,
            values=self._model_display_names,
            state="readonly",
            width=40,
        )
        self.model_combo.pack(side="left", padx=8)

        # ── 第 3 行：输出路径 ──
        row3 = ttk.Frame(main)
        row3.pack(fill="x", **pad)
        ttk.Label(row3, text="输出路径：").pack(side="left")
        ttk.Label(row3, textvariable=self.output_path, foreground="blue").pack(
            side="left", padx=8, fill="x", expand=True
        )

        # ── 第 4 行：按钮 + 进度条 ──
        row4 = ttk.Frame(main)
        row4.pack(fill="x", **pad)
        self.denoise_btn = ttk.Button(
            row4, text="开始降噪", command=self._start_denoise
        )
        self.denoise_btn.pack(side="left", padx=(0, 16))

        self.progress = ttk.Progressbar(
            row4, mode="indeterminate", length=300
        )
        self.progress.pack(side="left", fill="x", expand=True)

        # ── 第 5 行：状态 ──
        row5 = ttk.Frame(main)
        row5.pack(fill="x", **pad)
        ttk.Label(row5, textvariable=self.status_text, foreground="#224466").pack(
            side="left"
        )

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------
    def _choose_video(self):
        path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self.video_path.set(path)
            # 自动生成输出路径
            dirname = os.path.dirname(path)
            basename = os.path.splitext(os.path.basename(path))[0]
            ext = os.path.splitext(path)[1]
            self.output_path.set(os.path.join(dirname, f"{basename}_denoised{ext}"))

    def _choose_output(self):
        if not self.video_path.get():
            messagebox.showwarning("提示", "请先选择输入视频")
            return
        path = filedialog.asksaveasfilename(
            title="保存降噪视频",
            defaultextension=os.path.splitext(self.video_path.get())[1],
            initialfile=self.output_path.get(),
            filetypes=[
                ("MP4", "*.mp4"),
                ("MKV", "*.mkv"),
                ("MOV", "*.mov"),
                ("AVI", "*.avi"),
            ],
        )
        if path:
            self.output_path.set(path)

    @property
    def _model_key(self) -> str:
        """当前选择的模型内部 key"""
        return self._model_key_of.get(self.model_display.get(), MODEL_NAMES[2])

    def _start_denoise(self):
        if self.processing:
            return
        if not self.video_path.get():
            messagebox.showwarning("提示", "请先选择视频文件")
            return
        if not os.path.exists(self.video_path.get()):
            messagebox.showerror("错误", "视频文件不存在")
            return

        self.processing = True
        self.denoise_btn.config(state="disabled")
        self.progress.start(10)
        self.status_text.set("正在准备...")

        # 在主线程捕获参数，避免跨线程访问 Tk 变量
        video_path = self.video_path.get()
        model_key = self._model_key
        output_path = self.output_path.get()

        thread = threading.Thread(
            target=self._run_pipeline,
            args=(video_path, model_key, output_path),
            daemon=True,
        )
        thread.start()

    # ------------------------------------------------------------------
    # 后台 pipeline
    # ------------------------------------------------------------------
    def _run_pipeline(self, video_path: str, model_key: str, output_path: str):
        """后台线程：提取 → 降噪 → 合成"""
        tmp_wav = None
        try:
            # ── 阶段 1：提取音频 ──
            self._post_progress("正在提取音频...")
            tmp_wav, sr, duration = extract_audio(video_path)

            # ── 阶段 2：降噪 ──
            if duration > 0:
                self._post_progress(
                    f"正在降噪...（音频时长 {int(duration//60)}分{int(duration%60)}秒，请耐心等待）"
                )
            else:
                self._post_progress("正在降噪...")

            import soundfile as sf
            audio, sr_read = sf.read(tmp_wav)
            # soundfile 读取的可能和 ffprobe 不同，以读取为准
            sr = sr_read
            enhanced = denoise(audio, sr, model_key)

            # 写回临时 WAV
            sf.write(tmp_wav, enhanced, sr)

            # ── 阶段 3：合成视频 ──
            self._post_progress("正在合成视频...")
            merge_audio(video_path, tmp_wav, output_path)

            # ── 完成 ──
            self.msg_queue.put((MSG_DONE, output_path))

        except Exception as e:
            self.msg_queue.put((MSG_ERROR, str(e)))
        finally:
            if tmp_wav:
                cleanup([tmp_wav])

    def _post_progress(self, text: str):
        self.msg_queue.put((MSG_PROGRESS, text))

    # ------------------------------------------------------------------
    # 轮询消息队列
    # ------------------------------------------------------------------
    def _poll_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                msg_type = msg[0]
                if msg_type == MSG_PROGRESS:
                    self.status_text.set(msg[1])
                elif msg_type == MSG_DONE:
                    self.progress.stop()
                    self.progress.config(mode="determinate", value=100)
                    self.status_text.set("完成！降噪视频已保存")
                    self.processing = False
                    self.denoise_btn.config(state="normal")
                    messagebox.showinfo("完成", f"降噪完成！\n\n已保存至：\n{msg[1]}")
                elif msg_type == MSG_ERROR:
                    self.progress.stop()
                    self.progress.config(mode="indeterminate")
                    self.status_text.set("出错")
                    self.processing = False
                    self.denoise_btn.config(state="normal")
                    messagebox.showerror("错误", f"处理失败：\n{msg[1]}")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    app = DenoiseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
