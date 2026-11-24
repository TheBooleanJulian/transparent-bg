"""
Background Removal Telegram Bot
--------------------------------
Accepts photos (uploaded directly, sent as files, or forwarded) and
returns a PNG with the background removed, subject(s) preserved on
a transparent background.

Follows TheBooleanJulian bot fleet conventions:
- polling (no webhook) for simplicity on Zeabur
- async, python-telegram-bot v21+
- structured logging
- graceful handling of large files / multiple subjects
"""

import io
import logging
import os
from pathlib import Path

from PIL import Image
from rembg import remove, new_session
from telegram import Update, InputFile
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

# u2net = fast, general purpose. isnet-general-use = higher quality, slower.
REMBG_MODEL = os.environ.get("REMBG_MODEL", "u2net")

# Telegram bot API file download cap (bots can't fetch files >20MB via getFile)
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bg-remove-bot")

# rembg session is loaded once and reused across requests (avoids reloading
# the ONNX model on every message).
_session = new_session(REMBG_MODEL)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me a photo (or forward one to me) and I'll send it back "
        "as a transparent PNG with the background removed.\n\n"
        "Tip: send it as a *file/document* instead of a compressed photo "
        "if you want the highest quality result.",
        parse_mode="Markdown",
    )


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat_id = update.effective_chat.id

    # Resolve the incoming file: compressed photo vs. uncompressed document
    tg_file = None
    file_size = None

    if message.photo:
        # Telegram sends multiple resolutions; take the largest.
        photo = message.photo[-1]
        tg_file = photo
        file_size = photo.file_size
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        tg_file = message.document
        file_size = message.document.file_size
    else:
        await message.reply_text("That doesn't look like an image I can process.")
        return

    if file_size and file_size > MAX_FILE_SIZE_BYTES:
        await message.reply_text(
            "That file is too large for me to download (Telegram bot limit is 20MB). "
            "Try sending a smaller or more compressed version."
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
    status_msg = await message.reply_text("Removing background…")

    try:
        file = await tg_file.get_file()
        raw_bytes = bytes(await file.download_as_bytearray())

        input_image = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        output_image = remove(input_image, session=_session)

        buffer = io.BytesIO()
        output_image.save(buffer, format="PNG")
        buffer.seek(0)

        # Sent as a document so Telegram doesn't re-compress it and strip
        # the alpha channel the way it would for send_photo.
        await context.bot.send_document(
            chat_id=chat_id,
            document=InputFile(buffer, filename="no_background.png"),
            caption="Here you go — background removed.",
            reply_to_message_id=message.message_id,
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process image from chat %s", chat_id)
        await message.reply_text(
            "Something went wrong while processing that image. Please try again."
        )
    finally:
        try:
            await status_msg.delete()
        except Exception:  # noqa: BLE001
            pass


async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Send me a photo or an image file and I'll strip the background out for you."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))

    image_filter = filters.PHOTO | (
        filters.Document.IMAGE
    )
    app.add_handler(MessageHandler(image_filter, handle_image))

    app.add_handler(MessageHandler(~image_filter & ~filters.COMMAND, handle_unsupported))

    logger.info("Bot starting with model=%s (polling mode)", REMBG_MODEL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
