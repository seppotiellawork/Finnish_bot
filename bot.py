import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from gtts import gTTS
from pypdf import PdfReader
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# שרת דמה לשמירה על הפורט ב-Render
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

# הגדרת לוגים
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# זיכרון פנימי פשוט לשמירת תוכן ה-PDF שהועלה לכל משתמש
user_study_materials = {}

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """טיפול בקבצי PDF שהמשתמש מעלה לבוט"""
    chat_id = update.message.chat_id
    document = update.message.document
    
    if not document.file_name.endswith('.pdf'):
        await update.message.reply_text("Please send a valid PDF file for your Finnish lessons.")
        return

    await update.message.reply_text("📥 Downloading and processing your PDF book... Please wait.")
    
    try:
        # הורדת הקובץ מטלגרם
        file = await context.bot.get_file(document.file_id)
        file_path = f"temp_{chat_id}.pdf"
        await file.download_to_drive(file_path)
        
        # קריאת הטקסט מתוך ה-PDF בעזרת pypdf
        reader = PdfReader(file_path)
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
                
        # שמירת תוכן הספר בזיכרון של הבוט עבור המשתמש הזה
        user_study_materials[chat_id] = extracted_text
        
        # מחיקת קובץ ה-PDF מהאחסון הזמני
        if os.path.exists(file_path):
            os.remove(file_path)
            
        await update.message.reply_text(
            "✅ Book loaded successfully! I am now your Finnish tutor based on this material. "
            "You can ask me questions, ask for vocabulary, or ask me to explain grammar rules in English."
        )
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        await update.message.reply_text(f"❌ Failed to process the PDF: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מענה להודעות טקסט של המשתמש כמורה לפינית"""
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    # בדיקה אם המשתמש העלה קודם ספר
    has_material = chat_id in user_study_materials and len(user_study_materials[chat_id]) > 0
    
    # תגובה בסיסית כמורה פרטי לפינית (מסביר באנגלית)
    if has_material:
        # אפשר בעתיד לחבר כאן מודל AI או להשתמש בטקסטים מתוך הספר
        reply_text = f"Tutor (based on your PDF): As a Finnish tutor, regarding your question '{user_text}', let's look at the grammar and vocabulary from your textbook."
    else:
        reply_text = f"Hello! I am your Finnish tutor. You haven't uploaded a PDF book yet. Send me a PDF textbook, or ask me any Finnish question in English!"

    await update.message.reply_text(reply_text)
    
    # המרה לקול והשמעה (אופציונלי - מקריא את התשובה באנגלית/פינית)
    try:
        tts = gTTS(text=reply_text, lang='en', slow=False)
        audio_path = f"{chat_id}.mp3"
        tts.save(audio_path)
        with open(audio_path, 'rb') as audio_file:
            await context.bot.send_voice(chat_id=chat_id, voice=audio_file)
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        logger.error(f"TTS error: {e}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # הוספת מאזין לקבצי PDF
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    # הוספת מאזין להודעות טקסט
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Finnish Tutor Bot is running...")
    application.run_polling()
