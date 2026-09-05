import os
import logging
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from pypdf import PdfReader
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Finnish AI Tutor Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
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
    
    if "drive.google.com" in user_text:
        await update.message.reply_text("📥 Loading your textbook and connecting it to your AI tutor...")
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
                    
            user_data_store[chat_id] = {
                "book_text": extracted_text,
                "history": []
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            await update.message.reply_text(
                "✅ Textbook loaded successfully! I am your personal Finnish tutor.\n"
                "Ask me anything or let's start our first lesson!"
            )
            return
        except Exception as e:
            logger.error(f"Error loading from Drive: {e}")
            await update.message.reply_text("❌ Failed to load the file. Make sure sharing is set to 'Anyone with the link'.")
            return

    if chat_id not in user_data_store:
        await update.message.reply_text("Hello! Please send me the Google Drive link to your Finnish PDF textbook first.")
        return
        
    student = user_data_store[chat_id]
    
    if not client:
        await update.message.reply_text("⚠️ Error: GEMINI_API_KEY is missing in Render Environment variables.")
        return

    system_instruction = (
        "You are an expert, friendly, and conversational Finnish private tutor. "
        "Help the student learn Finnish step-by-step using their textbook content provided below. "
        "Speak naturally, explain grammar simply, give examples, and ask engaging questions.\n\n"
        f"--- TEXTBOOK CONTENT ---\n{student['book_text'][:10000]}"
    )

    try:
        chat_history = student.get("history", [])
        chat_history.append(f"User: {user_text}")
        
        full_prompt = (
            f"{system_instruction}\n\n"
            f"Conversation History:\n" + "\n".join(chat_history[-8:]) + "\nTutor:"
        )
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=full_prompt,
        )
        
        reply_text = response.text.strip()
        chat_history.append(f"Tutor: {reply_text}")
        student["history"] = chat_history
        
        await update.message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Gemini API Error details: {e}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("AI Finnish Tutor Bot is running...")
    application.run_polling()
