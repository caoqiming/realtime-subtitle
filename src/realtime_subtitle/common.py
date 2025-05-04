import dataclasses

SAMPLE_RATE = 16000


@dataclasses.dataclass
class SubtitleData:
    # 识别到的文本
    text: str
    # 相对于整个录音的起始时间
    start_time: float
    # 相对于整个录音的结束时间
    end_time: float
    # 翻译
    translated_text: str
    speaker_index: int


def convert_time_to_index(t: float) -> int:
    # 原始数据是以字节存储的，采样点是int16，也就是说一个采样点对应两个字节
    return int(t*SAMPLE_RATE)*2  # 需要保证是2的整数倍
