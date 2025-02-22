## Server

### Requirements:

- ffmpeg
- Microsoft C++ Build Tools

### Set up:

```shell
# Using conda
conda create --name live-translate python=3.11
conda activate live-translate
cd server
pip install -r requirements.txt
```

### Installing CUDA:

You can run this app using CPU, but it will use a much smaller and less accurate whisper model and run slower.
Download the latest version of CUDA from [here](https://developer.nvidia.com/cuda-downloads).

```shell
conda uninstall pytorch torchaudio # Remove existing pytorch and torchaudio
conda install pytorch torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```

### Running:

```shell
python app.py
```

## Client

```shell
cd app
npm install
npm start
```
