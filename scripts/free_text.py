#!/usr/bin/env python3
"""Zero-cost-only text generation for Blogger33.

Uses Hugging Face Inference Providers with provider=publicai.
No paid fallback is permitted. If unavailable, fail closed.
"""
from __future__ import annotations
import json, os, requests

API="https://router.huggingface.co/v1/chat/completions"
MODEL=os.environ.get("BLOGGER_FREE_TEXT_MODEL","swiss-ai/Apertus-70B-Instruct-2509:publicai")

def free_generate_text(prompt:str, *, temperature:float=0.5)->str:
    token=os.environ.get("HF_TOKEN","").strip()
    if not token:
        raise RuntimeError("ZERO_COST_HOLD: HF_TOKEN missing; paid fallback forbidden")
    r=requests.post(API,headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},
        json={"model":MODEL,"messages":[{"role":"user","content":prompt}],"temperature":temperature},timeout=120)
    if r.status_code>=400:
        raise RuntimeError(f"ZERO_COST_HOLD: free text provider unavailable ({r.status_code}); paid fallback forbidden")
    data=r.json()
    text=data["choices"][0]["message"]["content"].strip()
    if not text:
        raise RuntimeError("ZERO_COST_HOLD: empty free-provider response")
    return text
