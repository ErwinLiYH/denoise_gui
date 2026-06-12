"""Bilingual text dictionary for the Video Audio Denoiser GUI.

Usage:
    from i18n import TEXTS
    t = TEXTS["zh"]["choose_btn"]       # "选择视频"
    t = TEXTS["en"]["choose_btn"]       # "Select Video"
"""

TEXTS = {
    "zh": {
        # ── window ──
        "window_title": "视频音频降噪工具",
        "lang_btn": "English",

        # ── ffmpeg dialogs ──
        "ffmpeg_not_found_title": "ffmpeg 未找到",
        "ffmpeg_not_found_msg": (
            "未在系统 PATH 中找到 ffmpeg！\n\n"
            "请手动定位 ffmpeg 可执行文件（如 ffmpeg.exe）。\n"
            "是否现在选择？\n\n"
            "（选「否」将退出程序）"
        ),
        "ffmpeg_select_title": "请选择 ffmpeg 可执行文件",
        "ffmpeg_filetype": "ffmpeg",
        "all_files": "所有文件",
        "ffprobe_select_title": "请选择 ffprobe",
        "ffprobe_not_found_msg": "同目录下未找到 ffprobe，请手动选择 ffprobe 可执行文件。",
        "ffprobe_filetype": "ffprobe",
        "ffmpeg_invalid_title": "无效的 ffmpeg",
        "ffmpeg_invalid_msg": "所选文件不是有效的 ffmpeg：\n{path}\n\n请重新选择。",
        "ffprobe_invalid_title": "无效的 ffprobe",
        "ffprobe_invalid_msg": "所选文件不是有效的 ffprobe：\n{path}\n\n请重新选择。",
        "ffmpeg_config_ok_title": "配置成功",
        "ffmpeg_config_ok_msg": (
            "ffmpeg 已配置：\n{ffmpeg}\n"
            "ffprobe 已配置：\n{ffprobe}\n\n"
            "现在可以正常使用了。"
        ),

        # ── UI: config section ──
        "config_frame": "任务配置",
        "pending_placeholder": "未选择文件，点击下方选择按钮添加视频",
        "choose_btn": "选择视频",
        "add_btn": "加入队列",
        "hint_label": "选择视频可以多次多个选择，点击加入队列将上方所选视频以下方配置加入队列",
        "model_label": "降噪模型：",
        "output_mode_label": "输出模式：",
        "output_replace": "替换原音轨",
        "output_add": "添加为新音轨",
        "attn_label": "降噪质量：",
        "attn_hint_default": "0~30，越大越温和（保真度高）；越小降噪越激进（去噪强）。推荐 6~12",
        "attn_hint_zipenhancer": "ZipEnhancer 不支持此参数",

        # ── UI: queue section ──
        "queue_frame": "任务队列",
        "col_index": "#",
        "col_video": "视频文件",
        "col_model": "降噪模型",
        "col_mode": "输出模式",
        "col_output": "输出路径",
        "col_status": "状态",
        "remove_btn": "移除选中",
        "clear_btn": "清空全部",
        "start_btn": "▶ 开始处理队列",

        # ── Job status ──
        "job_status_pending": "⏳等待",
        "job_status_running": "🔄处理中",
        "job_status_done": "✅完成",
        "job_status_error": "❌失败",

        # ── output mode display ──
        "mode_replace": "替换",
        "mode_add": "添加",

        # ── file dialog ──
        "video_select_title": "选择视频文件（可多选）",
        "video_filetype": "视频文件",

        # ── status messages ──
        "status_files_chosen": "已选择 {count} 个文件，点击「加入队列」确认",
        "status_jobs_added": "已添加 {added} 个视频到队列（共 {total} 个任务）",
        "status_jobs_remaining": "队列剩余 {count} 个任务",
        "status_queue_cleared": "队列已清空",
        "status_queue_start": "开始处理队列（共 {count} 个任务）...",
        "status_processing": "正在处理 {idx}/{total} — {name}",
        "status_queue_done": "队列处理完毕：成功 {success} 个，失败 {fail} 个",
        "status_done_single": "完成！降噪视频已保存",
        "status_error_single": "出错",

        # ── progress strings (background thread) ──
        "progress_extract": "[{idx}/{total}] 正在提取音频：{name}",
        "progress_denoise_with_dur": "[{idx}/{total}] 正在降噪：{name}（{min}分{sec}秒）",
        "progress_denoise": "[{idx}/{total}] 正在降噪：{name}",
        "progress_merge": "[{idx}/{total}] 正在合成视频：{name}",

        # ── messagebox ──
        "msgbox_info": "提示",
        "msgbox_confirm": "确认",
        "msg_no_video_selected": "请先选择视频文件",
        "msg_duplicate_video_title": "重复视频",
        "msg_duplicate_video": "视频「{name}」已在队列中，已自动跳过。\n\n路径：{path}",
        "msg_clear_confirm": "确定要清空全部 {count} 个任务吗？",
        "msg_queue_empty": "任务队列为空，请先添加任务",
        "msg_reprocess_title": "队列中有已完成的任务",
        "msg_reprocess": (
            "队列中包含之前已完成或失败的任务。\n"
            "是否重新运行整个队列？\n"
            "（选「否」将取消启动）"
        ),
        "msg_queue_done_title": "全部完成",
        "msg_queue_done_summary": "队列处理完毕！\n成功：{success} 个\n失败：{fail} 个\n",
        "msg_queue_fail_item": "  ✗ [{idx}] {name}\n      原因：{error}",
        "msg_queue_fail_title": "队列完成（有失败）",
        "msg_done_single_title": "完成",
        "msg_done_single": "降噪完成！\n\n已保存至：\n{path}",
        "msg_error_single_title": "错误",
        "msg_error_single": "处理失败：\n{msg}",

        # ── model display names ──
        "model_display_zipenhancer": "ZipEnhancer (16kHz)",
        "model_display_dpdfnet_baseline": "DPDFNet - baseline (16kHz, 最快)",
        "model_display_dpdfnet2": "DPDFNet - dpdfnet2 (16kHz, 实时)",
        "model_display_dpdfnet4": "DPDFNet - dpdfnet4 (16kHz, 均衡)",
        "model_display_dpdfnet8": "DPDFNet - dpdfnet8 (16kHz, 最佳)",
        "model_display_dpdfnet2_48khz_hr": "DPDFNet - dpdfnet2 (48kHz, 均衡)",
        "model_display_dpdfnet8_48khz_hr": "DPDFNet - dpdfnet8 (48kHz, 最佳)",
    },

    "en": {
        # ── window ──
        "window_title": "Video Audio Denoiser",
        "lang_btn": "中文",

        # ── ffmpeg dialogs ──
        "ffmpeg_not_found_title": "ffmpeg Not Found",
        "ffmpeg_not_found_msg": (
            "ffmpeg was not found in the system PATH!\n\n"
            "Please locate the ffmpeg executable (e.g. ffmpeg.exe).\n"
            "Would you like to select it now?\n\n"
            "(Select 'No' to exit the program)"
        ),
        "ffmpeg_select_title": "Select ffmpeg executable",
        "ffmpeg_filetype": "ffmpeg",
        "all_files": "All Files",
        "ffprobe_select_title": "Select ffprobe",
        "ffprobe_not_found_msg": (
            "ffprobe was not found in the same directory. "
            "Please locate the ffprobe executable manually."
        ),
        "ffprobe_filetype": "ffprobe",
        "ffmpeg_invalid_title": "Invalid ffmpeg",
        "ffmpeg_invalid_msg": (
            "The selected file is not a valid ffmpeg:\n{path}\n\n"
            "Please select again."
        ),
        "ffprobe_invalid_title": "Invalid ffprobe",
        "ffprobe_invalid_msg": (
            "The selected file is not a valid ffprobe:\n{path}\n\n"
            "Please select again."
        ),
        "ffmpeg_config_ok_title": "Configuration Successful",
        "ffmpeg_config_ok_msg": (
            "ffmpeg configured:\n{ffmpeg}\n"
            "ffprobe configured:\n{ffprobe}\n\n"
            "You can now use the tool normally."
        ),

        # ── UI: config section ──
        "config_frame": "Task Configuration",
        "pending_placeholder": (
            "No files selected. Click the Select Video button below to add videos."
        ),
        "choose_btn": "Select Video",
        "add_btn": "Add to Queue",
        "hint_label": (
            "You can select multiple videos. "
            "Click 'Add to Queue' to add them with the settings below."
        ),
        "model_label": "Denoising Model:",
        "output_mode_label": "Output Mode:",
        "output_replace": "Replace Original",
        "output_add": "Add as New Track",
        "attn_label": "Denoising Strength:",
        "attn_hint_default": (
            "0–30, higher = gentler (better fidelity); "
            "lower = more aggressive. Recommended: 6–12"
        ),
        "attn_hint_zipenhancer": "ZipEnhancer does not support this parameter",

        # ── UI: queue section ──
        "queue_frame": "Task Queue",
        "col_index": "#",
        "col_video": "Video File",
        "col_model": "Model",
        "col_mode": "Mode",
        "col_output": "Output Path",
        "col_status": "Status",
        "remove_btn": "Remove Selected",
        "clear_btn": "Clear All",
        "start_btn": "▶ Start Processing",

        # ── Job status ──
        "job_status_pending": "⏳Pending",
        "job_status_running": "🔄Processing",
        "job_status_done": "✅Done",
        "job_status_error": "❌Failed",

        # ── output mode display ──
        "mode_replace": "Replace",
        "mode_add": "Add",

        # ── file dialog ──
        "video_select_title": "Select Video Files (multi-select)",
        "video_filetype": "Video Files",

        # ── status messages ──
        "status_files_chosen": (
            "{count} file(s) selected. Click 'Add to Queue' to confirm"
        ),
        "status_jobs_added": (
            "{added} video(s) added to queue ({total} task(s) total)"
        ),
        "status_jobs_remaining": "{count} task(s) remaining in queue",
        "status_queue_cleared": "Queue cleared",
        "status_queue_start": (
            "Starting queue processing ({count} task(s))..."
        ),
        "status_processing": "Processing {idx}/{total} — {name}",
        "status_queue_done": (
            "Queue finished: {success} succeeded, {fail} failed"
        ),
        "status_done_single": "Done! Denoised video saved.",
        "status_error_single": "Error",

        # ── progress strings (background thread) ──
        "progress_extract": "[{idx}/{total}] Extracting audio: {name}",
        "progress_denoise_with_dur": (
            "[{idx}/{total}] Denoising: {name} ({min}m {sec}s)"
        ),
        "progress_denoise": "[{idx}/{total}] Denoising: {name}",
        "progress_merge": "[{idx}/{total}] Merging video: {name}",

        # ── messagebox ──
        "msgbox_info": "Info",
        "msgbox_confirm": "Confirm",
        "msg_no_video_selected": "Please select a video file first.",
        "msg_duplicate_video_title": "Duplicate Video",
        "msg_duplicate_video": (
            "Video '{name}' is already in the queue. Skipped.\n\nPath: {path}"
        ),
        "msg_clear_confirm": (
            "Are you sure you want to clear all {count} task(s)?"
        ),
        "msg_queue_empty": "The task queue is empty. Please add tasks first.",
        "msg_reprocess_title": "Completed tasks in queue",
        "msg_reprocess": (
            "The queue contains previously completed or failed tasks.\n"
            "Do you want to re-run the entire queue?\n"
            "(Select 'No' to cancel)"
        ),
        "msg_queue_done_title": "All Done",
        "msg_queue_done_summary": (
            "Queue finished!\nSucceeded: {success}\nFailed: {fail}\n"
        ),
        "msg_queue_fail_item": "  ✗ [{idx}] {name}\n      Reason: {error}",
        "msg_queue_fail_title": "Queue Finished (with failures)",
        "msg_done_single_title": "Done",
        "msg_done_single": "Denoising complete!\n\nSaved to:\n{path}",
        "msg_error_single_title": "Error",
        "msg_error_single": "Processing failed:\n{msg}",

        # ── model display names ──
        "model_display_zipenhancer": "ZipEnhancer (16kHz)",
        "model_display_dpdfnet_baseline": "DPDFNet - baseline (16kHz, Fastest)",
        "model_display_dpdfnet2": "DPDFNet - dpdfnet2 (16kHz, Real-time)",
        "model_display_dpdfnet4": "DPDFNet - dpdfnet4 (16kHz, Balanced)",
        "model_display_dpdfnet8": "DPDFNet - dpdfnet8 (16kHz, Best)",
        "model_display_dpdfnet2_48khz_hr": "DPDFNet - dpdfnet2 (48kHz, Balanced)",
        "model_display_dpdfnet8_48khz_hr": "DPDFNet - dpdfnet8 (48kHz, Best)",
    },
}
