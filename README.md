# realtime subtitle

This is an offline realtime subtitle program for M-series mac.

## install

require python >=3.9

```bash
# install dependencies
# if you don't have brew, install it from https://brew.sh/
brew install portaudio
# install realtime-subtitle via pip
pip install realtime-subtitle
```

## usage

```bash
# to run with a ui
realtime-subtitle ui

# to parse a wav file
realtime-subtitle parse -f {your_wav_file_path}
```

you can find more whisper models [here](https://huggingface.co/collections/mlx-community/whisper-663256f9964fbb1177db93dc)
