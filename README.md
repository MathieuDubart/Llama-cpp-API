# Llama.cpp API

## Prerequisites

- Setup [Tailscale](https://tailscale.com/) on your devices
- Git clone G. Gerganov's Llama.cpp from [his Github repository](https://github.com/ggerganov/llama.cpp)
- Download a .gguf model (mistral-7b-instruct-v0.2.Q4_K_M.gguf is recommended)
- Place it inside ./models

## Starting project

- Git clone this repository inside Llama.cpp one's `git clone git@github.com:MathieuDubart/Llama-cpp-api.git`
- Open `server.py` and change model path to match with your model name
- Run `python3 server.py` in root directory
- You can now access your API routes on every linked to Tailscale device, with your hosting device's Tailscale IP (Port 5000)) (e.g: `100.x.x.x:5000/generate`)
