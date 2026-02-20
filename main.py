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
        # Tizim ko'rsatmasini yanada qat'iy qilamiz
        model = genai.GenerativeModel(
            model_name="models/gemini-flash-latest",
            system_instruction="""Siz professional tahlilchisiz. 
            MUHIM QOIDA: Javobingizda hech qanday sarlavha belgilari (#), qalinlashtirish (**), 
            yoki yulduzchalarni (*) ishlatmang. Faqat oddiy matn va raqamlangan ro'yxatdan foydalaning."""
        )
        
        prompt = f"""
        Quyidagi formatda javob ber (belgilarsiz, faqat matn):

        1. ASL MATN:
        [Bu yerga audio matnini tahrirlab yozing]

        2. O'ZBEKCHA TARJIMASI:
        [Matn tarjimasi yoki 'Matn o'zbek tilida' deb yozing]

        3. TO'LIQ TAHLIL:
        [Kadr va matn tahlili]

        Audio matni: {transcription}
        """
        
        response = model.generate_content([visual_file, prompt])
        # Telegramga yuborishdan oldin matnni ortiqcha belgilardan tozalash (qo'shimcha himoya)
        clean_text = response.text.replace("*", "").replace("#", "").replace("`", "")
        await update.message.reply_text(clean_text)

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
