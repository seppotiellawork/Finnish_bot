import os
import logging
from gtts import gTTS
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# הגדרת לוגים
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# הטוקן של הבוט מ-משתני הסביבה ב-Render
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    logger.info(f"התקבלה הודעה מ-{chat_id}: {user_text}")
    await context.bot.send_message(chat_id=chat_id, text="מייצר עבורך קובץ קול... ⏳")
    
    try:
        # יצירת קובץ קול בעזרת gTTS (תומך בעברית ע"י ציון lang='he')
        tts = gTTS(text=user_text, lang='he', slow=False)
        audio_path = f"{chat_id}.mp3"
        tts.save(audio_path)
        
        # שליחת קובץ השמע כהודעת קול (Voice) לטלגרם
        with open(audio_path, 'rb') as audio_file:
            await context.bot.send_voice(chat_id=chat_id, voice=audio_file)
            
        # מחיקת הקובץ מהשרת המקומי אחרי השליחה
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
    except Exception as e:
        logger.error(f"שגיאה ביצירת השמע: {e}")
        # אם יש שפה אחרת או שגיאה בעברית, ננסה אנגלית כגיבוי
        try:
            tts = gTTS(text=user_text, lang='en', slow=False)
            audio_path = f"{chat_id}.mp3"
            tts.save(audio_path)
            with open(audio_path, 'rb') as audio_file:
                await context.bot.send_voice(chat_id=chat_id, voice=audio_file)
            os.remove(audio_path)
        except Exception as inner_e:
            await context.bot.send_message(chat_id=chat_id, text=f"אירעה שגיאה ביצירת הקול: {str(inner_e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # האזנה להודעות טקסט בלבד
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("הבוט הקליל התחיל לפעול...")
    application.run_polling()
