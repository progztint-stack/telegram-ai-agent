# Telegram AI Browser Agent

مساعد آمن على Telegram يدعم Gemini وGroq ومتصفح Playwright وSQLite، وهو مصمم للاستخدام التعليمي واختبار صفحات HTML محلية فقط.

## المتطلبات

- Python 3.11 أو أحدث
- GitHub Codespaces أو بيئة Linux
- مفاتيح اختيارية لـGemini وGroq وتوكن Telegram

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

يعمل المشروع في وضع المحاكاة عند غياب مفاتيح المزودين وTelegram؛ لن يبدأ البوت الخارجي قبل توفر التوكن والمستخدمين المصرح لهم.

## إعداد الاعتمادات

عدّل ملف `.env` محليًا بالقيم التالية:

```dotenv
GEMINI_API_KEY=
GROQ_API_KEY=
TELEGRAM_BOT_TOKEN=
AUTHORIZED_TELEGRAM_USERS=123456789
BROWSER_HEADLESS=true
BROWSER_ALLOWED_DOMAINS=localhost,127.0.0.1
DATABASE_URL=sqlite:///./data/tasks.db
```

لا تضع مفاتيح حقيقية في Git أو Telegram أو السجلات.

### GitHub Codespaces Secrets

1. افتح إعدادات GitHub للحساب أو المستودع.
2. اختر **Secrets and variables > Codespaces**.
3. أضف الأسرار بالمسميات: `GEMINI_API_KEY`، `GROQ_API_KEY`، `TELEGRAM_BOT_TOKEN`، و`AUTHORIZED_TELEGRAM_USERS`.
4. أعِد إنشاء Codespace أو افتح جلسة جديدة.

## أوامر البوت

- `/start` البدء
- `/help` المساعدة
- `/status` حالة الإعدادات
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

لا يتم تشغيل البوت عند غياب `TELEGRAM_BOT_TOKEN`.

## المعمارية

- `src/providers`: واجهة موحدة وسلسلة فشل Gemini ثم Groq.
- `src/bot`: أوامر Telegram والتحكم بالتفويض.
- `src/browser`: إدارة Chromium والتصفح والتقاط الصور وفحص DOM.
- `src/services`: المهام والسياق والتقارير.
- `src/database`: تخزين SQLite.
- `fixtures`: صفحات HTML تجريبية محلية.

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
