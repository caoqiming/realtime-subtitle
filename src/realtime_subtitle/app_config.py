from dataclasses import dataclass, field
import dataclasses
import json
import os

CONFIG_FILE_PATH = "~/.config/glimmer/realtime-subtitle.config"


@dataclass
class AppConfig:
    InputDevice: str = "default"
    # 语音识别的模型名称
    ModelName: str = "mlx-community/whisper-tiny.en-mlx"
    # 可选的语音识别的模型名称
    AllModelName: list[str] = field(default_factory=lambda: [
        "mlx-community/whisper-tiny.en-mlx",
        "mlx-community/whisper-small-mlx",
        "mlx-community/whisper-medium-mlx",
        "mlx-community/whisper-turbo",
        "mlx-community/whisper-large-v3-mlx",
        "mlx-community/whisper-large-v3-turbo",
    ])
    Latency: float = 0.5
    MaxProcessTime = 30.0
    NoSpeechThreshold: float = 0.6
    LogprobThreshold: float = -1.0
    TolerationOfLies: float = 1.0
    # 翻译相关
    EnableTranslation: bool = True
    OnlineTranslation: bool = False
    TranslateFrom: str = "en"
    TranslateTo: str = "zh"
    # 语音识别
    EnableSpeakerRecognition: bool = True
    DbscanEps: float = 0.95
    # UI
    SubtitleLength: int = 80
    SubtitleHight: int = 3
    TranslationSubtitleLength: int = 39
    TranslationSubtitleHight: int = 3
    ModelRefuseThreshold: int = 3
    TranslationPresantDelay: int = 0  # 在最新的多少个segment之后才显示翻译，避免翻译显示抖动严重
    EnableFloatingWindowEdge: bool = False  # 悬浮窗口边框，没有边框就无法拖动
    FloatingWindowX: float = 0.5
    FloatingWindowY: float = 0.085
    FloatingWindowTransparency: float = 0.9  # 1.0 表示不透明
    FloatingWindowFontSize: int = 20
    FloatingWindowTextColor: str = "#004604"
    FloatingWindowBackgroundColor: str = "#dadada"
    FloatingWindowXOffset: float = 0.25
    FloatingWindowYOffset: float = 0.8
    TranslationFloatingWindowXOffset: float = 0.25
    TranslationFloatingWindowYOffset: float = 0.71
    # 文件保存路径
    SavePath: str = "~/Desktop/realtime-subtitle"


def _load_config(file_path: str) -> AppConfig:
    # 扩展文件路径中的 ~ 符号
    file_path = os.path.expanduser(file_path)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")

    # 从文件中读取 JSON 数据
    with open(file_path, 'r') as f:
        data = json.load(f)

    # 将 JSON 数据转换为 AppConfig 对象
    appConfig = AppConfig(**data)
    return appConfig


def _save_config(file_path: str, cfg: AppConfig):
    # 扩展文件路径中的 ~ 符号
    file_path = os.path.expanduser(file_path)
    # 确保目录存在
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    # 将配置写入文件
    with open(file_path, 'w') as f:
        f.write(json.dumps(dataclasses.asdict(cfg)))


def get() -> AppConfig:
    try:
        cfg = _load_config(CONFIG_FILE_PATH)
        return cfg
    except:
        # fallback to default config
        return AppConfig()


def save(cfg: AppConfig):
    _save_config(CONFIG_FILE_PATH, cfg)


if __name__ == "__main__":
    _save_config(
        CONFIG_FILE_PATH,
        AppConfig(
            ModelName="whisper-1",
            AllModelName=["whisper-1", "whisper-2"],
            Latency=0.5,
            Translate=True
        )
    )
    app_config = _load_config(CONFIG_FILE_PATH)
    print(app_config)
