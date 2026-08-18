"""
ربات تلگرامی دانلود از SoundCloud - فقط برای استفاده شخصی
این نسخه برای دیپلوی روی Railway آماده شده و توکن/آیدی رو از
متغیرهای محیطی BOT_TOKEN و OWNER_ID می‌خونه.
"""

import os
import logging
import tempfile
import yt_dlp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- تنظیمات ----------------
# این دو مقدار از متغیرهای محیطی خونده می‌شن (توی Railway تنظیم می‌شن، نه داخل کد)
BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])
# ------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def is_owner(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == OWNER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("این ربات خصوصیه و فقط برای صاحبش کار می‌کنه.")
        return
    await update.message.reply_text(
        "سلام! لینک ترک یا پلی‌لیست SoundCloud رو برام بفرست تا دانلودش کنم."
    )


async def download_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("این ربات خصوصیه و فقط برای صاحبش کار می‌کنه.")
        return

    url = update.message.text.strip()
    if "soundcloud.com" not in url:
        await update.message.reply_text("لطفاً یک لینک معتبر از SoundCloud بفرست.")
        return

    status_msg = await update.message.reply_text("در حال دانلود... ⏳")

    with tempfile.TemporaryDirectory() as tmpdir:
        # اسم فایل دقیقاً همون اسم ترک توی SoundCloud می‌مونه (فقط کاراکترهای غیرمجاز فایل‌سیستم حذف می‌شن)
        outtmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")
        ydl_opts = {
            # بالاترین کیفیت صدای موجود
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            # دانلود کاور با بالاترین کیفیت موجود در SoundCloud
            "writethumbnail": True,
            "postprocessors": [
                {
                    # تبدیل به mp3 با بهترین کیفیت ممکن (VBR سطح ۰ = بالاترین کیفیت)
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                },
                {
                    # تبدیل کاور به jpg با بالاترین کیفیت برای اینکه بشه توی تگ mp3 جا داد
                    "key": "FFmpegThumbnailsConvertor",
                    "format": "jpg",
                },
                {
                    # چسباندن کاور به‌عنوان کاور آلبوم داخل خود فایل mp3
                    "key": "EmbedThumbnail",
                },
                {
                    # نوشتن تگ‌های عنوان/خواننده روی فایل
                    "key": "FFmpegMetadata",
                },
            ],
            "postprocessor_args": {
                "thumbnailsconvertor": ["-q:v", "1"],  # کیفیت تبدیل کاور: بالاترین
            },
            "noplaylist": True,
            "quiet": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "track")
                # پیدا کردن فایل mp3 خروجی
                filename = None
                for f in os.listdir(tmpdir):
                    if f.endswith(".mp3"):
                        filename = os.path.join(tmpdir, f)
                        break

            if not filename or not os.path.exists(filename):
                await status_msg.edit_text("فایل دانلود شده پیدا نشد.")
                return

            # محدودیت حجم فایل تلگرام برای ارسال معمولی: ۵۰ مگابایت
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            if size_mb > 49:
                await status_msg.edit_text(
                    f"فایل «{title}» حجمش {size_mb:.1f}MB هست و بزرگ‌تر از محدودیت تلگرامه."
                )
                return

            await status_msg.edit_text("دانلود تموم شد، در حال ارسال... 📤")
            with open(filename, "rb") as audio_file:
                await update.message.reply_audio(audio=audio_file, title=title)
            await status_msg.delete()

        except Exception as e:
            logger.exception("خطا در دانلود")
            await status_msg.edit_text(f"خطا در دانلود: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_track))
    logger.info("ربات روشن شد...")
    app.run_polling()


if __name__ == "__main__":
    main()
