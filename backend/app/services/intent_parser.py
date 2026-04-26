"""Regex-based intent parser for Goofy voice commands."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import json
import re
from difflib import SequenceMatcher

import structlog

logger = structlog.get_logger()

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "docs" / "intent-schema-v0.json"


@dataclass
class ParsedCommand:
    """Structured command returned by the intent parser."""

    intent: str
    parameters: Dict[str, Any]
    confidence: float
    matched_alias: str
    response: Optional[str] = None


class IntentParser:
    """Parse natural language transcripts into structured system-wide intents."""

    def __init__(self) -> None:
        self.schema = self._load_schema()
        self.intent_patterns = self._build_intent_patterns()

    def _load_schema(self) -> Dict[str, Any]:
        if not SCHEMA_PATH.exists():
            msg = "Intent schema file not found"
            logger.error("intent_schema_missing", path=str(SCHEMA_PATH))
            raise FileNotFoundError(msg)

        with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _build_intent_patterns(self) -> Dict[str, Dict[str, Any]]:
        patterns: Dict[str, Dict[str, Any]] = {}
        for intent in self.schema["intents"]:
            aliases = intent.get("aliases", [])
            compiled_aliases = [self._compile_alias(alias) for alias in aliases]
            patterns[intent["intent"]] = {
                "aliases": aliases,
                "compiled": compiled_aliases,
            }
        return patterns

    @staticmethod
    def _compile_alias(alias: str) -> re.Pattern[str]:
        escaped = re.escape(alias.strip())
        pattern = escaped.replace(r"\ ", r"\s+")
        return re.compile(rf"\b{pattern}\b", re.IGNORECASE)

    def parse(self, transcript: str) -> Optional[ParsedCommand]:
        if not transcript:
            return None

        normalized = transcript.strip().lower()
        logger.debug("intent_parse_attempt", transcript=normalized)

        heuristics = [
            self._match_system_screenshot,
            self._match_system_volume,
            self._match_system_type,
            self._match_system_press,
            self._match_system_open_app,
            self._match_search_google,
            self._match_conversation,
        ]

        for matcher in heuristics:
            result = matcher(normalized, transcript)
            if result:
                logger.debug(
                    "intent_parse_success",
                    intent=result.intent,
                    confidence=result.confidence,
                    alias=result.matched_alias,
                )
                return result

        logger.info("intent_parse_no_match", transcript=normalized)
        return None

    def _match_alias(self, key: str, text: str) -> Optional[str]:
        intent_entry = self.intent_patterns.get(key)
        if not intent_entry:
            return None

        for alias, pattern in zip(intent_entry["aliases"], intent_entry["compiled"]):
            if pattern.search(text):
                return alias
        return None

    def _confidence(self, alias: str, text: str) -> float:
        ratio = SequenceMatcher(None, alias.lower(), text.lower()).ratio()
        return round(max(0.7, min(1.0, ratio + 0.1)), 2)

    def _match_system_screenshot(self, normalized: str, original: str) -> Optional[ParsedCommand]:
        alias = self._match_alias("system.screenshot", normalized)
        # Require "take" or "capture" or a direct command, don't just match any mention of "screenshot"
        if not alias and not re.search(r"\b(take|capture|grab|get|make)\s+(?:a\s+)?screenshot\b", normalized):
            if not (normalized == "screenshot" or normalized == "take screenshot"):
                return None

        return ParsedCommand(
            intent="system.screenshot",
            parameters={},
            confidence=self._confidence(alias or "screenshot", original),
            matched_alias=alias or "screenshot",
            response="Sure, I've captured your screen.",
        )

    def _match_system_volume(self, normalized: str, original: str) -> Optional[ParsedCommand]:
        alias = self._match_alias("system.volume", normalized)
        action: Optional[str] = None
        
        if re.search(r"\b(increase|up|higher|louder)\b", normalized):
            action = "up"
        elif re.search(r"\b(decrease|down|lower|quieter)\b", normalized):
            action = "down"
        elif "mute" in normalized:
            action = "mute"
        elif "unmute" in normalized:
            action = "unmute"

        if not action and not alias:
            return None

        return ParsedCommand(
            intent="system.volume",
            parameters={"action": action or "up"},
            confidence=self._confidence(alias or f"volume {action}", original),
            matched_alias=alias or f"volume {action}",
            response=f"Adjusting volume {action if action else ''}.",
        )

    def _match_system_type(self, normalized: str, original: str) -> Optional[ParsedCommand]:
        alias = self._match_alias("system.type", normalized)
        # Require it to start with the action or have a clear command structure
        if not alias and not re.match(r"^(?:type|write|insert|put)\s+", normalized):
            return None

        # Extract text to type
        match = re.search(r"(?:type|write|insert|put)\s+(.*)", original, re.IGNORECASE)
        text = match.group(1).strip() if match else None
        if not text:
            return None

        return ParsedCommand(
            intent="system.type",
            parameters={"text": text},
            confidence=self._confidence(alias or "type", original),
            matched_alias=alias or "type",
            response=f"Typing: {text}",
        )

    def _match_system_press(self, normalized: str, original: str) -> Optional[ParsedCommand]:
        alias = self._match_alias("system.press", normalized)
        if not alias and not re.match(r"^(?:press|hit|tap)\s+", normalized):
            return None

        match = re.search(r"(?:press|hit|tap)\s+(\w+)", normalized)
        key = match.group(1) if match else None
        if not key:
            return None

        return ParsedCommand(
            intent="system.press",
            parameters={"key": key},
            confidence=self._confidence(alias or "press", original),
            matched_alias=alias or "press",
            response=f"Pressing {key}.",
        )

    def _match_system_open_app(self, normalized: str, original: str) -> Optional[ParsedCommand]:
        alias = self._match_alias("system.open_app", normalized)
        if not alias and not re.match(r"^(?:open|launch|start|run)\s+", normalized):
            return None

        match = re.search(r"(?:open|launch|start|run)\s+(.*)", original, re.IGNORECASE)
        app_name = match.group(1).strip() if match else None
        if not app_name:
            return None

        return ParsedCommand(
            intent="system.open_app",
            parameters={"app_name": app_name},
            confidence=self._confidence(alias or "open", original),
            matched_alias=alias or "open",
            response=f"Opening {app_name}.",
        )

    def _match_search_google(self, normalized: str, original: str) -> Optional[ParsedCommand]:
        alias = self._match_alias("search.google", normalized)
        if not alias and not re.match(r"^(?:search for|search|google|look up)\s+", normalized):
            return None

        match = re.search(r"(?:search for|search|google|look up)\s+(.*)", original, re.IGNORECASE)
        query = match.group(1).strip() if match else None
        if not query:
            return None

        return ParsedCommand(
            intent="search.google",
            parameters={"query": query},
            confidence=self._confidence(alias or "search", original),
            matched_alias=alias or "search",
            response=f"Searching Google for {query}.",
        )

    def _match_conversation(self, normalized: str, original: str) -> Optional[ParsedCommand]:
        alias = self._match_alias("conversation.chat", normalized)
        if not alias:
            return None

        return ParsedCommand(
            intent="conversation.chat",
            parameters={},
            confidence=self._confidence(alias, original),
            matched_alias=alias,
            response="Hello! I'm Goofy, your system assistant. How can I help?",
        )


intent_parser = IntentParser()

__all__ = ["intent_parser", "ParsedCommand"]

