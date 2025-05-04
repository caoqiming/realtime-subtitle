import json
import wave
import pyaudio
import argparse

with open('/Users/glimmer/Documents/code/playground/glimmer-whisper/data/archived.json', 'r') as file:
    archived = json.load(file)


def play_wav_segment(wav_file, start_time, end_time):
    """
    播放 WAV 文件的指定片段。

    Args:
        wav_file (str): WAV 文件的路径。
        start_time (float): 开始播放的时间，单位为秒。
        end_time (float): 结束播放的时间，单位为秒。
    """

    try:
        wf = wave.open(wav_file, 'rb')
    except wave.Error as e:
        print(f"Error opening WAV file: {e}")
        return

    p = pyaudio.PyAudio()

    # 获取 WAV 文件的参数
    channels = wf.getnchannels()
    rate = wf.getframerate()
    format = p.get_format_from_width(wf.getsampwidth())

    stream = p.open(format=format,
                    channels=channels,
                    rate=rate,
                    output=True)

    # 计算起始和结束的帧数
    start_frame = int(start_time * rate)
    end_frame = int(end_time * rate)

    # 移动到起始位置
    wf.setpos(start_frame)

    # 读取并播放指定片段
    data = wf.readframes(end_frame - start_frame)
    stream.write(data)

    # 关闭流和文件
    stream.stop_stream()
    stream.close()
    p.terminate()
    wf.close()


if __name__ == '__main__':
    # 示例用法
    # 替换为你的 WAV 文件路径
    wav_file = '/Users/glimmer/Documents/code/playground/glimmer-whisper/data/output.wav'
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default=0, help="index", type=int)
    index = parser.parse_args().index
    print("总共", len(archived))
    print(archived[index])
    play_wav_segment(
        wav_file, archived[index]['start_time'], archived[index]['end_time'])
