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

# API kalitlarni olish
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Groq va Gemini-ni sozlash
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# Portni band qilish uchun "yolg'onchi" server
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Menga tahlil qilish uchun video yuboring.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bot video kelganini bildirdi
    status_msg = await update.message.reply_text("Video qabul qilindi. Tahlil qilinmoqda, iltimos kuting...")
    
    try:
        video_file = await context.bot.get_file(update.message.video.file_id)
        video_path = "temp_video.mp4"
        await video_file.download_to_drive(video_path)

        # Video tahlil qismi (MoviePy orqali kadr olish)
        clip = VideoFileClip(video_path)
        clip.save_frame("frame.jpg", t=1) 
        
        # Gemini orqali tasvirni tahlil qilish
        sample_file = genai.upload_file(path="frame.jpg", display_name="Frame")
        model = genai.GenerativeModel(model_name="models/gemini-flash-latest")
        response = model.generate_content([sample_file, "Ushbu videodagi kadrni tahlil qilib, nima bo'layotganini o'zbek tilida qisqa yozib ber."])
        
        await update.message.reply_text(f"Tahlil natijasi: \n\n{response.text}")
        
        # Tozalash
        clip.close()
        os.remove(video_path)
        os.remove("frame.jpg")

    except Exception as e:
        await update.message.reply_text(f"Xatolik yuz berdi: {str(e)}")

def main():
    # Serverni alohida oqimda boshlaymiz
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    print("Bot serverda to'liq quvvat bilan ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
