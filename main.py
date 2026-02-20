import os
import asyncio
import threading
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

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Bot yangilandi va ishga tushdi. Video yuboring.")

# ... (kodning tepa qismi o'sha-o'sha qoladi) ...

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⚡️ Video tahlil qilinmoqda...")
    v_path = f"v_{update.message.chat_id}.mp4"
    a_path = f"a_{update.message.chat_id}.wav"
    f_path = f"f_{update.message.chat_id}.jpg"

    try:
        video_file = await context.bot.get_file(update.message.video.file_id)
        await video_file.download_to_drive(v_path)

        clip = VideoFileClip(v_path)
        if clip.audio:
            clip.audio.write_audiofile(a_path, fps=16000, logger=None)
        clip.save_frame(f_path, t=1)
        clip.close()

        transcription = "Audio ma'lumot topilmadi."
        if os.path.exists(a_path):
            with open(a_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(a_path, audio_file.read()),
                    model="whisper-large-v3",
                    language="uz", # Groq avtomatik tarjima qilishi ham mumkin
                    response_format="text"
                )

        visual_file = genai.upload_file(path=f_path)
        model = genai.GenerativeModel(model_name="models/gemini-flash-latest")
        
        # MANA SHU YERDA FORMATNI BELGILAYMIZ
        prompt = f"""
        Videodagi ushbu kadr va quyidagi audio matni asosida javobni aynan shu formatda qaytar:

        1. 📝 **ASL MATN (Original text):**
        [Bu yerga audiodagi gaplarni tahrirlangan va xatosiz ko'rinishda yozing]

        2. 🇺🇿 **O'ZBEKCHA TARJIMASI:**
        [Agar asl matn o'zbekcha bo'lmasa, tarjima qiling. O'zbekcha bo'lsa, 'Matn o'zbek tilida' deb qo'ying]

        3. 🔍 **TO'LIQ TAHLIL:**
        [Kadr va matnni birlashtirgan holda tahlil bering]

        Audio matni: {transcription}
        """
        
        response = model.generate_content([visual_file, prompt])
        await update.message.reply_text(response.text)

    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {str(e)}")
    finally:
        for p in [v_path, a_path, f_path]:
            if os.path.exists(p): os.remove(p)
# ... (qolgan qismi o'sha-o'sha) ...
def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.run_polling()

if __name__ == "__main__":
    main()
