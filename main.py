import os
import asyncio
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Menga tahlil qilish uchun video yuboring.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bu yerda sizning video tahlil kodingiz bor (uni o'zgartirmang)
    await update.message.reply_text("Video qabul qilindi, tahlil kutilmoqda...")

import http.server
import socketserver
import threading

def run_dummy_server():
    # Render port xatosi bermasligi uchun kichik "yolg'onchi" server
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

def main():
    # Portni band qilish uchun serverni alohida oqimda boshlaymiz
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # Botni ishga tushirish
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    print("Bot serverda ishga tushishga tayyor!")
    app.run_polling()

if __name__ == "__main__":
    main()
