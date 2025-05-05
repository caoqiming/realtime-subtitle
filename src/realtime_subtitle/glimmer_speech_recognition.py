from realtime_subtitle.common import *
import numpy as np
from sklearn.preprocessing import normalize
from speechbrain.inference.speaker import SpeakerRecognition
import os
import torch
from realtime_subtitle import app_config
cfg = app_config.get()


class SpeechRecognition:
    def __init__(self):
        self.recognizer = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=os.path.expanduser(
                "~/.cache/speechbrain/spkrec-ecapa-voxceleb"),
        )

    def get_embed(self, current_buffer: bytes) -> np.ndarray:
        # 将音频数据从 bytes 转换为 numpy 数组
        audio_np = np.frombuffer(
            current_buffer, dtype=np.int16).astype(np.float32) / 32768.0

        # 转换为 torch.Tensor，并添加 batch 维度
        audio_tensor = torch.tensor(audio_np).unsqueeze(
            0)  # shape: (1, num_samples)

        # 使用 recognizer 提取嵌入
        embed = self.recognizer.encode_batch(audio_tensor)
        # 转换为 numpy 数组并移除 batch 维度
        embed_np = embed.squeeze(0).detach().numpy()

        # 归一化为单位向量
        normalized_embed = normalize(embed_np.reshape(1, -1), norm='l2')[0]
        return normalized_embed

    def fit_predict(self,
                    subtitles: list[SubtitleData],
                    audio: bytes,
                    speaker_num: int = -1):
        if len(subtitles) == 0:
            return

        embeds = []  # 用于存储所有的 embed 向量

        for one in subtitles:
            # 提取每段字幕对应的音频片段
            temp_audio = audio[convert_time_to_index(
                one.start_time):convert_time_to_index(one.end_time)]
            embed = self.get_embed(temp_audio)
            embeds.append(embed)  # 将 embed 添加到列表中

        embed_matrix = np.vstack(embeds)
        if speaker_num > 0:
            # 如果指定了说话人数量，则使用 k-means 聚类
            print("use k-means")
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=speaker_num)
            kmeans.fit(embed_matrix)
            speaker_index_list = kmeans.predict(embed_matrix)
        else:
            # 如果没有指定了说话人数量，则使用 DBSCAN 聚类
            print("use DBSCAN")
            from sklearn.cluster import DBSCAN
            dbscan = DBSCAN(eps=cfg.DbscanEps, min_samples=1)
            speaker_index_list = dbscan.fit_predict(embed_matrix)
        for i in range(0, len(subtitles)):
            subtitles[i].speaker_index = speaker_index_list[i]
