import wave
import pyaudio
import threading
import mlx_whisper
import numpy as np
import time
import dataclasses
import threading
import json
import argostranslate.package
import argostranslate.translate
from translate import Translator
from . import app_config
from . import glimmer_speech_recognition
import os
from .common import *

cfg = app_config.get()

TEMP_SEGMENT_SIZE = 2


class RealtimeSubtitle:
    # 输入设备map，描述 to deviceindex
    device_map: dict[str, int]
    model_name = cfg.ModelName
    # "mlx-community/whisper-small-mlx"
    # "mlx-community/whisper-medium-mlx"
    # "mlx-community/whisper-turbo"
    # "mlx-community/whisper-large-v3-mlx"
    # "mlx-community/whisper-large-v3-turbo"
    lock = threading.Lock()
    # 原始的音频数据储存在这里
    audio_buffer = bytes()
    # 从这个索引开始处理，不用每次从头开始
    start_index: int = 0
    # 与 start_index 等价，单位为秒
    start_time: float = 0.0
    # 归档的数据，不再改变
    archived_data: list[SubtitleData] = []
    # 最近的两条数据，可以改变
    temp_data: list[SubtitleData] = []
    # 读取音频的线程，生产者
    listen_thread: threading.Thread
    # 处理音频的线程，消费者
    handle_thread: threading.Thread
    # 用户控制程序的运行和暂停
    running: bool = False
    # 当前输入模型的数据长度，用于判断模型是否开始编故事了
    current_buffer_length: int = 0

    # 开启读取麦克风的线程
    def start_listen(self):
        def listen():
            p = pyaudio.PyAudio()
            device_id = self.get_selected_input_device_id()
            if device_id < 0:
                print("use default device")
                stream = p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=SAMPLE_RATE,
                                input=True,
                                frames_per_buffer=1024)
            else:
                print(f"use device {device_id}")
                stream = p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=SAMPLE_RATE,
                                input=True,
                                input_device_index=device_id,
                                frames_per_buffer=1024)
            # 开始录音
            try:
                while True:
                    if not self.running:
                        print("stop listen")
                        return
                    data = stream.read(1024)
                    self.lock.acquire()
                    self.audio_buffer = self.audio_buffer + data
                    self.lock.release()
            except Exception as e:
                print(f"Error listening: {e}")
            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()
        self.listen_thread = threading.Thread(target=listen, daemon=True)
        self.listen_thread.start()

    # 开启线程持续处理数据
    def start_handle(self):
        def handle():
            while (1):
                self.lock.acquire()
                if not self.running:
                    print("stop handle")
                    self.lock.release()
                    return
                if self.start_index > len(self.audio_buffer):
                    print("\nself.start_index %d ,len(self.audio_buffer) %d\n" %
                          (self.start_index, len(self.audio_buffer)))
                    raise Exception("start_index out of range")

                current_buffer = self.audio_buffer[self.start_index:]
                self.current_buffer_length = len(current_buffer)
                current_buffer_length_time = self.convert_index_to_time(
                    self.current_buffer_length)
                if current_buffer_length_time > cfg.MaxProcessTime:
                    print("drop dara, current length %f, exceeds max length %f" %
                          (current_buffer_length_time, cfg.MaxProcessTime))
                    # 调整 start_time 使得要处理的数据不超过最大处理时间
                    # 这里调整到最大处理时长的1/5
                    self.start_time = self.convert_index_to_time(
                        len(self.audio_buffer)) - (cfg.MaxProcessTime / 5.0)
                    self.start_index = self.convert_time_to_index(
                        self.start_time)
                    self.lock.release()
                    continue

                self.lock.release()
                # 开始处理数据
                start_time = time.time()
                audio_np = np.frombuffer(
                    current_buffer, dtype=np.int16).astype(np.float32) / 32768.0
                result = mlx_whisper.transcribe(
                    audio_np, path_or_hf_repo=self.model_name,
                    condition_on_previous_text=False,
                    no_speech_threshold=cfg.NoSpeechThreshold,
                    logprob_threshold=cfg.LogprobThreshold,
                    temperature=(0.0, 0.2))
                end_time = time.time()
                used_time = end_time - start_time

                print("handle %f ,costs %f\n" %
                      (current_buffer_length_time, end_time - start_time))
                self.handle_result(result)
                if cfg.Latency-used_time > 0:
                    time.sleep(cfg.Latency-used_time)
        self.handle_thread = threading.Thread(target=handle, daemon=True)
        self.handle_thread.start()

    # 处理一次数据，用于处理从文件读取的数据
    def handle_once(self):
        audio_np = np.frombuffer(
            self.audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
        result = mlx_whisper.transcribe(
            audio_np, path_or_hf_repo=self.model_name,
            condition_on_previous_text=False,
            no_speech_threshold=cfg.NoSpeechThreshold,
            logprob_threshold=cfg.LogprobThreshold,
            temperature=(0.0, 0.2))
        self.current_buffer_length = len(self.audio_buffer)
        self.handle_result(result)

    def handle_result(self, result: dict):
        # 计算当前喂给模型的终止时间，超过这个时间的数据都是模型在编故事
        max_end_time = self.start_time + \
            self.convert_index_to_time(self.current_buffer_length)

        segments = result['segments']
        self.temp_data.clear()
        last_archived_end_time = -1.0
        for i in range(0, len(segments)):
            current_seg = segments[i]
            # convert segment to SubtitleData
            new_data = SubtitleData(
                text=current_seg['text'],
                start_time=self.start_time + current_seg['start'],
                end_time=self.start_time + current_seg['end'],
                translated_text="",
                speaker_index=-1,
            )

            # validate data
            # 1. skip empty text
            if len(new_data.text) == 0:
                print("[handle result]skip empty text")
                continue
            # 2. skip lies
            if new_data.end_time > max_end_time + cfg.TolerationOfLies:
                print("[handle result]skip lies, max_end_time %f, exceeds %f" %
                      (max_end_time, new_data.end_time - max_end_time))
                continue

            if cfg.EnableTranslation:
                if cfg.OnlineTranslation:
                    new_data.translated_text = self.OnlineTranslator.translate(
                        new_data.text)
                else:
                    new_data.translated_text = argostranslate.translate.translate(
                        new_data.text, cfg.TranslateFrom, cfg.TranslateTo)

            if i < len(segments) - TEMP_SEGMENT_SIZE:
                self.archived_data.append(new_data)
                last_archived_end_time = new_data.end_time
            else:
                self.temp_data.append(new_data)

        # 更新 start_index 和 start_time
        if last_archived_end_time > 0 and last_archived_end_time < max_end_time:
            self.start_time = last_archived_end_time
            self.start_index = self.convert_time_to_index(self.start_time)
        if hasattr(self, 'update_hook') and callable(self.update_hook):
            self.update_hook()

    def convert_time_to_index(self, t: float) -> int:
        # 原始数据是以字节存储的，采样点是int16，也就是说一个采样点对应两个字节
        return int(t*SAMPLE_RATE)*2  # 需要保证是2的整数倍

    def convert_index_to_time(self, index: int) -> float:
        return index/2.0/SAMPLE_RATE

    def show_result(self):
        '''
        展示结果
        '''
        all_text = ""
        for one in self.archived_data:
            all_text += one.text + "\n"
        for one in self.temp_data:
            all_text += one.text + "\n"
        print(all_text)

    def data_to_json(self, data: list[SubtitleData]):
        data_list = []
        for one in data:
            data_list.append(dataclasses.asdict(one))
        return json.dumps(data_list)

    def save_audio(self, path):
        waveFile = wave.open(path, 'wb')
        waveFile.setnchannels(1)
        waveFile.setframerate(SAMPLE_RATE)
        waveFile.setsampwidth(
            pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        # self.lock.acquire()
        waveFile.writeframes(self.audio_buffer)
        # self.lock.release()
        waveFile.close()

    def export(self, speaker_num: int = -1):
        '''
        1. 保存音频
        2. 保存json格式源信息方便debug
        3. 声纹识别
        4. 保存字幕
        5. 以 html 格式保存使其可交互
        '''
        print("start export...")
        current_time = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        save_dir = cfg.SavePath + "/" + current_time
        save_dir = os.path.expanduser(save_dir)
        # 创建目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # 保存音频
        audio_path = save_dir + "/audio.wav"
        self.save_audio(audio_path)

        # 合并 archived_data 和 temp_data
        all_data = self.archived_data + self.temp_data
        json_debug_path = save_dir + "/result.json"
        with open(json_debug_path, "w", encoding="utf-8") as f:
            f.write(self.data_to_json(all_data))

        # 声纹识别
        if cfg.EnableSpeakerRecognition:
            speaker_recognition_start = time.time()
            print("start speaker recognition, this may takes some time...")
            self.speech_recognition.fit_predict(
                all_data, self.audio_buffer, speaker_num=speaker_num)
            speaker_recognition_end = time.time()
            print("speaker recognition costs %f" %
                  (speaker_recognition_end - speaker_recognition_start))

        # 按 LRC 格式保存
        lrc_path = save_dir + "/subtitles.lrc"
        with open(lrc_path, "w", encoding="utf-8") as lrc_file:
            for data in all_data:
                start_time = self.format_time(data.start_time, lrc=True)
                lrc_file.write(f"[{start_time}]{data.text}\n")

        # 按字幕格式保存
        subtitle_path = save_dir + "/subtitles.srt"
        with open(subtitle_path, "w", encoding="utf-8") as subtitle_file:
            for i, data in enumerate(all_data):
                subtitle_file.write(f"{i + 1}\n")
                start_time = self.format_time(data.start_time)
                end_time = self.format_time(data.end_time)
                subtitle_file.write(f"{start_time} --> {end_time}\n")
                subtitle_file.write(f"{data.text}\n\n")

        # 按 HTML 格式保存
        # 生成内容
        content = ""
        for idx, data in enumerate(all_data):
            content += (
                f"<span class='segment' data-index='{idx}' data-start-time='{data.start_time:.2f}' data-end-time='{data.end_time:.2f}' data-speaker-index='{data.speaker_index}'>"
                f"{data.text}</span> "
            )

        translation = ""
        for idx, data in enumerate(all_data):
            translation += (
                f"<span class='segment' data-index='{idx}' data-start-time='{data.start_time:.2f}' data-end-time='{data.end_time:.2f}' data-speaker-index='{data.speaker_index}'>"
                f"{data.translated_text}</span> "
            )

        # 读取 HTML 模板
        template_path = os.path.join(
            os.path.dirname(__file__), "template.html")
        with open(template_path, "r", encoding="utf-8") as template_file:
            template = template_file.read()

        # 替换模板中的占位符
        html_content = template.replace("{{ audio_path }}", "audio.wav")
        html_content = html_content.replace("{{ content }}", content)
        html_content = html_content.replace("{{ translation }}", translation)

        # 保存 HTML 文件
        html_path = save_dir + "/transcription.html"
        with open(html_path, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)

        print(f"Export completed. Files saved in {save_dir}")

    def format_time(self, seconds: float, lrc=False, markdown=False) -> str:
        '''
        格式化时间为字幕文件、LRC 或 markdown 格式
        '''
        minutes = int(seconds // 60)
        seconds = seconds % 60
        if lrc:
            return f"{minutes:02}:{seconds:05.2f}"  # LRC 格式为 mm:ss.xx
        elif markdown:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"{hours:02}:{minutes:02}:{seconds:06.3f}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"{hours:02}:{minutes:02}:{seconds:06.3f}".replace(".", ",")

    def __init__(self):
        # 先运行一次，导入模型
        print(f"load whisper model {self.model_name}...")
        mlx_whisper.transcribe(
            np.zeros(1024), path_or_hf_repo=self.model_name)
        # 初始化翻译
        if cfg.OnlineTranslation:
            # 联网翻译
            print("init online translator...")
            self.OnlineTranslator = Translator(
                from_lang=cfg.TranslateFrom, to_lang=cfg.TranslateTo)
        else:
            # 本地翻译
            print("init local translator...")
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            package_to_install = next(
                filter(
                    lambda x: x.from_code == cfg.TranslateFrom and x.to_code == cfg.TranslateTo, available_packages
                )
            )
            argostranslate.package.install_from_path(
                package_to_install.download())
        # 初始化声纹识别
        print("init speech recognition...")
        self.speech_recognition = glimmer_speech_recognition.SpeechRecognition()
        # 获取所有的输入设备
        self.device_map = {}
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                device_str = f"Device {i}: {info['name']} - Input Channels: {info['maxInputChannels']}"
                self.device_map[device_str] = i

    def stop(self):
        self.lock.acquire()
        if not self.running:
            raise Exception("not running")
        self.running = False
        self.lock.release()
        self.listen_thread.join()
        # self.handle_thread.join()
        print("stopped")

    def start(self):
        global cfg
        self.lock.acquire()
        if self.running:
            raise Exception("already running")
        self.running = True
        self.lock.release()
        # 开始之前重新读取设置
        cfg = app_config.get()
        self.start_listen()
        self.start_handle()
        print("started")

    def set_update_hook(self, update_hook):
        self.update_hook = update_hook

    def get_input_devices(self) -> list[str]:
        all_devices = []
        for k, _ in self.device_map.items():
            all_devices.append(k)
        return all_devices

    def get_selected_input_device_id(self) -> int:
        if cfg.InputDevice in self.device_map:
            return self.device_map[cfg.InputDevice]
        return -1


if __name__ == "__main__":
    rs = RealtimeSubtitle()
