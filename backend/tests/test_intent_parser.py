import pytest
from app.services.intent_parser import intent_parser

def test_screenshot_intent_true_positives():
    commands = [
        "goofy take a screenshot",
        "capture a screenshot of my screen",
        "make a screenshot right now",
        "grab a screenshot for me"
    ]
    for cmd in commands:
        parsed = intent_parser.parse(cmd)
        assert parsed is not None
        assert parsed.intent == "system.screenshot"

def test_screenshot_intent_false_positives():
    commands = [
        "i took a screenshot yesterday",
        "can you show me my screenshot folder",
        "the screenshot looks blurry"
    ]
    for cmd in commands:
        parsed = intent_parser.parse(cmd)
        # Should either be None or NOT system.screenshot (likely None for regex)
        if parsed:
            assert parsed.intent != "system.screenshot"

def test_volume_intent():
    parsed_up = intent_parser.parse("goofy increase the volume")
    assert parsed_up is not None
    assert parsed_up.intent == "system.volume"
    assert parsed_up.parameters["action"] == "up"

    parsed_down = intent_parser.parse("decrease volume please")
    assert parsed_down is not None
    assert parsed_down.intent == "system.volume"
    assert parsed_down.parameters["action"] == "down"

def test_type_intent():
    parsed = intent_parser.parse("type hello world")
    assert parsed is not None
    assert parsed.intent == "system.type"
    assert parsed.parameters["text"] == "hello world"

def test_open_app_intent():
    parsed = intent_parser.parse("open notepad")
    assert parsed is not None
    assert parsed.intent == "system.open_app"
    assert parsed.parameters["app_name"] == "notepad"

    # Testing false positive prevention (should start with the verb)
    parsed_false = intent_parser.parse("i want to keep the window open")
    if parsed_false:
        assert parsed_false.intent != "system.open_app"

def test_media_intent():
    parsed_play = intent_parser.parse("goofy play the music")
    assert parsed_play is not None
    assert parsed_play.intent == "system.media"
    assert parsed_play.parameters["action"] == "playpause"

    parsed_next = intent_parser.parse("next track please")
    assert parsed_next is not None
    assert parsed_next.intent == "system.media"
    assert parsed_next.parameters["action"] == "nexttrack"
