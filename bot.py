import os
import logging
import torch
from transformers import AutoProcessor, BarkModel
import scipy.io.wavfile as wavfile
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# הגדרת לוגים לטרמינל
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# טוקן הבוט מ-BotFather (מומלץ לשים במשתנה סביבה, או להדביק כאן ישירות לניסיון)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "הדבק_כאן_את_הטוקן_שלך")

logger.info("טוען את מודל Bark לזיכרון... זה עשוי לקחת כמה רגעים.")
device = "cuda" if torch.cuda.is_available() else "cpu"

# טעינת המודל והפרוססור
processor = AutoProcessor.from_pretrained("suno/bark")
model = BarkModel.from_pretrained("suno/bark").to(device)
logger.info(f"המודל נטען בהצלחה על גבי: {device}")

def text_to_speech(text: str, output_filename="output.wav"):
    # הגדרת פריסט קול (אפשר לשנות בהתאם להעדפה, למשל v2/en_speaker_6)
    inputs = processor(text, voice_preset="v2/en_speaker_6").to(device)

    # יצירת המערך הקולי
    audio_array = model.generate(**inputs)
    audio_array = audio_array.cpu().numpy().squeeze()

    # שמירה כקובץ שמע WAV
    sample_rate = model.generation_config.sample_rate
    wavfile.write(output_filename, sample_rate, audio_array)
    return output_filename

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id

    logger.info(תיקון הודעה התקבלה מ-[{chat_id}]: {user_text})
    await context.bot.send_message(chat_id=chat_id, text="מייצר עבורך קובץ קול באמצעות Bark... ⏳")

    try:
        # יצירת קובץ השמע
        audio_path = text_to_speech(user_text, output_filename=f"{chat_id}.wav")

        # שליחת קובץ השמע כהודעת קול (Voice) לטלגרם
        with open(audio_path, 'rb') as audio_file:
            await context.bot.send_voice(chat_id=chat_id, voice=audio_file)

        # מחיקת הקובץ מהשרת המקומי אחרי השליחה
        if os.path.exists(audio_path):
            os.remove(audio_path)

    except Exception as e:
        logger.error(f"שגיאה ביצירת השמע: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"אירעה שגיאה ביצירת הקול: {str(e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    # האזנה להודעות טקסט (לא כולל פקודות)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("הבוט התחיל לפעול ומאזין להודעות...")
    application.run_polling()