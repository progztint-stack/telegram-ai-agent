# Telegram AI Browser Agent

مساعد AMBOR AI BOT آمن على Telegram يدعم Gemini وGroq ومتصفح Playwright وSQLite. يقتصر المتصفح افتراضيًا على النطاقات المسموحة ويحظر الشبكات المحلية والعناوين غير العامة.

## المتطلبات

- Python 3.11 أو أحدث
- GitHub Codespaces أو بيئة Linux
- توكن Telegram ومعرّف مستخدم مصرح به ومفتاح واحد على الأقل من Gemini أو Groq لتشغيل البوت

## التشغيل في GitHub Codespaces

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m playwright install --with-deps chromium
cp .env.example .env
python -m pytest
python scripts/health_check.py
```

تعمل اختبارات الوحدات دون مفاتيح حقيقية باستخدام مزود محاكاة. يتطلب فحص الصحة اكتمال إعدادات التشغيل؛ عند عدم وجود أسرار سيعرض أسماء القيم الناقصة ويعيد حالة غير سليمة. لن يبدأ البوت الفعلي إلا عند ضبط `TELEGRAM_BOT_TOKEN` و`AUTHORIZED_TELEGRAM_USERS` ومفتاح مزود واحد على الأقل.

## إعداد الاعتمادات

عدّل ملف `.env` محليًا بالقيم التالية:

```dotenv
GEMINI_API_KEY=
GROQ_API_KEY=
TELEGRAM_BOT_TOKEN=
AUTHORIZED_TELEGRAM_USERS=123456789
AI_PRIMARY_PROVIDER=gemini
AI_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=1
BROWSER_HEADLESS=true
BROWSER_ALLOWED_DOMAINS=localhost,127.0.0.1
DATABASE_URL=sqlite:///./data/tasks.db
LOG_LEVEL=INFO
```

لا تضع مفاتيح حقيقية في Git أو Telegram أو السجلات.

### GitHub Codespaces Secrets

1. افتح إعدادات GitHub للحساب أو المستودع.
2. اختر **Secrets and variables > Codespaces**.
3. أضف الأسرار بالمسميات: `GEMINI_API_KEY`، `GROQ_API_KEY`، و`TELEGRAM_BOT_TOKEN`. يمكن ضبط `AUTHORIZED_TELEGRAM_USERS` كسرّ أو متغير Codespaces.
4. تحقق من سياسة وصول المنظمة/المستودع للأسرار، ثم أعد تشغيل Codespace. وجود سر في إعدادات GitHub لا يعني تلقائيًا أنه متاح لكل مستودع.
5. للتحقق دون كشف القيم، شغّل `python scripts/health_check.py`؛ سيعرض أسماء الإعدادات الناقصة فقط.

## أوامر البوت

- `/start` البدء
- `/help` المساعدة
- `/status` حالة الإعدادات
- `/provider` المزود النشط وحالة الإعداد
- `/providers` حالة المزودين
- `/test_ai` تجربة الذكاء الاصطناعي
- `/browser_status` حالة المتصفح
- `/cancel` إلغاء المهمة النشطة
- `/tasks` عرض المهام

## أوامر التشغيل والاختبار

```bash
python -m src.main
python -m pytest
python -m pytest tests/unit
python -m pytest tests/browser
python scripts/health_check.py
```

لا يتم تشغيل البوت عند غياب `TELEGRAM_BOT_TOKEN` أو قائمة المستخدمين المصرح لهم أو كلا مفتاحي الذكاء الاصطناعي. يمكن بدء التشغيل بمفتاح مزود واحد، ويُستخدم المزود الآخر تلقائيًا إذا كان مفتاحه مضبوطًا.

## المعمارية

- `src/providers`: واجهة موحدة وسلسلة فشل Gemini ثم Groq.
- `src/bot`: أوامر Telegram والتحكم بالتفويض.
- `src/browser`: إدارة Chromium والتصفح والتقاط الصور وفحص DOM.
- `src/services`: المهام والسياق والتقارير.
- `src/database`: تخزين SQLite.
- `fixtures`: صفحات HTML تجريبية محلية.

## النشر المستمر

يجب تشغيل البوت كعامل (worker) دائم مع عملية واحدة فقط لأن Telegram يستخدم long polling. لا يُعد Codespaces مضيف إنتاج دائمًا. أضف المتغيرات التالية إلى إعدادات البيئة السرية لدى مضيفك:

- مطلوب: `TELEGRAM_BOT_TOKEN`، و`AUTHORIZED_TELEGRAM_USERS` (معرّفات Telegram الرقمية مفصولة بفواصل)، ومفتاح واحد على الأقل من `GEMINI_API_KEY` أو `GROQ_API_KEY`.
- يُنصح بضبط المفتاحين معًا لتفعيل التحويل الاحتياطي. لا تُرسل مفاتيح حقيقية داخل المستودع أو سجلات النشر.
- اضبط `DATABASE_URL` على ملف SQLite ضمن قرص دائم، مثل `sqlite:////data/ambor/tasks.db`، وتأكد أن مجلد `/data/ambor` موجود وقابل للكتابة.
- يتطلب المضيف Python 3.11+ واتصال HTTPS صادرًا إلى Telegram وواجهات Gemini/Groq. يحتاج المتصفح Chromium وتبعياته النظامية.

خطوات بناء وتشغيل عامل Linux:

```bash
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium
python scripts/health_check.py
python -m src.main
```

يحدد [Procfile](./Procfile) أمر العامل `python -m src.main`. استخدم القرص الدائم الذي يوفره مضيفك، واضبط فحص الصحة على `python scripts/health_check.py`. لا تشغّل نسخًا متعددة من العامل على قاعدة SQLite نفسها. يغلق التطبيق عملاء المزودين وChromium عند إيقافه الطبيعي.

يبدأ Gemini افتراضيًا، ويضبط `AI_PRIMARY_PROVIDER=groq` لجعل Groq أساسيًا. تُنفذ الطلبات تسلسليًا، وتحدد `AI_MAX_RETRIES` و`AI_TIMEOUT_SECONDS` محاولات/مهلة كل مزود. يفحص `/status` قاعدة البيانات وحالة تهيئة المزودين؛ لا ينفذ طلبات مدفوعة إلى المزودين.

## أمان المتصفح

- قائمة صريحة للنطاقات المسموحة.
- حجب localhost والشبكات الخاصة ونطاقات الربط المحلي افتراضيًا.
- رفض بروتوكولات غير HTTP/HTTPS.
- عدم تجاوز CAPTCHA أو المصادقة أو القيود الأمنية.
- الإجراءات التدميرية تتطلب تأكيدًا صريحًا؛ وهي غير مفعلة افتراضيًا.
- لا يتم إرسال أو حل التقييمات الرسمية تلقائيًا.

## هيكل المشروع

```text
telegram-ai-agent/
├── src/
│   ├── main.py
│   ├── bot/
│   ├── providers/
│   ├── browser/
│   ├── services/
│   ├── config/
│   └── database/
├── tests/unit/
├── tests/integration/
├── tests/browser/
├── fixtures/
├── scripts/
├── .devcontainer/
├── .vscode/
├── .env.example
├── requirements.txt
└── requirements-dev.txt
```

## الاعتمادات المطلوبة فعليًا

- Gemini يحتاج `GEMINI_API_KEY`.
- Groq يحتاج `GROQ_API_KEY`.
- Telegram يحتاج `TELEGRAM_BOT_TOKEN` و`AUTHORIZED_TELEGRAM_USERS`.
- المتصفح يستخدم Playwright ولا يحتاج مفاتيح لخوادم الاختبار المحلية.
