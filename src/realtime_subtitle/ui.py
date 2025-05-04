import tkinter as tk
from tkinter import *
from .realtime_subtitle import RealtimeSubtitle
from . import app_config
rs = RealtimeSubtitle()
cfg = app_config.get()
# UI
root = tk.Tk()
root.title('Realtime Subtitle')
# 字幕一行的长度
SUBTITLE_LENGTH = cfg.SubtitleLength
# 字幕显示几行
SUBTITLE_HIGH = cfg.SubtitleHight

TRANSLATION_SUBTITLE_LENGTH = cfg.TranslationSubtitleLength
TRANSLATION_SUBTITLE_HIGH = cfg.TranslationSubtitleHight

# 模型输出比上一次超过这个长度就可能是抽风了
MODLE_OUTPUT_ADD_THRESHOLD = 80
# 模型输出比上次少于这个长度可能也是抽风了
MODLE_OUTPUT_SUB_THRESHOLD = 3
# 连续抽风这么多次可能就不是抽了，由它去吧
MODLE_REFUSE_THRESHOLD = cfg.ModelRefuseThreshold
model_thrashing_count = 0

# 记录上一次的总数据长度，只有当新的数据比上一次多时才刷新。避免模型抽风，导致闪烁
last_all_text_length = 0


# 开始/暂停 按钮
def start_stop_button_onclick():
    '''
    开始/暂停 按钮
    '''
    if rs.running:
        # to stop
        rs.stop()
        start_stop_button.config(text="Start")
    else:
        # to start
        rs.start()
        start_stop_button.config(text="Stop")


start_stop_button = tk.Button(
    root, text='Start', width=10, command=start_stop_button_onclick)
start_stop_button.grid(row=0, column=0)

# 开启悬浮窗口 原文字幕
floating_window_open = BooleanVar()


def get_floating_window_position():
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_offset = int(screen_width * cfg.FloatingWindowXOffset)
    y_offset = int(screen_height * cfg.FloatingWindowYOffset)
    return f"+{x_offset}+{y_offset}"


def floating_check_button_onclick():
    global floating_window
    global FloatingText
    if floating_window_open.get():
        # 创建一个新的顶层窗口
        floating_window = tk.Toplevel(root)
        floating_window.title("")
        floating_window.geometry(
            cfg.FloatingWindowSize + get_floating_window_position())  # 设置窗口大小
        floating_window.attributes("-topmost", True)  # 窗口始终置顶
        floating_window.attributes(
            "-alpha", cfg.FloatingWindowTransparency)  # 设置窗口透明度 (0.0-1.0)

        # 禁用窗口边框
        floating_window.overrideredirect(not cfg.EnableFloatingWindowEdge)
        # 设置窗口背景颜色
        floating_window.configure(bg="")

        # 添加一个 Text 模块
        FloatingText = tk.Text(
            floating_window,
            width=50,
            height=10,
            font=("Helvetica", cfg.FloatingWindowFontSize, "bold"),
            bd=0,  # 移除边框
            highlightthickness=0,  # 移除焦点高亮
        )
        FloatingText.pack(expand=True, fill="both")

        FloatingText.configure(
            bg=cfg.FloatingWindowBackgroundColor.strip('"'), fg=cfg.FloatingWindowTextColor.strip('"'))

        # 确保窗口始终置顶
        def keep_window_on_top():
            if floating_window_open.get():
                floating_window.attributes("-topmost", True)
                floating_window.after(1000, keep_window_on_top)  # 每隔 1 秒检查一次

        keep_window_on_top()

    else:
        if 'floating_window' in globals() and floating_window.winfo_exists():
            floating_window.destroy()


floating_check_button = Checkbutton(
    root, text='subtitle floating window', variable=floating_window_open, command=floating_check_button_onclick)
floating_check_button.grid(row=0, column=1)


# 开启悬浮窗口 翻译字幕
translation_floating_window_open = BooleanVar()


def get_translation_floating_window_position():
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_offset = int(screen_width * cfg.TranslationFloatingWindowXOffset)
    y_offset = int(screen_height * cfg.TranslationFloatingWindowYOffset)
    return f"+{x_offset}+{y_offset}"


def translation_floating_check_button_onclick():
    global translation_floating_window
    global TranslationFloatingText
    if translation_floating_window_open.get():
        # 创建一个新的顶层窗口
        translation_floating_window = tk.Toplevel(root)
        translation_floating_window.title("")
        translation_floating_window.geometry(
            cfg.FloatingWindowSize + get_translation_floating_window_position())  # 设置窗口大小
        translation_floating_window.attributes("-topmost", True)  # 窗口始终置顶
        translation_floating_window.attributes(
            "-alpha", cfg.FloatingWindowTransparency)  # 设置窗口透明度 (0.0-1.0)

        # 禁用窗口边框
        translation_floating_window.overrideredirect(
            not cfg.EnableFloatingWindowEdge)
        # 设置窗口背景颜色
        translation_floating_window.configure(bg="gray")  # 设置为透明背景的颜色

        # 添加一个 Text 模块
        TranslationFloatingText = tk.Text(
            translation_floating_window,
            width=50,
            height=10,
            font=("Helvetica", cfg.FloatingWindowFontSize, "bold"),
            bd=0,  # 移除边框
            highlightthickness=0,  # 移除焦点高亮
        )
        TranslationFloatingText.pack(expand=True, fill="both")

        # 设置 Text 的背景颜色为不透明
        TranslationFloatingText.configure(
            bg=cfg.FloatingWindowBackgroundColor.strip('"'), fg=cfg.FloatingWindowTextColor.strip('"'))

        # 确保窗口始终置顶
        def keep_window_on_top():
            if floating_window_open.get():
                translation_floating_window.attributes("-topmost", True)
                translation_floating_window.after(
                    1000, keep_window_on_top)  # 每隔 1 秒检查一次

        keep_window_on_top()

    else:
        if 'translation_floating_window' in globals() and translation_floating_window.winfo_exists():
            translation_floating_window.destroy()


translation_floating_check_button = Checkbutton(
    root, text='translation floating window', variable=translation_floating_window_open, command=translation_floating_check_button_onclick)
translation_floating_check_button.grid(row=0, column=2)


# 设置按钮
def setting_button_onclick():
    # 创建设置窗口
    setting_window = tk.Toplevel(root)
    setting_window.title("设置")
    setting_window.geometry("600x600")
    setting_window.grab_set()  # 模态窗口，阻止与主窗口交互

    # 创建一个滚动区域
    canvas = tk.Canvas(setting_window)
    scrollbar = tk.Scrollbar(
        setting_window, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # 字段控件存储
    field_widgets = {}

    # 动态生成字段控件
    def create_field_widgets():
        row = 0
        for field_name, field_type in cfg.__annotations__.items():
            if field_name == "AllModelName":  # 跳过 AllModelName
                continue

            # 创建标签
            label = tk.Label(scrollable_frame, text=field_name, anchor="w")
            label.grid(row=row, column=0, sticky="w", padx=10, pady=5)

            # 根据字段类型创建控件
            if field_name == "ModelName":
                # 下拉框
                field_var = tk.StringVar(value=cfg.ModelName)
                dropdown = tk.OptionMenu(
                    scrollable_frame, field_var, cfg.ModelName, *cfg.AllModelName
                )
                dropdown.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
                field_widgets[field_name] = field_var
            elif field_name == "InputDevice":
                # 下拉框
                field_var = tk.StringVar(value=cfg.InputDevice)
                dropdown = tk.OptionMenu(
                    scrollable_frame, field_var, cfg.InputDevice, *rs.get_input_devices()
                )
                dropdown.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
                field_widgets[field_name] = field_var
            elif field_type == bool:
                # 复选框
                field_var = tk.BooleanVar(value=cfg.__dict__[field_name])
                checkbox = tk.Checkbutton(scrollable_frame, variable=field_var)
                checkbox.grid(row=row, column=1, sticky="w", padx=10, pady=5)
                field_widgets[field_name] = field_var
            elif field_type in [int, float]:
                # 数字输入框
                field_var = tk.StringVar(value=str(cfg.__dict__[field_name]))
                entry = tk.Entry(scrollable_frame, textvariable=field_var)
                entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
                field_widgets[field_name] = field_var
            elif field_type == str:
                # 文本输入框
                field_var = tk.StringVar(value=cfg.__dict__[field_name])
                entry = tk.Entry(scrollable_frame, textvariable=field_var)
                entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
                field_widgets[field_name] = field_var

            row += 1
        # 提示
        label = tk.Label(scrollable_frame,
                         text="*Some settings, including ModelName, require restarting the program to take effect", anchor="w")
        label.grid(row=row, column=0, columnspan=2,
                   sticky="w", padx=10, pady=5)

    create_field_widgets()

    # 保存按钮
    def save_settings():
        for field_name, field_var in field_widgets.items():
            value = field_var.get()
            if isinstance(cfg.__dict__[field_name], int):
                value = int(value)
            elif isinstance(cfg.__dict__[field_name], float):
                value = float(value)
            cfg.__dict__[field_name] = value
        app_config.save(cfg)  # 保存配置
        setting_window.destroy()

    save_button = tk.Button(
        scrollable_frame, text="save", command=save_settings)
    save_button.grid(row=len(cfg.__annotations__)+1,
                     column=0, columnspan=2, pady=10)

    # 调整列宽
    scrollable_frame.columnconfigure(1, weight=1)


setting_button = tk.Button(
    root, text='settings', width=10, command=setting_button_onclick)
setting_button.grid(row=0, column=3)


# 导出按钮
def export_button_onclick():
    '''
    导出按钮
    '''
    rs.export()


export_button = tk.Button(
    root, text='export', width=10, command=export_button_onclick)
export_button.grid(row=0, column=4)


# 显示窗口
# 宽度占满
AllText = tk.Text(root, height=10, wrap=tk.WORD)
AllText.grid(row=1, column=0, columnspan=5, sticky="ew")

AllTranslationText = tk.Text(root, height=10, wrap=tk.WORD)
AllTranslationText.grid(row=2, column=0, columnspan=5, sticky="ew")


def get_all_text_with_speaker() -> str:
    result = ""
    current_speaker_name = ""
    for one in rs.archived_data:
        if current_speaker_name != one.speaker_index:
            current_speaker_name = one.speaker_index
            result += f"\n{current_speaker_name}:\n"
        result += one.text
    for one in rs.temp_data:
        if current_speaker_name != one.speaker_index:
            current_speaker_name = one.speaker_index
            result += f"\n{current_speaker_name}:\n"
        result += one.text

    return result


def update_hook():
    '''
    添加显示数据的回调函数
    '''
    global last_all_text_length
    global model_thrashing_count
    archived_text = ""
    temp_text = ""
    archived_translation = ""
    temp_translation = ""
    for one in rs.archived_data:
        archived_text += one.text
        archived_translation += one.translated_text
    for one in rs.temp_data:
        temp_text += one.text
    # 翻译不显示最新的，因为最新的抖动过于严重
    for one in rs.temp_data[:len(rs.temp_data)-cfg.TranslationPresantDelay]:
        temp_translation += one.translated_text
    all_text = archived_text + temp_text
    all_translation = archived_translation + temp_translation
    # 拦截模型抽风
    if len(all_text) > last_all_text_length + MODLE_OUTPUT_ADD_THRESHOLD or len(all_text) < last_all_text_length - MODLE_OUTPUT_SUB_THRESHOLD:
        model_thrashing_count += 1
        if model_thrashing_count < MODLE_REFUSE_THRESHOLD:
            return
        else:
            model_thrashing_count = 0  # let it go

    last_all_text_length = len(all_text)

    AllText.replace("1.0", tk.END, all_text)
    AllText.see(tk.END)  # 滚动到底部
    AllTranslationText.replace("1.0", tk.END, all_translation)
    AllTranslationText.see(tk.END)  # 滚动到底部

    try:
        if floating_window_open.get():
            # 计算字幕应该显示多少个字符
            show_length = len(all_text) % SUBTITLE_LENGTH + \
                (SUBTITLE_HIGH-1) * SUBTITLE_LENGTH
            # 将要显示的字符整理好，添加换行
            show_text = all_text[-show_length:]
            show_text_with_return = ""  # 添加换行
            for i in range(0, min(show_length, len(show_text))):  # 最开始 show_text 长度不够
                if i % SUBTITLE_LENGTH == 0 and i != 0:
                    show_text_with_return += "\n"
                show_text_with_return += show_text[i]
            FloatingText.replace("1.0", tk.END, show_text_with_return)

        if translation_floating_window_open.get():
            # 计算字幕应该显示多少个字符
            show_length = len(all_translation) % TRANSLATION_SUBTITLE_LENGTH + \
                (TRANSLATION_SUBTITLE_HIGH-1) * TRANSLATION_SUBTITLE_LENGTH
            # 将要显示的字符整理好，添加换行
            show_text = all_translation[-show_length:]
            show_text_with_return = ""  # 添加换行
            for i in range(0, min(show_length, len(show_text))):  # 最开始 show_text 长度不够
                if i % TRANSLATION_SUBTITLE_LENGTH == 0 and i != 0:
                    show_text_with_return += "\n"
                show_text_with_return += show_text[i]
            TranslationFloatingText.replace(
                "1.0", tk.END, show_text_with_return)
    except:
        # 用户可能手动关闭了悬浮窗口
        ...


rs.set_update_hook(update_hook)


def main():
    root.mainloop()


if __name__ == "__main__":
    main()
