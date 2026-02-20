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

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⚡️ Video qabul qilindi. Tahlil boshlandi...")
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

        transcription = "Audioda hech nima topilmadi."
        if os.path.exists(a_path):
            with open(a_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(a_path, audio_file.read()),
                    model="whisper-large-v3",
                    language="uz",
                    response_format="text"
                )

        visual_file = genai.upload_file(path=f_path)
        model = genai.GenerativeModel(model_name="models/gemini-flash-latest")
        prompt = f"Videodagi ushbu kadrni va audiodagi ushbu matnni birlashtirib o'zbek tilida tahlil ber: {transcription}"
        response = model.generate_content([visual_file, prompt])

        await update.message.reply_text(f"📝 TAHLIL:\n\n{response.text}")

    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {str(e)}")
    finally:
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
