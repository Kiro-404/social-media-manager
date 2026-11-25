"""
Turns a (Niche, TrendSignal) pair into a concrete ContentIdea: a title, the
narrative angle tying the trend to the niche, a ready-to-record script, a
caption, and hashtags — all in one LLM call, returned as JSON and persisted.
"""
from __future__ import annotations

import json
import re

from loguru import logger
from sqlalchemy.orm import Session

from app.ideation.llm_client import LLMClient, get_llm_client
from app.models import ContentIdea, Niche, TrendSignal

_PROMPT_TEMPLATE = """You are a senior short-form social media content strategist.

Niche / channel context:
- Name: {niche_name}
- Description: {niche_description}
- Target audience: {target_audience}
- Tone of voice: {tone_of_voice}
- Content language: {language}

Trending topic to react to:
- Keyword/topic: {trend_keyword}
- Source: {trend_source}

Task: invent ONE short-form content idea (for Reels/Shorts/TikTok, 30-60s)
that genuinely connects this trending topic to the niche above — not a
generic mention of the trend, but a real, specific angle a creator in this
niche would actually post.

Respond with ONLY a valid JSON object (no markdown fences, no commentary),
using exactly these keys:
{{
  "title": "short punchy working title",
  "angle": "1-2 sentences explaining why this angle connects the trend to the niche",
  "script": "a full spoken script/voiceover for the video, written in {language}, 80-150 words, in the specified tone of voice",
  "caption": "a ready-to-post caption in {language}, including 1-2 emoji if natural, no hashtags here",
  "hashtags": "5-8 relevant hashtags separated by spaces, no commentary"
}}
"""


def _build_prompt(niche: Niche, trend: TrendSignal | None) -> str:
    return _PROMPT_TEMPLATE.format(
        niche_name=niche.name,
        niche_description=niche.description or "(not provided)",
        target_audience=niche.target_audience or "(not provided)",
        tone_of_voice=niche.tone_of_voice or "friendly and energetic",
        language=niche.language,
        trend_keyword=trend.keyword if trend else "(no specific trend — invent a timely, plausible one)",
        trend_source=trend.source if trend else "none",
    )


def _parse_llm_json(raw_text: str) -> dict:
    """
    LLMs occasionally wrap JSON in markdown fences or add stray text.
    Extract the first {...} block and parse it; raise a clear error if
    nothing parseable is found so the caller can retry or surface it.
    """
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {raw_text[:300]!r}")
    return json.loads(match.group(0))


def generate_idea(
    db: Session,
    niche: Niche,
    trend: TrendSignal | None = None,
    llm: LLMClient | None = None,
) -> ContentIdea:
    llm = llm or get_llm_client()
    prompt = _build_prompt(niche, trend)

    raw_text = llm.generate(prompt, temperature=0.85)
    try:
        parsed = _parse_llm_json(raw_text)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error(f"[idea_generator] failed to parse LLM output: {exc}")
        raise

    idea = ContentIdea(
        niche_id=niche.id,
        trend_signal_id=trend.id if trend else None,
        title=parsed.get("title", "").strip(),
        angle=parsed.get("angle", "").strip(),
        script=parsed.get("script", "").strip(),
        caption=parsed.get("caption", "").strip(),
        hashtags=parsed.get("hashtags", "").strip(),
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea
