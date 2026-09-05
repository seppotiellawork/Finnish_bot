import os
import logging
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from pypdf import PdfReader
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

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

def download_file_from_google_drive(file_id, destination):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    response = session.get(URL, params={'id': file_id}, stream=True)
    with open(destination, "wb") as f:
        for chunk in response.iter_content(32768):
            if chunk:
                f.write(chunk)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    chat_id = update.message.chat_id
    
    # אם המשתמש שולח קישור לגוגל דרייב
    if "drive.google.com/file/d/" in user_text:
        await update.message.reply_text("📥 Google Drive link detected! Downloading and reading the book...")
        try:
            # חילוץ ה-ID מהקישור
            file_id = user_text.split("/d/")[1].split("/")[0]
            file_path = f"temp_{chat_id}.pdf"
            
            # הורדה מגוגל דרייב
            download_file_from_google_drive(file_id, file_path)
            
            # קריאת הקובץ
            reader = PdfReader(file_path)
            extracted_text = ""
            max_pages = min(len(reader.pages), 60) # קריאת 60 עמודים ראשונים לשמירה על זיכרון
            for i in range(max_pages):
                text = reader.pages[i].extract_text()
                if text:
                    extracted_text += text + "\n"
                    
            user_data_store[chat_id] = {
                "book_text": extracted_text,
                "current_chapter": 1
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            await update.message.reply_text("✅ Book from Google Drive loaded successfully! Let's start learning.")
            return
        except Exception as e:
            logger.error(f"Error loading from Drive: {e}")
            await update.message.reply_text("❌ Failed to load the file from Google Drive. Make sure the link is set to 'Anyone with the link'.")
            return

    # אם הקובץ עדיין לא נטען
    if chat_id not in user_data_store:
        await update.message.reply_text("Hello! Please send me the Google Drive link to your PDF textbook to get started.")
        return
        
    user = user_data_store[chat_id]
    
    # תגובות מורה לפינית
    if "test me" in user_text.lower():
        reply = "🧠 **Mini-Quiz**: How do you introduce yourself formally in Finnish based on chapter 1? Type your answer!"
    else:
        reply = f"Tutor Guidance:\nRegarding '{user_text}': Let's check the rules from your book. Would you like me to give you an example sentence?"

    await update.message.reply_text(reply, parse_mode="Markdown")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Finnish Tutor Bot with Google Drive is running...")
    application.run_polling()
