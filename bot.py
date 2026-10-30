
import os
import logging
import asyncio
import tempfile
from pathlib import Path

import fal_client
from telegram import Update
from telegram.ext import (
Application,
CommandHandler,
MessageHandler,
ContextTypes,
filters,
)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
FAL_KEY = os.environ["FAL_KEY"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"Welcome to Kdollarbot AI Video! 🎬\n\n"
"Send me a photo to animate it into a video.\n"
"Please use images you have permission to use."
)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
message = update.message
status = await message.reply_text(
"Your photo was received. Preparing your video request..."
)

photo = message.photo[-1]
telegram_file = await context.bot.get_file(photo.file_id)

with tempfile.TemporaryDirectory() as temp_dir:
    image_path = Path(temp_dir) / "photo.jpg"
    await telegram_file.download_to_drive(custom_path=str(image_path))

    try:
        await status.edit_text("Uploading your photo for AI animation...")

        image_url = await asyncio.to_thread(
            fal_client.upload_file, str(image_path)
        )

        await status.edit_text("Generating your video. Please wait...")

        result = await asyncio.to_thread(
            fal_client.subscribe,
            "fal-ai/wan/v2.2-a14b/image-to-video",
            arguments={
                "image_url": image_url,
                "prompt": (
                    "Animate this image naturally with gentle movement. "
                    "Preserve the subject's identity and clothing."
                ),
            },
        )

        video_url = result.get("video", {}).get("url")

        if not video_url:
            raise ValueError("The model did not return a video URL.")

        await status.edit_text("Your video is ready. Downloading it...")

        import requests

        response = await asyncio.to_thread(
            requests.get, video_url, timeout=120
        )
        response.raise_for_status()

        video_path = Path(temp_dir) / "generated.mp4"
        video_path.write_bytes(response.content)

        with video_path.open("rb") as video:
            await message.reply_video(
                video=video,
                caption="Your AI-generated video is ready! 🎬",
            )

        await status.delete()

    except Exception:
        logger.exception("Video generation failed")
        await status.edit_text(
            "Sorry, video generation failed. Please try again later."
        )

async def main():
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

logger.info("Kdollarbot is starting")
await app.initialize()
await app.start()
await app.updater.start_polling()
await asyncio.Event().wait()

if name == "main":
asyncio.run(main())
