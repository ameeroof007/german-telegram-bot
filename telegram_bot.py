import os
import re
import json
import tempfile
import datetime
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytz
from gtts import gTTS
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.8-flash"

GERMANY_TZ = pytz.timezone("Europe/Berlin")
PROGRESS_FILE = "lesson_progress.json"

USER_MODES = {}
CHAT_HISTORIES = {}

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

A1_CURRICULUM = [
    "1. التحية والوداع (Hallo, Guten Morgen, Tschüss)",
    "2. التعريف بالنفس: الاسم والعمر (Ich heiße..., Ich bin... Jahre alt)",
    "3. السؤال عن الحال والرد (Wie geht es dir? Mir geht es gut)",
    "4. الضمائر الشخصية (ich, du, er, sie, es, wir, ihr, sie)",
    "5. فعل الكينونة (sein) وتصريفه في الحاضر",
    "6. فعل الملكية (haben) وتصريفه في الحاضر",
    "7. الأرقام من 0 إلى 20",
    "8. الأرقام من 21 إلى 100",
    "9. أيام الأسبوع وأوقات اليوم (Montag - Sonntag)",
    "10. أشهر السنة وفصول السنة الأربعة",
    "11. أدوات التعريف (der, die, das) للمذكر والمؤنث والمحايد",
    "12. أدوات النكرة (ein, eine) والنفي (kein, keine)",
    "13. أفراد العائلة (die Familie)",
    "14. الألوان الأساسية (die Farben)",
    "15. الفواكه والخضروات (Obst und Gemüse)",
    "16. الطعام والشراب الأساسي (Essen und Trinken)",
    "17. في المطعم والمقهى: كيف تطلب طعامك",
    "18. أدوات السؤال (Wer, Was, Wo, Woher, Wann, Wie)",
    "19. الدول واللغات والجنسيات (Deutschland, Arabisch...)",
    "20. الساعة والوقت (Wie spät ist es?)",
    "21. الروتين اليومي والأفعال القابلة للانفصال (aufstehen, einkaufen)",
    "22. الأفعال الشائعة في الحاضر (gehen, kommen, machen, lernen)",
    "23. الأفعال القوية مع تغيير الحرف الصوتي (sprechen, essen, schlafen)",
    "24. ضمائر الملكية (mein, dein, sein, ihr)",
    "25. المنزل والغرف (die Wohnung und die Zimmer)",
    "26. الأثاث والأدوات المنزلية (die Möbel)",
    "27. الملابس (die Kleidung)",
    "28. حالة النصب (Akkusativ) للمذكر (den, einen)",
    "29. حروف الجر المكانية البسيطة (in, auf, unter, neben)",
    "30. في السوبرماركت: السؤال عن السعر والكمية (Wie viel kostet...?)",
    "31. وسائل المواصلات (der Bus, der Zug, das Auto)",
    "32. السؤال عن الطريق والاتجاهات (links, rechts, geradeaus)",
    "33. الأماكن في المدينة (der Bahnhof, die Post, die Bank)",
    "34. الطقس وحالة الجو (Das Wetter: Es regnet, Die Sonne scheint)",
    "35. الهوايات وأوقات الفراغ (Hobbys und Freizeit)",
    "36. الفعل المساعد (können - يستطيع) وبناء الجملة معه",
    "37. الفعل المساعد (müssen - يجب) وبناء الجملة معه",
    "38. الفعل المساعد (wollen / möchten - يريد / يود)",
    "39. أجزاء الجسم (der Körper)",
    "40. عند الطبيب: التعبير عن الألم (Mir tut ... weh)",
    "41. المهن والعمل (Berufe und Arbeit)",
    "42. الصفات الأساسية وعكسها (groß/klein, neu/alt, billig/teuer)",
    "43. حروف الجر الزمنية (am, um, im)",
    "44. صيغة الجمع للأسماء في الألمانية",
    "45. النفي باستخدام (nicht) وموقعها في الجملة",
    "46. حالة الجر (Dativ) مع الضمائر (mir, dir, ihm, ihr)",
    "47. الأفعال التي تأخذ Dativ (helfen, danken, gefallen, gehören)",
    "48. حروف الجر التي تأخذ Dativ دائماً (mit, nach, aus, zu, von, bei)",
    "49. حروف الجر التي تأخذ Akkusativ دائماً (für, ohne, gegen, durch, um)",
    "50. الماضي البسيط لفعلي الكينونة والملكية (war / hatte)",
    "51. مدخل إلى الماضي التام (Perfekt) مع (haben)",
    "52. الماضي التام (Perfekt) لأفعال الحركة مع (sein)",
    "53. صيغة الأمر المهذبة والعادية (Imperativ)",
    "54. أدوات الربط البسيطة (und, aber, oder, denn)",
    "55. في الفندق: حجز غرفة والاستفسار",
    "56. في المطار ومحطة القطار: التذاكر والمواعيد",
    "57. كتابة رسالة أو إيميل قصير رسمي وغير رسمي",
    "58. التهنئة في المناسبات (Alles Gute zum Geburtstag!)",
    "59. التعبير عن الرأي البسيط (Ich finde..., Ich glaube...)",
    "60. مراجعة شاملة ومحادثة قصيرة تجمع أساسيات A1"
]

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chat_id": None, "lesson_index": 0}

def save_progress(data):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# دالة ذكية لإعادة المحاولة تلقائياً في حال ضغط الخوادم (503)
def safe_generate_content(contents):
    for attempt in range(3):
        try:
            return client.models.generate_content(model=MODEL_NAME, contents=contents)
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < 2:
                    time.sleep(2) # الانتظار لثانيتين وإعادة المحاولة
                    continue
            raise e

def extract_german_phrases(text: str) -> str:
    german_lines = []
    for line in text.splitlines():
        if "🇩🇪" in line:
            clean = re.sub(r"[🇩🇪*#_`:\-]", "", line).strip()
            clean = re.sub(r"[\u0600-\u06FF]+", "", clean).strip()
            if clean:
                german_lines.append(clean)
    return " ... ".join(german_lines[:4])

async def send_german_voice(bot, chat_id: int, german_text: str):
    if not german_text or len(german_text) < 2:
        return
    try:
        tts = gTTS(text=german_text, lang="de")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            temp_path = tmp.name
        tts.save(temp_path)
        with open(temp_path, "rb") as audio_file:
            await bot.send_voice(chat_id=chat_id, voice=audio_file, caption="🔊 النطق الصوتي بالألمانية")
        os.remove(temp_path)
    except Exception:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    USER_MODES[chat_id] = "tutor"
    await update.message.reply_text(
        "مرحباً بك في معلم ومترجم الألمانية الذكي! 🇩🇪🇬🇧🇸🇦\n\n"
        "📌 الأوامر المتاحة:\n"
        "• `/translate` - وضع الترجمة الفورية (عربي ➔ ألماني وإنجليزي)\n"
        "• `/tutor` - وضع المعلم الذكي والشرح\n"
        "• `/clear` - مسح ذاكرة المحادثة\n"
        "• `/daily` - تفعيل الدرس اليومي الساعة 9:00 صباحاً\n"
        "• `/test_lesson` - استلام درس تجريبي الآن\n\n"
        "🎙️ أرسل رسالة صوتية لتصحيح نطقك، أو صورة لشرحها!"
    )

async def set_translate_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USER_MODES[update.effective_chat.id] = "translate"
    await update.message.reply_text("🌐 تم تفعيل وضع الترجمة الفورية! اكتب أي جملة عربية وسأترجمها للألمانية والإنجليزية.")

async def set_tutor_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USER_MODES[update.effective_chat.id] = "tutor"
    await update.message.reply_text("🎓 تم تفعيل وضع المعلم الذكي!")

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    CHAT_HISTORIES[update.effective_chat.id] = []
    await update.message.reply_text("🧹 تم مسح ذاكرة المحادثة بنجاح.")

async def send_scheduled_lesson(context: ContextTypes.DEFAULT_TYPE):
    progress = load_progress()
    chat_id = progress.get("chat_id")
    idx = progress.get("lesson_index", 0)

    if not chat_id:
        return

    if idx >= len(A1_CURRICULUM):
        idx = 0

    topic = A1_CURRICULUM[idx]
    prompt = (
        f"أنت معلم لغة ألمانية محترف. اكتب درساً يومياً لمستوى A1 حول:\n'{topic}'\n\n"
        f"التزم بالتنسيق التالي:\n1. عنوان الدرس ورقمه ({idx + 1}/60).\n"
        f"2. شرح القاعدة بالعربية.\n3. أهم 5 كلمات مع علم 🇩🇪 وترجمتها بالإنجليزية 🇬🇧 والعربية 🇸🇦.\n"
        f"4. حوار قصير مع الترجمة.\n5. سؤال تمرين."
    )

    try:
        response = safe_generate_content(prompt)
        lesson_text = response.text
        await context.bot.send_message(chat_id=chat_id, text=lesson_text)
        
        german_audio_text = extract_german_phrases(lesson_text)
        await send_german_voice(context.bot, chat_id, german_audio_text)

        progress["lesson_index"] = idx + 1
        save_progress(progress)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ خطأ مؤقت في الخوادم، حاول مجدداً بعد قليل: {str(e)}")

async def enable_daily_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    progress = load_progress()
    progress["chat_id"] = update.effective_chat.id
    save_progress(progress)
    await update.message.reply_text("✅ تم تفعيل الدروس اليومية الساعة 9:00 صباحاً.")

async def test_lesson_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    progress = load_progress()
    progress["chat_id"] = update.effective_chat.id
    save_progress(progress)
    await update.message.reply_text("⏳ جاري تحضير الدرس...")
    await send_scheduled_lesson(context)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if user_text.startswith("/"):
        return

    chat_id = update.effective_chat.id
    mode = USER_MODES.get(chat_id, "tutor")
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        if mode == "translate":
            prompt = (
                f"ترجم النص بدقة من العربية إلى الألمانية والإنجليزية بالشكل التالي:\n"
                f"🇩🇪 [الترجمة الألمانية]\n🗣️ النطق: [الطريقة]\n🇬🇧 [الإنجليزية]\n\nالنص: {user_text}"
            )
        else:
            history = CHAT_HISTORIES.setdefault(chat_id, [])
            history_context = "\n".join(history[-8:])
            prompt = (
                f"أنت معلم ألمانية A1. أجب بالعربية، وضع علم 🇩🇪 قبل الألمانية ومقابلها 🇬🇧 و 🇸🇦.\n"
                f"السياق:\n{history_context}\n\nسؤال الطالب: {user_text}"
            )

        response = safe_generate_content(prompt)
        reply_text = response.text

        if mode != "translate":
            history.append(f"الطالب: {user_text}")
            history.append(f"المعلم: {reply_text}")

        await update.message.reply_text(reply_text)
        german_audio_text = extract_german_phrases(reply_text)
        await send_german_voice(context.bot, chat_id, german_audio_text)

    except Exception as e:
        await update.message.reply_text(f"⚠️ الخوادم مشغولة مؤقتاً (خطأ 503). يجدر بك المحاولة بعد ثوانٍ.")

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    try:
        file = await update.message.voice.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            path = tmp.name
        await file.download_to_drive(path)
        with open(path, "rb") as f:
            b_data = f.read()
        os.remove(path)

        prompt = "استمع للرسالة الصوتية لطالب A1 ألماني. صحح نطقه واكتب ما قاله بالألمانية 🇩🇪 والإنجليزية 🇬🇧 والعربية 🇸🇦."
        response = safe_generate_content([types.Part.from_bytes(data=b_data, mime_type="audio/ogg"), prompt])
        await update.message.reply_text(response.text)
        await send_german_voice(context.bot, chat_id, extract_german_phrases(response.text))
    except Exception as e:
        await update.message.reply_text(f"⚠️ تعذر معالجة الصوت بسبب الضغط المؤقت.")

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            path = tmp.name
        await file.download_to_drive(path)
        with open(path, "rb") as f:
            b_data = f.read()
        os.remove(path)

        prompt = update.message.caption or "اشرح محتوى هذه الصورة باللغة الألمانية."
        response = safe_generate_content([types.Part.from_bytes(data=b_data, mime_type="image/jpeg"), prompt])
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"⚠️ تعذر معالجة الصورة بسبب الضغط المؤقت.")

async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("start", "رسالة الترحيب والتعريف"),
        ("translate", "وضع الترجمة الفورية (عربي ➔ ألماني وإنجليزي)"),
        ("tutor", "وضع المعلم الذكي والقواعد"),
        ("test_lesson", "استلام درس A1 تجريبي مع النطق"),
        ("daily", "تفعيل الدروس اليومية الساعة 9 ص"),
        ("clear", "مسح ذاكرة المحادثة")
    ])

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("translate", set_translate_mode))
    application.add_handler(CommandHandler("tutor", set_tutor_mode))
    application.add_handler(CommandHandler("clear", clear_memory))
    application.add_handler(CommandHandler("daily", enable_daily_lessons))
    application.add_handler(CommandHandler("test_lesson", test_lesson_now))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))

    job_queue = application.job_queue
    job_queue.run_daily(
        send_scheduled_lesson,
        time=datetime.time(hour=9, minute=0, tzinfo=GERMANY_TZ)
    )

    print("🚀 البوت يعمل مع نظام الحماية ضد الضغط (503)...")
    application.run_polling()

if __name__ == "__main__":
    main()
