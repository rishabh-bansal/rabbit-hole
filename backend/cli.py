"""Run one lane from the terminal: python cli.py <lane> "<start>" "<target>"."""
import asyncio, os, sys, time
from dotenv import load_dotenv
load_dotenv("../.env")
from race import Lane, run_lane
from wiki import Wiki

LANES = {
    "qwen": Lane("cerebras", "Qwen on Cerebras (test)", "https://api.cerebras.ai/v1", os.environ.get("CEREBRAS_API_KEY", ""), "qwen-3.8-27b"),
    "kimi": Lane("cerebras", "Kimi K3.1 Pro on Cerebras", "https://api.cerebras.ai/v1", os.environ.get("CEREBRAS_API_KEY", ""), "moonshotai-kimi-k3.1-pro-trial", {"reasoning_effort": "low"}),
    "nvidia": Lane("gpu", "Kimi K3.1 Pro on NVIDIA GPUs", "https://integrate.api.nvidia.com/v1", os.environ.get("NVIDIA_API_KEY", ""), "moonshotai/kimi-k3.1-pro", {"reasoning_effort": "low"}),
}

async def main():
    lane = LANES[sys.argv[1]]
    w = Wiki()
    async def emit(e):
        t = e.get("t")
        print(f"[{t:6.1f}s] " if isinstance(t, (int, float)) else "         ", {k: v for k, v in e.items() if k not in ("lane", "summary", "t")}, flush=True)
    await run_lane(lane, w, sys.argv[2], sys.argv[3], emit)
    await w.close()

asyncio.run(main())
