# استوديو برق للتقارير والخلاصات (BARQ Editorial RSS Studio)

تطبيق محلي خفيف الوزن ومستقل بالكامل لإدارة التقارير والتحليلات التحريرية باللغة العربية، وتوليد خلاصات **RSS 2.0** القياسية متعددة التصنيفات ونشرها آلياً على **GitHub Pages**.

---

## ✨ المميزات الرئيسية

- **منظومة مستقلة بالكامل**: لا تعتمد على موقع برق القائم، ولا على لارافيل، ولا على واجهات ذكاء اصطناعي مدفوعة.
- **واجهة عربية احترافية (RTL)**: تصميم صحفي حديث بخطوط *Cairo* للعناوين و*IBM Plex Sans Arabic* للنصوص والبيانات، مع لوحة ألوان تناسب المنصات الإخبارية الرائدة.
- **استيراد ذكي لتقارير ChatGPT**: محلل نصوص مدمج يقبل مخرجات ChatGPT بصيغ Markdown أو نصوص مهيكلة أو JSON، ويستخرج تلقائياً: العنوان، التصنيف، الموجز، الوسوم، الكاتب، والمحتوى.
- **خلاصات RSS 2.0 قياسية 100%**:
  - خلاصة رئيسية شاملة (`/feed.xml` و `/rss.xml`).
  - خلاصات فرعية متخصصة لكل قسم تحريري (`/feeds/{category}.xml`).
  - تواريخ بتنسيق **RFC 822** الصارم.
  - دعم وسوم `content:encoded` و `atom:link` و `dc:creator` و `<enclosure>` للصور البارزة.
  - تغليف النصوص العربية بعناية عبر كتل `CDATA` لضمان التوافق التام مع قارئات RSS العالمية (Feedly, Inoreader, NetNewsWire, Apple Podcasts/News, إلخ).
- **أتمتة النشر على GitHub Pages**:
  - تصدير موقع ثابت متكامل في مجلد `dist/` يضم بوابة خلاصات تفاعلية، صفحات قراءة مستقلة لكل تقرير، وملف فهرس `feed-catalog.json`.
  - أتمتة أوامر Git لعمل Commit وPush للفرع المخصص (`gh-pages`).
- **لوحة متابعة وتحكم شاملة**:
  - مؤشرات أداء لحظية (إجمالي التقارير، المنشور، المسودات، توزيع الأقسام).
  - محرر غني يدعم Markdown ومعاينة حية فورية ومكتبة وسوم وتحديد زمن القراءة التقديري.
  - سجل تتبع ومراجعة (Audit Log) لعمليات البناء والنشر.

---

## 🏗️ الهيكلية البرمجية

```text
barq-editorial-rss-studio/
├── app.py                  # خادم Flask ونقاط النهاية (Routes & APIs)
├── config.py               # الإعدادات والتصنيفات التحريرية وقيم البيئة
├── database.py             # طبقة بيانات SQLite ونماذج التقارير والسجلات
├── importer.py             # محلل نصوص ومسودات تقارير ChatGPT
├── rss_generator.py        # مولد خلاصات RSS 2.0 القياسية
├── github_publisher.py     # مولد الموقع الثابت وأتمتة النشر عبر Git
├── requirements.txt        # الحزم البرمجية الأساسية (Flask, markdown)
├── data/                   # قاعدة البيانات المحلية (SQLite)
├── dist/                   # مخرجات النشر الثابت لـ GitHub Pages
│   ├── index.html          # بوابة الخلاصات العامة
│   ├── feed.xml / rss.xml  # الخلاصات الرئيسية الموحدة
│   ├── feeds/              # خلاصات الأقسام التحريرية المتخصصة
│   └── articles/           # صفحات المقالات المستقلة
├── templates/              # قوالب واجهة المستخدم العربية (Jinja2)
├── static/                 # ملفات التنسيق CSS وسكربتات JS التفاعلية
└── tests/                  # حزمة الاختبارات المركزة
    ├── test_database.py
    ├── test_importer.py
    ├── test_rss.py
    ├── test_routes.py
    └── test_publisher.py
```

---

## 🚀 التشغيل السريع

### 1. إعداد البيئة الافتراضية
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. تشغيل التطبيق محلياً
```bash
python app.py
```
افتح المتصفح على: `http://127.0.0.1:5055`

---

## 🧪 تشغيل الاختبارات المركزة

```bash
source .venv/bin/activate
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🏷️ الأقسام التحريرية المعتمدة وخلاصاتها

| القسم التحريري | المعرّف (Slug) | رابط الخلاصة على GitHub Pages |
| :--- | :--- | :--- |
| **الخلاصة الشاملة** | `feed` | `https://ahmed-moftah.github.io/barq-rss-studio/feed.xml` |
| **شؤون سياسية** | `politics` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/politics.xml` |
| **اقتصاد وأعمال** | `economy` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/economy.xml` |
| **صحة وعافية** | `health` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/health.xml` |
| **ثقافة وفنون** | `arts` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/arts.xml` |
| **شؤون رياضية** | `sports` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/sports.xml` |
| **تكنولوجيا وابتكار** | `tech` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/tech.xml` |
| **أخبار عامة** | `news` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/news.xml` |
| **تقديرات موقف** | `analysis` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/analysis.xml` |
| **تقارير خاصة** | `reports` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/reports.xml` |
| **تحقيقات استقصائية**| `investigations` | `https://ahmed-moftah.github.io/barq-rss-studio/feeds/investigations.xml`|

---

## 🤖 كيفية استيراد تقارير ChatGPT

1. اطلب من ChatGPT صياغة التقرير مع ترويسة بسيطة مثل:
```markdown
# عنوان التقرير: تطورات استثمارات الطاقة المتجددة
**التصنيف:** اقتصاد وأعمال
**الموجز:** قراءة في تدفقات رؤوس الأموال نحو مشاريع الهيدروجين الأخضر.
**الوسوم:** طاقة متجددة, اقتصاد, استثمار
**الكاتب:** فريق التحليلات الاقتصادية

نص التقرير يبدأ هنا...
```
2. اضغط على زر **"استيراد مسودة من ChatGPT"** في الاستوديو.
3. الصق النص واضغط **"تحليل واستيراد للنموذج"**.
4. سيتم ملء حقول المحرر وتجهيز التقرير للمراجعة والنشر الفوري.
