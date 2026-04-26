from fastapi import APIRouter
from pydantic import BaseModel
import structlog

from app.services.intent_parser import ParsedCommand, intent_parser
from app.services.gemini import parse_with_gemini, summarize_page

router = APIRouter()
logger = structlog.get_logger()


class CommandRequest(BaseModel):
    transcript: str
    context: dict | None = None


class CommandResponse(BaseModel):
    success: bool
    intent: str | None = None
    parameters: dict | None = None
    confidence: float | None = None
    error: str | None = None
    strategy: str | None = None
    response: str | None = None


class SummarizeRequest(BaseModel):
    text: str
    url: str = ""
    title: str = ""


class SummarizeResponse(BaseModel):
    success: bool
    summary: str | None = None
    error: str | None = None


def _command_response_from_parsed(parsed: ParsedCommand, strategy: str = "regex") -> CommandResponse:
    return CommandResponse(
        success=True,
        intent=parsed.intent,
        parameters=parsed.parameters,
        confidence=parsed.confidence,
        strategy=strategy,
        response=parsed.response,
    )


@router.post("/commands/parse", response_model=CommandResponse)
async def parse_command(request: CommandRequest):
    """Parse a transcript into a structured command response."""

    logger.info("command_parse_request", transcript=request.transcript)

    # Strategy 1: Local regex parser (fast path)
    parsed = intent_parser.parse(request.transcript)
    if parsed:
        logger.info("command_parse_regex_match", intent=parsed.intent)
        return _command_response_from_parsed(parsed, strategy="regex")

    # Strategy 2: Gemini AI fallback
    logger.info("command_parse_regex_miss_trying_gemini", transcript=request.transcript)
    gemini_result = await parse_with_gemini(request.transcript, request.context)
    if gemini_result:
        logger.info("command_parse_gemini_match", intent=gemini_result.intent)
        return _command_response_from_parsed(gemini_result, strategy="gemini")

    # Both strategies failed
    logger.warning(
        "command_parse_no_match",
        transcript=request.transcript,
    )
    return CommandResponse(
        success=False,
        confidence=0.0,
        error="Could not understand that command. Try rephrasing.",
        strategy="none",
    )


@router.post("/commands/summarize", response_model=SummarizeResponse)
async def summarize_command(request: SummarizeRequest):
    """Summarize web page content using Gemini AI."""

    logger.info("summarize_request", url=request.url, text_length=len(request.text))

    summary = await summarize_page(
        text=request.text,
        url=request.url,
        title=request.title,
    )

    if summary:
        return SummarizeResponse(success=True, summary=summary)

    return SummarizeResponse(
        success=False,
        error="Summarization unavailable. Gemini API may not be configured.",
    )
