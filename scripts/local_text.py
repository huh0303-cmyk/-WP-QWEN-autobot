#!/usr/bin/env python3
"""Zero-cost local text fallback through Ollama on the Korea365 VPS."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

_OLLAMA_TGZ = "https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst"
_bootstrapped = False


def _reachable() -> bool:
    try:
        return requests.get(OLLAMA_URL + "/api/tags", timeout=3).status_code == 200
    except requests.RequestException:
        return False


def ensure_runner_ollama(download=None, run=None, pull_timeout: int = 900) -> bool:
    """GitHub 러너에는 Ollama가 없다. 마지막 수단(무료 로컬 Qwen)이 실제로 필요해진 순간에만
    공식 릴리스 바이너리를 받아 기동하고 모델을 pull 한다(평소 실행엔 비용·시간 0).
    RUNNER_OLLAMA_BOOTSTRAP=true 일 때만 동작."""
    global _bootstrapped
    if _reachable():
        return True
    if os.environ.get("RUNNER_OLLAMA_BOOTSTRAP", "").lower() not in {"1", "true", "yes", "on"} or _bootstrapped:
        return False
    _bootstrapped = True
    home = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "ollama-runner"
    home.mkdir(parents=True, exist_ok=True)
    tgz = home / "ollama.tar.zst"
    if download is None:
        def download():
            with requests.get(_OLLAMA_TGZ, stream=True, timeout=120) as r:
                r.raise_for_status()
                with tgz.open("wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
    download()
    try:
        subprocess.run(["tar", "--zstd", "-xf", str(tgz), "-C", str(home)], check=True, timeout=300)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # zstd CLI가 없는 러너: 파이썬 zstandard 로 풀기
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "zstandard"], check=True, timeout=300)
        import io, tarfile, zstandard
        with tgz.open("rb") as fh, zstandard.ZstdDecompressor().stream_reader(fh) as rd:
            with tarfile.open(fileobj=rd, mode="r|") as t:
                t.extractall(home, filter="data")
    binary = home / "bin" / "ollama"
    if run is None:
        run = subprocess.Popen
    run([str(binary), "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if _reachable():
            break
        time.sleep(1.5)
    else:
        return False
    subprocess.run([str(binary), "pull", OLLAMA_MODEL], check=True, timeout=pull_timeout)
    return True


def local_generate_text(
    prompt: str,
    *,
    temperature: float = 0.6,
    timeout: int = 75,
    max_tokens: int = 1800,
) -> str:
    ensure_runner_ollama()
    response = requests.post(
        OLLAMA_URL + "/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "5m",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        },
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Ollama unavailable: HTTP {response.status_code}")
    text = str(response.json().get("response", "")).strip()
    if not text:
        raise RuntimeError("Ollama returned empty text")
    return text
