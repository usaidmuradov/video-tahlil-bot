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

# 1. API kalitlar (Universal usul)
try:
    from google.colab import userdata
    TELEGRAM_TOKEN = userdata.get('TELEGRAM_TOKEN')
    GROQ_API_KEY = userdata.get('GROQ_API_KEY')
    GEMINI_API_KEY = userdata.get('GEMINI_API_KEY')
except:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. Mijozlarni sozlash
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-flash-latest')

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
    if msg_id in processed_messages: return
    processed_messages.add(msg_id)

    if update.message.video.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ Fayl juda katta. 20 MB dan kichik video yuboring.")
        processed_messages.remove(msg_id)
        return

    status_msg = await update.message.reply_text("⚡️ Video tahlil qilinmoqda...")
    uid = f"{update.message.chat_id}_{int(time.time())}"
    v_path, a_path, f_path = f"v_{uid}.mp4", f"a_{uid}.wav", f"f_{uid}.jpg"

    try:
        video_file = await context.bot.get_file(update.message.video.file_id)
        await video_file.download_to_drive(v_path)

        clip = VideoFileClip(v_path)
        has_audio = clip.audio is not None
        if has_audio: clip.audio.write_audiofile(a_path, fps=16000, logger=None)
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
        
        prompt = f"""
        Sening vazifang videodagi asosiy voqeani va audioni tahlil qilish. Javobingni quyidagi tuzilmada ber:
        1. **TO'LIQ AUDIO MATN:** {transcription if transcription else "Audio topilmadi"}
        2. **TO'LIQ AUDIO TARJIMA:** Agar audio o'zbekcha bo'lmasa, uni o'zbek tiliga ma'nodosh qilib tarjima qil.
        3. **UMUMIY TAHLIL:** Videodagi mayda vizual detallarga (kiyim, soqol, fon) ortiqcha to'xtalma. Asosiy harakatni londa tushuntir.
        """

        response = model.generate_content([visual_file, prompt])
        await update.message.reply_text(response.text, parse_mode="Markdown")

    except Exception as e:
        print(f"Xatolik: {e}")
        await update.message.reply_text("⚠️ Tahlil jarayonida xatolik yuz berdi.")
    finally:
        if msg_id in processed_messages: processed_messages.remove(msg_id)
        for p in [v_path, a_path, f_path]:
            if os.path.exists(p): os.remove(p)

def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
