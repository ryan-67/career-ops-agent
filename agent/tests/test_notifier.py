import pytest
from unittest.mock import patch, MagicMock
from agent.tasks.notifier import send_digest, _split_message


def test_send_digest_with_valid_file(tmp_path):
    digest = tmp_path / "digest-2026-04-23.md"
    digest.write_text("# Digest\n\n| Company | Score |\n|---------|-------|\n| Google | 4.5/5 |")

    with patch("agent.tasks.notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        result = send_digest(
            digest_path=str(digest),
            bot_token="fake-token",
            chat_id="123456"
        )

    assert result["success"] is True
    assert result["messages_sent"] >= 1


def test_send_digest_no_file_sends_empty_message():
    with patch("agent.tasks.notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        result = send_digest(
            digest_path=None,
            bot_token="fake-token",
            chat_id="123456"
        )

    assert result["success"] is True
    assert result["messages_sent"] == 1
    call_args = mock_post.call_args[1]["json"]["text"]
    assert "No new jobs" in call_args


def test_send_digest_splits_long_message(tmp_path):
    digest = tmp_path / "digest-long.md"
    digest.write_text("x" * 9000)

    with patch("agent.tasks.notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        result = send_digest(
            digest_path=str(digest),
            bot_token="fake-token",
            chat_id="123456"
        )

    assert result["messages_sent"] >= 3


def test_send_digest_raises_on_http_error(tmp_path):
    import requests
    digest = tmp_path / "digest.md"
    digest.write_text("# Test")

    with patch("agent.tasks.notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock()
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError("403")

        with pytest.raises(RuntimeError, match="Telegram API error"):
            send_digest(
                digest_path=str(digest),
                bot_token="fake-token",
                chat_id="123456"
            )


def test_split_message_short():
    chunks = _split_message("short message")
    assert len(chunks) == 1


def test_split_message_long():
    chunks = _split_message("a" * 10000)
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk) <= 4096