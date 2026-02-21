import os
import asyncio
import threading
import time
import http.server
import socketserver
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from moviepy.editor import VideoFileClip
from groq import Groq

# API kalitlar
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# Bir vaqtda ishlov berilayotgan xabarlar ro'yxati
processed_messages = set()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Bot tayyor. Video yuboring.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_id = update.message.message_id
    if msg_id in processed_messages:
        return # Agar bu xabar tahlil qilinayotgan bo'lsa, to'xtatish

    processed_messages.add(msg_id)

    # Fayl hajmini tekshirish (20MB)
    if update.message.video.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ Fayl juda katta. Telegram cheklovi sababli 20 MB dan kichik video yuboring.")
        return

    status_msg = await update.message.reply_text("⚡️ Video tahlil qilinmoqda...")

    # Unikal nomlar yaratish
    uid = f"{update.message.chat_id}_{int(time.time())}"
    v_path = f"v_{uid}.mp4"
    a_path = f"a_{uid}.wav"
    f_path = f"f_{uid}.jpg"

    try:
        video_file = await context.bot.get_file(update.message.video.file_id)
        await video_file.download_to_drive(v_path)

        clip = VideoFileClip(v_path)
        # Audio borligini tekshirish
        has_audio = clip.audio is not None
        if has_audio:
            clip.audio.write_audiofile(a_path, fps=16000, logger=None)

        clip.save_frame(f_path, t=1)
        clip.close()

        transcription = ""
        if has_audio and os.path.exists(a_path):
            with open(a_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(a_path, audio_file.read()),
                    model="whisper-large-v3",
                    language="uz",
                    response_format="text"
                )

        visual_file = genai.upload_file(path=f_path)
        model = genai.GenerativeModel(
            model_name="models/gemini-flash-latest",
            system_instruction="Siz video tahlilchisisiz. Javobda Markdown belgilarni (** , #) ishlatmang. Faqat oddiy matn bering."
        )

        prompt = f"""
        Kadrda nima borligini va audio matnni tahlil qil.
        MUHIM: Agar audio matn ('{transcription}') kadrga umuman mos kelmasa yoki ma'nosiz bo'lsa (masalan 'Long live India' kabi tushunarsiz gaplar), uni audio xatosi deb hisobla va e'tiborga olma.

        Javob tartibi:
        1. ASL MATN: (Audiodagi gaplar, agar tushunarsiz bo'lsa 'Musiqa yoki tushunarsiz audio' deb yoz)
        2. O'ZBEKCHA TARJIMASI:
        3. TO'LIQ TAHLIL: (Kadrda ko'ringan harakatlarni batafsil yoz. Masalan, futbolchi bayroqni tepgan bo'lsa, shuni ham qo'sh)
        """

        response = model.generate_content([visual_file, prompt])
        await update.message.reply_text(response.text)

    except Exception as e:
        print(f"Xatolik: {e}")
    finally:
        # Fayllarni o'chirish
        for p in [v_path, a_path, f_path]:
            if os.path.exists(p): os.remove(p)
        # Xabarni ro'yxatdan o'chirish (5 daqiqadan keyin keshni tozalash mumkin, hozircha oddiy)
        # processed_messages.remove(msg_id) # Bu yerda o'chirmaslik yaxshiroq

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
