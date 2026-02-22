import pytest
from core.models import Message, UserContext

def test_message_creation_defaults():
    msg = Message(user_id=123, chat_id=456)
    assert msg.user_id == 123
    assert msg.chat_id == 456
    assert msg.text == ""
    assert msg.images == []
    assert msg.audio_text == ""
    assert msg.is_group is False
    assert msg.channel == "telegram"
    assert msg.bot_mentioned is False
    assert msg.caption == ""

def test_message_creation_with_values():
    msg = Message(
        user_id=123,
        chat_id=456,
        text="Hello",
        images=[b"fake_image"],
        audio_text="Audio",
        is_group=True,
        channel="whatsapp",
        bot_mentioned=True,
        caption="A picture"
    )
    assert msg.text == "Hello"
    assert msg.images == [b"fake_image"]
    assert msg.is_group is True
    assert msg.channel == "whatsapp"
    assert msg.bot_mentioned is True

def test_user_context_defaults():
    ctx = UserContext()
    assert ctx.humor == "sarcástico"
    assert ctx.idioma is None

def test_user_context_with_values():
    ctx = UserContext(humor="feliz", idioma="es")
    assert ctx.humor == "feliz"
    assert ctx.idioma == "es"
