#!/usr/bin/env python3
"""명령을 타임아웃+재시도(지수 백오프)로 실행. 사용: retry_run.py [--attempts 3] [--timeout 900] -- cmd ...
발행 이중 방지: 성공(exit 0)이면 즉시 종료. 모든 시도 실패 시 마지막 exit code 반환."""
import argparse, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--attempts", type=int, default=3)
ap.add_argument("--timeout", type=int, default=900)
ap.add_argument("--backoff", type=int, default=30)
ap.add_argument("cmd", nargs=argparse.REMAINDER)
a = ap.parse_args()
cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
code = 1
for i in range(1, a.attempts + 1):
    print(f"[retry_run] attempt {i}/{a.attempts}: {' '.join(cmd)}", flush=True)
    try:
        code = subprocess.run(cmd, timeout=a.timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"[retry_run] timeout after {a.timeout}s", flush=True)
        code = 124
    if code == 0:
        sys.exit(0)
    if i < a.attempts:
        wait = a.backoff * (2 ** (i - 1))
        print(f"[retry_run] exit {code}; retry in {wait}s", flush=True)
        time.sleep(wait)
print(f"[retry_run] all attempts failed (exit {code})", flush=True)
sys.exit(code)
