"""Gemini AI service for intent parsing fallback and page summarization."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import structlog

from app.config import settings
from app.services.intent_parser import ParsedCommand

logger = structlog.get_logger()

# Lazy-initialized Gemini model
_model = None


def _get_model():
    """Lazily initialize and cache the Gemini generative model."""
    global _model
    if _model is not None:
        return _model

    if not settings.GEMINI_API_KEY:
        logger.warning("gemini_not_configured", message="GEMINI_API_KEY not set")
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel(settings.GEMINI_MODEL)
        logger.info("gemini_initialized", model=settings.GEMINI_MODEL)
        return _model
    except Exception as exc:
        logger.error("gemini_initialization_failed", error=str(exc))
        return None


INTENT_PARSE_PROMPT = """You are Goofy, an AI voice assistant for the Windows desktop. Parse the user's voice command into a structured intent.

Available intents and their parameters:
- system.open_app: Open a desktop application. Parameters: app_name (string)
- system.screenshot: Take a full screen screenshot. No parameters.
- system.type: Type text into the active window. Parameters: text (string)
- system.press: Press a specific keyboard key. Parameters: key (string, e.g., 'enter', 'win', 'space')
- system.volume: Adjust system volume. Parameters: action ('up', 'down', 'mute')
- search.google: Search google using the default browser. Parameters: query (string)
- system.run_powershell: Execute an arbitrary powershell script or command to accomplish complex system tasks (e.g., list files, manage processes, fetch data, change settings). You can do literally any OS automation via powershell. Parameters: script (string)
- conversation.chat: General conversational response for when the user is just chatting, asking a question, or saying hello. No parameters.

Respond with ONLY a JSON object (no markdown, no code fences):
{{"intent": "<intent_name>", "parameters": {{...}}, "confidence": <0.0-1.0>, "response": "<Conversational response acknowledging the action or answering the user like Siri would. Keep it brief.>"}}

If you cannot determine the intent, respond with:
{{"intent": "conversation.chat", "parameters": {{}}, "confidence": 0.5, "response": "Sorry, I couldn't understand that command."}}

User command: "{transcript}"
"""

SUMMARIZE_PROMPT = """Summarize the following web page content concisely in 3-5 bullet points.
Focus on the key information and main topics.
Keep each bullet point to one sentence.

Page URL: {url}
Page Title: {title}

Content:
{text}
"""


async def parse_with_gemini(
    transcript: str, context: Optional[Dict[str, Any]] = None
) -> Optional[ParsedCommand]:
    """
    Use Gemini to parse a voice transcript into a structured command.
    Returns ParsedCommand on success, None on failure or if Gemini is not configured.
    """
    model = _get_model()
    if model is None:
        return None

    try:
        prompt = INTENT_PARSE_PROMPT.format(transcript=transcript)
        response = await model.generate_content_async(prompt)

        if not response or not response.text:
            logger.warning("gemini_parse_empty_response", transcript=transcript)
            return None

        raw_text = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)

        parsed = json.loads(raw_text)

        intent = parsed.get("intent")
        if not intent:
            logger.info("gemini_parse_no_intent", transcript=transcript)
            return None

        confidence = float(parsed.get("confidence", 0.7))
        parameters = parsed.get("parameters", {})
        response_msg = parsed.get("response", "Done.")

        logger.info(
            "gemini_parse_success",
            intent=intent,
            confidence=confidence,
            transcript=transcript,
        )

        return ParsedCommand(
            intent=intent,
            parameters=parameters,
            confidence=confidence,
            matched_alias="gemini",
            response=response_msg,
        )

    except json.JSONDecodeError as exc:
        logger.error("gemini_parse_json_error", error=str(exc), transcript=transcript)
        return None
    except Exception as exc:
        logger.error("gemini_parse_failed", error=str(exc), transcript=transcript)
        return None


async def summarize_page(
    text: str, url: str = "", title: str = ""
) -> Optional[str]:
    """
    Use Gemini to summarize a web page's content.
    Returns the summary string on success, None on failure.
    """
    model = _get_model()
    if model is None:
        return None

    if not text or not text.strip():
        return None

    try:
        # Truncate to ~8000 chars to stay within token limits
        truncated = text[:8000]
        prompt = SUMMARIZE_PROMPT.format(url=url, title=title, text=truncated)

        response = await model.generate_content_async(prompt)

        if not response or not response.text:
            logger.warning("gemini_summarize_empty_response", url=url)
            return None

        summary = response.text.strip()
        logger.info("gemini_summarize_success", url=url, length=len(summary))
        return summary

    except Exception as exc:
        logger.error("gemini_summarize_failed", error=str(exc), url=url)
        return None


def is_configured() -> bool:
    """Check if the Gemini API is configured and ready."""
    return bool(settings.GEMINI_API_KEY)
