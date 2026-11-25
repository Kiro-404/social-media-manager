import pytest

from app.ideation.idea_generator import _parse_llm_json, generate_idea
from app.models import Niche


class FakeLLM:
    """A stand-in LLMClient that returns a fixed, valid JSON payload."""

    def generate(self, prompt: str, *, temperature: float = 0.8) -> str:
        return """```json
        {
          "title": "Why your 9-to-5 routine is secretly a trend",
          "angle": "Connects the viral 'day in my life' trend to productivity content.",
          "script": "This is a short test script for the generated idea.",
          "caption": "Here's how I actually spend my day 👀",
          "hashtags": "#productivity #dayinmylife #routine"
        }
        ```"""


def test_parse_llm_json_strips_markdown_fences():
    raw = '```json\n{"a": 1, "b": "two"}\n```'
    parsed = _parse_llm_json(raw)
    assert parsed == {"a": 1, "b": "two"}


def test_parse_llm_json_raises_on_garbage():
    with pytest.raises(ValueError):
        _parse_llm_json("no json here at all")


def test_generate_idea_persists_row(db_session):
    niche = Niche(name="Productivity", description="Tips for remote workers", language="en")
    db_session.add(niche)
    db_session.commit()
    db_session.refresh(niche)

    idea = generate_idea(db_session, niche=niche, trend=None, llm=FakeLLM())

    assert idea.id is not None
    assert idea.niche_id == niche.id
    assert "9-to-5" in idea.title
    assert idea.hashtags.startswith("#productivity")
