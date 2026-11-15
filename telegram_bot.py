import os
import json
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# بيانات الاعتماد من متغيرات البيئة على Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

GERMANY_TZ = pytz.timezone("Europe/Berlin")
PROGRESS_FILE = "lesson_progress.json"

# خادم ويب خفيف جداً وفوري لإرضاء Render ومنع الخروج المبكر
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

# تشغيل السيرفر فوراً في الخلفية قبل أي شيء آخر
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

def get_free_model():
    try:
        models = client.models.list().data
        for m in models:
            mid = m.id
            if "whisper" not in mid and "guard" not in mid and "tts" not in mid and "embed" not in mid:
                return mid
    except Exception:
        pass
    return "llama-3.1-8b-instant"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت تعلم الألمانية المجاني! 🇩🇪\n\n"
        "📌 الأوامر المتاحة:\n"
        "• `/daily` - لتفعيل استلام درس يومي الساعة 9:00 صباحاً.\n"
        "• `/test_lesson` - لاستلام الدرس التجريبي الآن.\n\n"
        "💬 يمكنك في أي وقت إرسال أي سؤال حول اللغة الألمانية، وسيقوم المعلم الذكي بالإجابة عليك فوراً!"
    )

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
        f"أنت معلم لغة ألمانية محترف. اكتب درساً يومياً شيقاً ومكثفاً لمستوى A1 حول الموضوع التالي:\n"
        f"'{topic}'\n\n"
        f"التزم بالتنسيق التالي بدقة:\n"
        f"1. عنوان الدرس ورقمه ({idx + 1}/60).\n"
        f"2. شرح القاعدة أو الفكرة بسطرين أو ثلاثة باللغة العربية البسيطة.\n"
        f"3. أهم 5 إلى 7 كلمات أو عبارات ألمانية رئيسية (مع أداة التعريف der/die/das للأسماء) وترجمتها للعربية.\n"
        f"4. مثالان لحوار قصير أو جملتين عمليتين مع الترجمة.\n"
        f"5. سؤال تمرين صغير في النهاية ليختبر الطالب نفسه."
    )

    chosen_model = get_free_model()
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=chosen_model,
    )
    lesson_text = chat_completion.choices[0].message.content

    await context.bot.send_message(chat_id=chat_id, text=lesson_text)

    progress["lesson_index"] = idx + 1
    save_progress(progress)

async def enable_daily_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    progress = load_progress()
    progress["chat_id"] = update.effective_chat.id
    save_progress(progress)
    await update.message.reply_text(
        "✅ تم تفعيل نظام الدروس اليومية بنجاح!\n"
        "ستصلك رسالة درس واحدة يومياً في الساعة 09:00 صباحاً بتوقيت ألمانيا.\n\n"
        "للحصول على الدرس التجريبي الآن فوراً، أرسل: /test_lesson"
    )

async def test_lesson_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    progress = load_progress()
    progress["chat_id"] = update.effective_chat.id
    save_progress(progress)
    await update.message.reply_text("⏳ جاري تحضير الدرس عبر النماذج المجانية...")
    await send_scheduled_lesson(context)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if user_text.startswith("/"):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    prompt = (
        f"أنت معلم لغة ألمانية صبور ومحترف لمستوى المبتدئين (A1). "
        f"أجب عن سؤال الطالب التالي باللغة العربية مع توضيح الأمثلة بالألمانية وترجمتها:\n\n"
        f"سؤال الطالب: {user_text}"
    )

    try:
        chosen_model = get_free_model()
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=chosen_model,
        )
        reply_text = response.choices[0].message.content
        await update.message.reply_text(reply_text)
    except Exception:
        await update.message.reply_text("عذراً، حدث خطأ بسيط أثناء معالجة سؤالك. حاول مجدداً بعد قليل.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("daily", enable_daily_lessons))
    application.add_handler(CommandHandler("test_lesson", test_lesson_now))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    job_queue = application.job_queue
    job_queue.run_daily(
        send_scheduled_lesson,
        time=datetime.time(hour=9, minute=0, tzinfo=GERMANY_TZ)
    )

    print("🚀 البوت السحابي يعمل الآن بنجاح...")
    application.run_polling()

if __name__ == "__main__":
    main()
