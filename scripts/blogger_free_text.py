"""Blogger compatibility entrypoints: approved Gemini six-stage policy only."""
from __future__ import annotations
from gemini_text import gemini_generate_text

def free_blogger_generate_text(prompt: str, *, temperature: float = 0.5, language: str | None = None) -> str:
    return gemini_generate_text(prompt, temperature=temperature, language=language)

def blogger_generate_with_fallback(prompt: str, *, temperature: float = 0.5, tries: int = 2, language: str | None = None) -> str:
    return free_blogger_generate_text(prompt, temperature=temperature, language=language)
