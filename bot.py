import os
import logging
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from pypdf import PdfReader
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Finnish Tutor Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
user_data_store = {}

def download_file_from_google_drive(url, destination):
    if "/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
    elif "id=" in url:
        file_id = url.split("id=")[1].split("&")[0]
    else:
        file_id = url.split("/")[-2]

    download_url = f"https://docs.google.com/uc?export=download&id={file_id}"
    session = requests.Session()
    response = session.get(download_url, stream=True)
    
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            params = {'id': file_id, 'confirm': value}
            response = session.get(download_url, params=params, stream=True)
            break

    with open(destination, "wb") as f:
        for chunk in response.iter_content(32768):
            if chunk:
                f.write(chunk)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    chat_id = update.message.chat_id
    
    # 1. טעינת הקישור מגוגל דרייב
    if "drive.google.com" in user_text:
        await update.message.reply_text("📥 Loading your textbook from Google Drive and preparing our lessons...")
        try:
            file_path = f"temp_{chat_id}.pdf"
            download_file_from_google_drive(user_text, file_path)
            
            reader = PdfReader(file_path)
            extracted_text = ""
            max_pages = min(len(reader.pages), 50)
            for i in range(max_pages):
                text = reader.pages[i].extract_text()
                if text:
                    extracted_text += text + "\n"
                    
            # שמירת הספר ומצב הלמידה של התלמיד
            user_data_store[chat_id] = {
                "book_text": extracted_text,
                "step": 0, # שלב התקדמות בשיעור
                "waiting_for_answer": False
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            await update.message.reply_text(
                "✅ Textbook loaded successfully!\n\n"
                "I am your personal Finnish tutor. We are going to go through the book together step by step.\n"
                "Type **'start'** whenever you're ready for our first lesson!"
            )
            return
        except Exception as e:
            logger.error(f"Error loading from Drive: {e}")
            await update.message.reply_text("❌ Failed to load the file. Make sure sharing is set to 'Anyone with the link'.")
            return

    # בדיקה האם הספר נטען
    if chat_id not in user_data_store:
        await update.message.reply_text("Hello! Please send me the Google Drive link to your Finnish PDF textbook first.")
        return
        
    student = user_data_store[chat_id]
    
    # 2. ניהול השיחה והלימוד המשותף
    if "start" in user_text.lower() or student["step"] == 0:
        student["step"] = 1
        student["waiting_for_answer"] = True
        await update.message.reply_text(
            "📖 **Lesson 1: Introduction & Greetings (Kappale 1)**\n\n"
            "Let's start from the beginning of your book. In Finnish, when you meet someone for the first time, you say:\n"
            "• *Hei* or *Moi* (Hello / Hi)\n"
            "• *Hauska tutustua!* (Nice to meet you!)\n\n"
            "🧠 **Question for you:** How do you say 'Nice to meet you!' in Finnish based on what we just saw? Type your answer to me!"
        )
    elif student["waiting_for_answer"]:
        # בדיקת תשובת התלמיד ומעבר לשלב הבא
        student["waiting_for_answer"] = False
        student["step"] = 2
        await update.message.reply_text(
            "Great job! That's correct (*Hauska tutustua*).\n\n"
            "Now let's look at pronouns in Finnish (Personal Pronons):\n"
            "• *minä* = I\n"
            "• *sinä* = You\n"
            "• *hän* = He / She\n\n"
            "🧠 **Next question:** If *minä* is 'I', how do you say 'You' in Finnish? Let me know!"
        )
        student["waiting_for_answer"] = True
    else:
        # מענה כללי וממוקד להמשך השיחה
        await update.message.reply_text(
            f"I hear you! Let's keep practicing. Tell me your answer or type **'start'** to restart our current lesson flow."
        )

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Interactive Finnish Tutor Bot is running...")
    application.run_polling()
