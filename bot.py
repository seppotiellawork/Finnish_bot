import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from gtts import gTTS
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- הוסף את זה כאן בראש הקובץ כדי לרצות את Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# הפעלת שרת הדמה ברקע
threading.Thread(target=run_dummy_server, daemon=True).start()
# ----------------------------------------------------

# הגדרת לוגים
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# הטוקן של הבוט
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# מכאן ממשיך שאר קוד הבוט הרגיל שלך...
