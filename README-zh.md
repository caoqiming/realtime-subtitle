# 实时字幕

一款离线实时字幕程序，基于 whisper 实现。支持 m 系列的 mac。

> windows 想用也很简单，把 mlx_whisper 换成 whisper 就行了。~~但我懒得改了，毕竟我的 windows 只用来打游戏。~~

## 安装说明

### 前置条件

#### 安装 portaudio

安装 portaudio，因实时字幕依赖这个包

```bash
brew install portaudio
```

如果提示没有 brew 命令的话，先安装一下

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### python>=3.9

使用 conda 创建虚拟环境（可选）
如果你还没有 conda，参考 minicanda 的[官网](https://www.anaconda.com/docs/getting-started/miniconda/install#macos-linux-installation)进行安装。

```bash
conda create -n subtitle python=3.9
```

### 安装

```bash
pip install realtime-subtitle
```

## 使用说明

```bash
# 启动用户界面
realtime-subtitle ui

# to parse a wav file
realtime-subtitle parse -f {your_wav_file_path}
```

如果提示没有 realtime-subtitle 命令，请检查是否激活了安装时使用的 conda 环境。如果没有激活，请先运行`conda activate subtitle`

## 常见问题

1. 安装完成，启动程序时报错 `LocalEntryNotFoundError: An error happened while trying to locate the file on the Hub and we cannot find the requested files in the local cache.`
   一般是因为网络问题，请尝试科学上网（开启全局模式），或者使用镜像源

2. 程序启动慢（除第一次以外）。
   可能是网络问题导致的。因为 mlx_whisper 会联网检查索引。解决方案有两个，科学上网，或者在启动程序时暂时把 wifi 关了。

3. 字幕抽风，乱输出。
   这个是 whisper 的问题，在没人说话时或者噪音太大时就会抽风。别被吓到就行。~~后续版本或许会加个音量阈值来过滤部分抽风的问题，但不一定能完全解决。~~
