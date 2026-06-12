"""Tkinter GUI — 视频音频降噪工具"""

import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass
from enum import Enum

# 将当前目录加入 path，确保能导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_utils import (
    check_ffmpeg, set_ffmpeg_paths, extract_audio, merge_audio, cleanup,
    add_audio_track,
)
from denoiser import denoise, MODEL_NAMES, get_model_display_names


# ---------------------------------------------------------------------------
# 后台任务消息类型
# ---------------------------------------------------------------------------
MSG_PROGRESS    = "progress"     # data = (stage_text,)
MSG_DONE        = "done"         # data = (output_path,)
MSG_ERROR       = "error"        # data = (error_message,)
MSG_JOB_START   = "job_start"    # data = (job_index,)
MSG_JOB_DONE    = "job_done"     # data = (job_index, output_path)
MSG_JOB_ERROR   = "job_error"    # data = (job_index, error_message)
MSG_QUEUE_DONE  = "queue_done"   # data = (success_count, fail_count)


class JobStatus(Enum):
    PENDING = "⏳等待"
    RUNNING = "🔄处理中"
    DONE    = "✅完成"
    ERROR   = "❌失败"


@dataclass
class JobConfig:
    """单个降噪任务的配置"""
    video_path: str
    model_key: str          # 内部 key，如 dpdfnet8_48khz_hr
    model_display: str      # 显示名，如 DPDFNet - dpdfnet8 (48kHz, 最佳)
    output_path: str
    output_mode: str        # replace / add
    attn_limit_db: float
    status: JobStatus = JobStatus.PENDING
    error_message: str = ""

    @property
    def video_basename(self) -> str:
        return os.path.basename(self.video_path)


class DenoiseApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("视频音频降噪工具")
        self.root.geometry("920x820")
        self.root.resizable(True, True)

        # ── ffmpeg 检测 ──
        if not check_ffmpeg():
            if not self._ask_ffmpeg_path():
                self.root.destroy()
                return

        # ── 模型名称映射（显示名 → 内部 key） ──
        self._model_display_names = get_model_display_names()
        self._model_key_of = dict(zip(self._model_display_names, MODEL_NAMES))

        # ── 状态变量 ──
        self._pending_files: list[str] = []  # 待加入队列的已选文件路径
        self.model_display = tk.StringVar(value=self._model_display_names[6])  # 默认 dpdfnet8 48khz
        self.status_text = tk.StringVar(value="未选择文件，点击下方选择按钮添加视频")
        self.output_mode = tk.StringVar(value="add")  # replace / add
        self.attn_db_var = tk.IntVar(value=12)
        self.processing = False

        # ── 任务队列 ──
        self.jobs: list[JobConfig] = []

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
        pad = {"padx": 12, "pady": 4}

        main = ttk.Frame(root, padding=12)
        main.pack(fill="both", expand=True)

        # ==============================================================
        # 上半部分：任务配置
        # ==============================================================
        config_frame = ttk.LabelFrame(main, text="任务配置", padding=10)
        config_frame.pack(fill="x", pady=(0, 8))

        # ── 第 1 行：已选文件列表 ──
        pending_frame = ttk.Frame(config_frame)
        pending_frame.pack(fill="x", **pad)
        self.pending_text = tk.Text(
            pending_frame, height=10, state="disabled",
            bg=self.root.cget("bg"), relief="sunken", borderwidth=1,
            font=("TkDefaultFont", 9), wrap="none",
        )
        pending_scroll = ttk.Scrollbar(
            pending_frame, orient="vertical", command=self.pending_text.yview
        )
        self.pending_text.configure(yscrollcommand=pending_scroll.set)
        self.pending_text.pack(side="left", fill="both", expand=True)
        pending_scroll.pack(side="right", fill="y")
        self._refresh_pending_display()

        # ── 第 2 行：选择视频 / 加入队列 ──
        row1 = ttk.Frame(config_frame)
        row1.pack(fill="x", **pad)
        self.choose_btn = ttk.Button(row1, text="选择视频", command=self._choose_video)
        self.choose_btn.pack(side="left", padx=(0, 8))
        self.add_btn = ttk.Button(row1, text="加入队列", command=self._add_to_queue)
        self.add_btn.pack(side="left")

        # ── 第 3 行：注释 ──
        ttk.Label(
            config_frame,
            text="选择视频可以多次多个选择，点击加入队列将上方所选视频以下方配置加入队列",
            foreground="gray", font=("TkDefaultFont", 8),
        ).pack(fill="x", padx=12, pady=(0, 6))

        # ── 第 4 行：模型选择 ──
        row2 = ttk.Frame(config_frame)
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
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_changed)

        # ── 第 4 行：输出模式 ──
        row_mode = ttk.Frame(config_frame)
        row_mode.pack(fill="x", **pad)
        ttk.Label(row_mode, text="输出模式：").pack(side="left")
        self.radio_replace = ttk.Radiobutton(
            row_mode, text="替换原音轨", variable=self.output_mode, value="replace",
        )
        self.radio_replace.pack(side="left", padx=(4, 16))
        self.radio_add = ttk.Radiobutton(
            row_mode, text="添加为新音轨", variable=self.output_mode, value="add",
        )
        self.radio_add.pack(side="left")

        # ── 第 5 行：降噪质量（仅 DPDFNet） ──
        row_attn = ttk.Frame(config_frame)
        row_attn.pack(fill="x", **pad)
        ttk.Label(row_attn, text="降噪质量：").pack(side="left")
        self.attn_spinbox = ttk.Spinbox(
            row_attn, from_=0, to=30, increment=1, width=5,
            textvariable=self.attn_db_var,
        )
        self.attn_spinbox.pack(side="left", padx=4)
        self.attn_hint_label = ttk.Label(
            row_attn,
            text="0~30，越大越温和（保真度高）；越小降噪越激进（去噪强）。推荐 6~12",
            foreground="gray",
        )
        self.attn_hint_label.pack(side="left", padx=4)

        # ==============================================================
        # 中间部分：任务队列
        # ==============================================================
        queue_frame = ttk.LabelFrame(main, text="任务队列", padding=10)
        queue_frame.pack(fill="both", expand=True, pady=(0, 8))

        # Treeview
        columns = ("#", "video", "model", "mode", "output", "status")
        self.queue_tree = ttk.Treeview(
            queue_frame, columns=columns, show="headings",
            height=8, selectmode="extended",
        )
        self.queue_tree.heading("#", text="#")
        self.queue_tree.heading("video", text="视频文件")
        self.queue_tree.heading("model", text="降噪模型")
        self.queue_tree.heading("mode", text="输出模式")
        self.queue_tree.heading("output", text="输出路径")
        self.queue_tree.heading("status", text="状态")

        self.queue_tree.column("#", width=40, anchor="center", stretch=False)
        self.queue_tree.column("video", width=180, anchor="w")
        self.queue_tree.column("model", width=200, anchor="w")
        self.queue_tree.column("mode", width=80, anchor="center")
        self.queue_tree.column("output", width=220, anchor="w")
        self.queue_tree.column("status", width=100, anchor="center")

        vsb = ttk.Scrollbar(queue_frame, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=vsb.set)

        self.queue_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # 队列操作按钮行
        queue_btn_row = ttk.Frame(main)
        queue_btn_row.pack(fill="x", pady=(0, 8))
        self.remove_btn = ttk.Button(
            queue_btn_row, text="移除选中", command=self._remove_selected
        )
        self.remove_btn.pack(side="left", padx=(0, 8))
        self.clear_btn = ttk.Button(
            queue_btn_row, text="清空全部", command=self._clear_queue
        )
        self.clear_btn.pack(side="left")

        # ==============================================================
        # 底部：启动 + 进度条 + 状态
        # ==============================================================
        bottom = ttk.Frame(main)
        bottom.pack(fill="x")

        self.start_queue_btn = ttk.Button(
            bottom, text="▶ 开始处理队列", command=self._start_queue
        )
        self.start_queue_btn.pack(side="left", padx=(0, 12))

        self.progress = ttk.Progressbar(
            bottom, mode="determinate", length=300
        )
        self.progress.pack(side="left", fill="x", expand=True)

        # 状态标签
        status_row = ttk.Frame(main)
        status_row.pack(fill="x", pady=(6, 0))
        ttk.Label(status_row, textvariable=self.status_text, foreground="#224466").pack(
            side="left"
        )

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------
    def _on_model_changed(self, event=None):
        """模型切换时联动启用/禁用降噪质量控件"""
        if self._model_key == "zipenhancer":
            self.attn_spinbox.config(state="disabled")
            self.attn_hint_label.config(
                text="ZipEnhancer 不支持此参数",
                foreground="gray",
            )
        else:
            self.attn_spinbox.config(state="normal")
            self.attn_hint_label.config(
                text="0~30，越大越温和（保真度高）；越小降噪越激进（去噪强）。推荐 6~12",
                foreground="gray",
            )

    def _choose_video(self):
        """多选视频文件，追加到待添加列表"""
        paths = filedialog.askopenfilenames(
            title="选择视频文件（可多选）",
            filetypes=[
                ("视频文件", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self._pending_files.extend(paths)
            self._refresh_pending_display()
            self.status_text.set(f"已选择 {len(self._pending_files)} 个文件，点击「加入队列」确认")

    def _add_to_queue(self):
        """将 _pending_files 中的所有文件按当前配置加入队列"""
        if not self._pending_files:
            messagebox.showwarning("提示", "请先选择视频文件")
            return

        added = 0
        for path in self._pending_files:
            dirname = os.path.dirname(path)
            basename_noext = os.path.splitext(os.path.basename(path))[0]
            ext = os.path.splitext(path)[1]
            output_path = os.path.join(dirname, f"{basename_noext}_denoised{ext}")
            if self._try_add_job(path, output_path):
                added += 1

        # 清空待添加列表
        self._pending_files.clear()
        self._refresh_pending_display()

        if added > 0:
            self._refresh_tree()
        self.status_text.set(f"已添加 {added} 个视频到队列（共 {len(self.jobs)} 个任务）")

    @property
    def _model_key(self) -> str:
        """当前选择的模型内部 key"""
        return self._model_key_of.get(self.model_display.get(), MODEL_NAMES[6])

    def _set_controls_state(self, disabled: bool):
        """统一控制所有交互控件的启用/禁用"""
        new_state = "disabled" if disabled else "normal"
        combo_state = "disabled" if disabled else "readonly"
        self.choose_btn.config(state=new_state)
        self.add_btn.config(state=new_state)
        self.start_queue_btn.config(state=new_state)
        self.remove_btn.config(state=new_state)
        self.clear_btn.config(state=new_state)
        self.model_combo.config(state=combo_state)
        self.radio_replace.config(state=new_state)
        self.radio_add.config(state=new_state)
        # Spinbox 只在 DPDFNet 模型下恢复
        if disabled:
            self.attn_spinbox.config(state="disabled")
        else:
            self._on_model_changed()

    # ------------------------------------------------------------------
    # 任务队列管理
    # ------------------------------------------------------------------
    def _refresh_pending_display(self):
        """刷新已选文件列表的 Text 显示"""
        self.pending_text.config(state="normal")
        self.pending_text.delete("1.0", "end")
        if not self._pending_files:
            self.pending_text.insert(
                "1.0", "未选择文件，点击下方选择按钮添加视频"
            )
        else:
            self.pending_text.insert("1.0", "\n".join(self._pending_files))
        self.pending_text.config(state="disabled")

    def _try_add_job(self, video_path: str, output_path: str) -> bool:
        """尝试添加一个任务到队列，自动去重。返回 True 表示成功添加。"""
        # 去重检查
        existing = {job.video_path for job in self.jobs}
        if video_path in existing:
            basename = os.path.basename(video_path)
            messagebox.showwarning(
                "重复视频",
                f"视频「{basename}」已在队列中，已自动跳过。\n\n路径：{video_path}",
            )
            return False

        job = JobConfig(
            video_path=video_path,
            model_key=self._model_key,
            model_display=self.model_display.get(),
            output_path=output_path,
            output_mode=self.output_mode.get(),
            attn_limit_db=float(self.attn_db_var.get()),
        )
        self.jobs.append(job)
        return True

    def _remove_selected(self):
        """删除 Treeview 中选中的任务"""
        selected_iids = self.queue_tree.selection()
        if not selected_iids:
            return
        # 从后往前删，避免索引偏移
        indices = sorted(
            [self.queue_tree.index(iid) for iid in selected_iids],
            reverse=True,
        )
        for idx in indices:
            if 0 <= idx < len(self.jobs):
                self.jobs.pop(idx)
        self._refresh_tree()
        self.status_text.set(f"队列剩余 {len(self.jobs)} 个任务")

    def _clear_queue(self):
        """清空全部任务"""
        if not self.jobs:
            return
        if messagebox.askyesno("确认", f"确定要清空全部 {len(self.jobs)} 个任务吗？"):
            self.jobs.clear()
            self._refresh_tree()
            self.status_text.set("队列已清空")

    def _refresh_tree(self):
        """全量刷新 Treeview"""
        for row in self.queue_tree.get_children():
            self.queue_tree.delete(row)
        for i, job in enumerate(self.jobs):
            mode_text = "替换" if job.output_mode == "replace" else "添加"
            # DPDFNet 模型显示时追加降噪强度
            if job.model_key == "zipenhancer":
                model_text = job.model_display
            else:
                model_text = f"{job.model_display}, {job.attn_limit_db:.0f}dB"
            self.queue_tree.insert(
                "", "end", iid=str(i),
                values=(
                    i + 1,
                    job.video_path,
                    model_text,
                    mode_text,
                    job.output_path,
                    job.status.value,
                ),
            )

    def _update_job_row(self, idx: int):
        """更新 Treeview 中某一行的显示（状态等）"""
        if 0 <= idx < len(self.jobs):
            job = self.jobs[idx]
            mode_text = "替换" if job.output_mode == "replace" else "添加"
            if job.model_key == "zipenhancer":
                model_text = job.model_display
            else:
                model_text = f"{job.model_display}, {job.attn_limit_db:.0f}dB"
            iid = str(idx)
            if self.queue_tree.exists(iid):
                self.queue_tree.item(iid, values=(
                    idx + 1,
                    job.video_path,
                    model_text,
                    mode_text,
                    job.output_path,
                    job.status.value,
                ))

    # ------------------------------------------------------------------
    # 队列处理
    # ------------------------------------------------------------------
    def _start_queue(self):
        """启动队列处理"""
        if self.processing:
            return
        if not self.jobs:
            messagebox.showwarning("提示", "任务队列为空，请先添加任务")
            return

        # 检查是否有已完成/失败的任务，重置为 pending
        has_processed = any(j.status in (JobStatus.DONE, JobStatus.ERROR) for j in self.jobs)
        if has_processed:
            if not messagebox.askyesno(
                "队列中有已完成的任务",
                "队列中包含之前已完成或失败的任务。\n是否重新运行整个队列？\n（选「否」将取消启动）"
            ):
                return
            for j in self.jobs:
                j.status = JobStatus.PENDING
                j.error_message = ""
            self._refresh_tree()

        self.processing = True
        self._set_controls_state(True)
        self.progress["maximum"] = len(self.jobs)
        self.progress["value"] = 0
        self.status_text.set(f"开始处理队列（共 {len(self.jobs)} 个任务）...")

        # 快照当前队列（避免并发修改）
        jobs_snapshot = list(self.jobs)

        thread = threading.Thread(
            target=self._run_queue,
            args=(jobs_snapshot,),
            daemon=True,
        )
        thread.start()

    def _run_queue(self, jobs: list):
        """后台线程：顺序处理每个 job"""
        for idx, job in enumerate(jobs):
            # 跳过已标记为错误的（理论上不会）
            job.status = JobStatus.RUNNING
            self.msg_queue.put((MSG_JOB_START, idx))

            tmp_wav = None
            try:
                self._post_progress(f"[{idx + 1}/{len(jobs)}] 正在提取音频：{job.video_basename}")
                tmp_wav, sr, duration = extract_audio(job.video_path)

                if duration > 0:
                    self._post_progress(
                        f"[{idx + 1}/{len(jobs)}] 正在降噪：{job.video_basename}"
                        f"（{int(duration // 60)}分{int(duration % 60)}秒）"
                    )
                else:
                    self._post_progress(
                        f"[{idx + 1}/{len(jobs)}] 正在降噪：{job.video_basename}"
                    )

                import soundfile as sf
                audio, sr_read = sf.read(tmp_wav)
                sr = sr_read
                enhanced = denoise(audio, sr, job.model_key,
                                   attn_limit_db=job.attn_limit_db)
                sf.write(tmp_wav, enhanced, sr)

                self._post_progress(f"[{idx + 1}/{len(jobs)}] 正在合成视频：{job.video_basename}")
                if job.output_mode == "add":
                    if job.model_key == "zipenhancer":
                        track_title = "ZipEnhancer"
                    else:
                        track_title = (
                            f"DPDFNet {job.model_key}"
                            f" (attn_limit_db={job.attn_limit_db:.0f}dB)"
                        )
                    add_audio_track(job.video_path, tmp_wav, job.output_path,
                                    track_title)
                else:
                    merge_audio(job.video_path, tmp_wav, job.output_path)

                job.status = JobStatus.DONE
                self.msg_queue.put((MSG_JOB_DONE, idx, job.output_path))

            except Exception as e:
                job.status = JobStatus.ERROR
                job.error_message = str(e)
                self.msg_queue.put((MSG_JOB_ERROR, idx, str(e)))
            finally:
                if tmp_wav:
                    cleanup([tmp_wav])

        # 全部完成
        success = sum(1 for j in jobs if j.status == JobStatus.DONE)
        fail = sum(1 for j in jobs if j.status == JobStatus.ERROR)
        self.msg_queue.put((MSG_QUEUE_DONE, success, fail))

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

                elif msg_type == MSG_JOB_START:
                    idx = msg[1]
                    self._update_job_row(idx)
                    job = self.jobs[idx]
                    self.status_text.set(
                        f"正在处理 {idx + 1}/{len(self.jobs)} — {job.video_basename}"
                    )

                elif msg_type == MSG_JOB_DONE:
                    idx, output_path = msg[1], msg[2]
                    self._update_job_row(idx)
                    self.progress["value"] = idx + 1

                elif msg_type == MSG_JOB_ERROR:
                    idx, error_msg = msg[1], msg[2]
                    self._update_job_row(idx)
                    self.progress["value"] = idx + 1

                elif msg_type == MSG_QUEUE_DONE:
                    success, fail = msg[1], msg[2]
                    self.progress["value"] = len(self.jobs)
                    self.processing = False
                    self._set_controls_state(False)
                    self.status_text.set(
                        f"队列处理完毕：成功 {success} 个，失败 {fail} 个"
                    )
                    # 构建摘要
                    summary_lines = [f"队列处理完毕！\n成功：{success} 个\n失败：{fail} 个\n"]
                    for i, job in enumerate(self.jobs):
                        if job.status == JobStatus.ERROR:
                            summary_lines.append(
                                f"  ✗ [{i+1}] {job.video_basename}\n"
                                f"      原因：{job.error_message}"
                            )
                    if fail > 0:
                        messagebox.showwarning(
                            "队列完成（有失败）",
                            "\n".join(summary_lines),
                        )
                    else:
                        messagebox.showinfo("全部完成", "\n".join(summary_lines))

                elif msg_type == MSG_DONE:
                    # 兼容旧的单任务消息（保留但不再触发）
                    self.progress.stop()
                    self.progress.config(mode="determinate", value=100)
                    self.status_text.set("完成！降噪视频已保存")
                    self.processing = False
                    self._set_controls_state(False)
                    messagebox.showinfo("完成", f"降噪完成！\n\n已保存至：\n{msg[1]}")

                elif msg_type == MSG_ERROR:
                    # 兼容旧的单任务消息
                    self.progress.stop()
                    self.progress.config(mode="indeterminate")
                    self.status_text.set("出错")
                    self.processing = False
                    self._set_controls_state(False)
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
