import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MSG_LENGTH = 4096


def _split_message(text: str) -> list[str]:
    """Splits a message into chunks under Telegram's 4096 char limit."""
    if len(text) <= MAX_MSG_LENGTH:
        return [text]

    chunks = []
    while len(text) > MAX_MSG_LENGTH:
        split_at = text.rfind("\n", 0, MAX_MSG_LENGTH)
        if split_at == -1:
            split_at = MAX_MSG_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def _send_message(token: str, chat_id: str, text: str) -> None:
    """Sends a single message via Telegram Bot API. Raises on HTTP error."""
    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()


def send_digest(
    digest_path: str | None,
    bot_token: str = None,
    chat_id: str = None
) -> dict:
    """
    Sends the aggregated digest to Telegram.
    Returns result dict with success, messages_sent, error.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not cid:
        raise ValueError(
            "Telegram credentials missing. "
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."
        )

    date_str = datetime.now().strftime("%Y-%m-%d")
    header = f"🤖 *Career-Ops Agent — {date_str}*\n\n"

    # No new jobs case
    if not digest_path or not os.path.exists(str(digest_path)):
        logger.info("No digest file found — sending empty notification")
        try:
            _send_message(token, cid, header + "No new jobs found in today's scan.")
            return {"success": True, "messages_sent": 1, "error": ""}
        except requests.HTTPError as e:
            raise RuntimeError(f"Telegram API error: {e}")

    with open(digest_path, "r", encoding="utf-8") as f:
        content = f.read()

    full_message = header + content
    chunks = _split_message(full_message)

    try:
        for chunk in chunks:
            _send_message(token, cid, chunk)
        logger.info(f"Digest sent via Telegram ({len(chunks)} message(s))")
        return {
            "success": True,
            "messages_sent": len(chunks),
            "error": ""
        }

    except requests.HTTPError as e:
        error_msg = f"Telegram API error: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)