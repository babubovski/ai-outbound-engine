import pytest

from ai_outbound_engine.sanitize import clean, limit_words, remove_dashes

EM, EN = "\u2014", "\u2013"


@pytest.mark.parametrize(
    "raw, expected",
    [
        (f"Saw your launch {EM} congrats on the traction.", "Saw your launch, congrats on the traction."),
        (f"Saw your launch{EM}congrats.", "Saw your launch, congrats."),
        (f"Saw your launch {EM} Congrats to the team.", "Saw your launch. Congrats to the team."),
        (f"Quick one {EN} are you the right person?", "Quick one, are you the right person?"),
        ("Fast -- and cheap.", "Fast, and cheap."),
        (f"We grew 2020{EN}2024.", "We grew 2020-2024."),
        (f"Worth a chat {EM}", "Worth a chat."),
        (f"Thanks, {EM} Max", "Thanks. Max"),
        (f"Worth a chat {EM}\n\nMax", "Worth a chat.\n\nMax"),
        (f"Talk soon,\n{EM} Max", "Talk soon,\nMax"),
    ],
)
def test_remove_dashes(raw, expected):
    assert remove_dashes(raw) == expected


def test_clean_never_leaves_dash_glyphs():
    text = f"A {EM} b {EN} c \u2015 d{EM}{EM}e"
    assert not set(clean(text)) & {EM, EN, "\u2015"}


def test_clean_strips_markdown_and_keeps_paragraphs():
    assert clean("**Hi Ada,**\n\n\n\n- one point\n## Header") == "Hi Ada,\n\none point\nHeader"


def test_limit_words_prefers_sentence_boundary():
    text = "One two three. Four five six seven. Eight nine ten eleven twelve."
    assert limit_words(text, 9) == "One two three. Four five six seven."


def test_limit_words_hard_cut_adds_period():
    assert limit_words("one two three four five six", 4) == "one two three four."


def test_limit_words_noop_when_short():
    assert limit_words("short text", 50) == "short text"
