try:
        # יצירת אובייקט צ'אט מובנה עם ההנחיה של המורה ותוכן הספר כהקשר
        chat = client.chats.create(
            model='gemini-2.5-flash',
            config={
                'system_instruction': system_instruction,
                'temperature': 0.7,
            }
        )
        
        # שליחת ההודעה של המשתמש וקבלת תשובה חלקה
        response = chat.send_message(user_text)
        reply_text = response.text.strip()
        
        await update.message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        await update.message.reply_text("⚠️ Sorry, I encountered an error communicating with the AI. Please try again.")
