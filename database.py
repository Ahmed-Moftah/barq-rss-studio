import sqlite3
import re
import datetime
import markdown
from config import Config

def get_connection(db_path=None):
    """Establish connection to SQLite database with dictionary-like row access."""
    path = db_path or Config.DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(db_path=None):
    """Initialize database tables and default configuration."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL DEFAULT 'reports',
                summary TEXT,
                content TEXT NOT NULL,
                content_html TEXT NOT NULL,
                author TEXT DEFAULT 'فريق تحرير برق',
                source TEXT DEFAULT 'إعداد تحريري',
                tags TEXT,
                image_url TEXT,
                image_caption TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                reading_time INTEGER DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS publish_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Default settings
        defaults = {
            "site_name": Config.SITE_NAME,
            "site_slogan": Config.SITE_SLOGAN,
            "site_description": Config.SITE_DESCRIPTION,
            "public_base_url": Config.PUBLIC_BASE_URL,
            "git_remote": Config.GIT_REMOTE,
            "git_branch": Config.GIT_BRANCH,
            "managing_editor": Config.SITE_MANAGING_EDITOR,
            "last_build_time": ""
        }
        for k, v in defaults.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
            
    conn.close()

def slugify(text):
    """
    Generate clean, URL-safe slug preserving Arabic letters, digits, and hyphens.
    """
    if not text:
        return f"report-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    # Replace whitespace and separators with hyphens
    clean = re.sub(r'[\s_]+', '-', text.strip())
    # Remove characters that are not alphanumeric or hyphens (keep Arabic unicode)
    clean = re.sub(r'[^\w\-]', '', clean, flags=re.UNICODE)
    # Remove consecutive hyphens
    clean = re.sub(r'-+', '-', clean).strip('-')
    if not clean:
        clean = f"report-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    return clean.lower()

def render_markdown(text):
    """Render markdown to clean HTML with common extensions."""
    if not text:
        return ""
    return markdown.markdown(
        text,
        extensions=[
            'extra',
            'nl2br',
            'tables',
            'fenced_code',
            'codehilite'
        ]
    )

def estimate_reading_time(text):
    """Estimate Arabic reading time in minutes (approx 150 words per minute)."""
    if not text:
        return 1
    words = len(text.split())
    minutes = max(1, round(words / 150))
    return minutes

def create_report(data, db_path=None):
    """Create a new editorial report."""
    conn = get_connection(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    title = data.get("title", "").strip()
    raw_slug = data.get("slug", "").strip() or title
    slug = slugify(raw_slug)
    
    # Ensure slug uniqueness
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM reports WHERE slug = ?", (slug,))
        if cursor.fetchone():
            slug = f"{slug}-{datetime.datetime.now().strftime('%H%M%S')}"
        
        content = data.get("content", "")
        content_html = render_markdown(content)
        reading_time = estimate_reading_time(content)
        status = data.get("status", "draft")
        published_at = now if status == "published" else data.get("published_at")
        
        cursor.execute("""
            INSERT INTO reports (
                title, slug, category, summary, content, content_html,
                author, source, tags, image_url, image_caption, status,
                reading_time, created_at, updated_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            slug,
            data.get("category", "reports"),
            data.get("summary", "").strip(),
            content,
            content_html,
            data.get("author", "فريق تحرير برق").strip(),
            data.get("source", "إعداد تحريري").strip(),
            data.get("tags", "").strip(),
            data.get("image_url", "").strip(),
            data.get("image_caption", "").strip(),
            status,
            reading_time,
            now,
            now,
            published_at
        ))
        report_id = cursor.lastrowid
    conn.close()
    return report_id

def update_report(report_id, data, db_path=None):
    """Update an existing editorial report."""
    conn = get_connection(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    existing = get_report_by_id(report_id, db_path)
    if not existing:
        conn.close()
        return False
        
    title = data.get("title", existing["title"]).strip()
    raw_slug = data.get("slug", "").strip() or existing["slug"]
    slug = slugify(raw_slug)
    
    with conn:
        cursor = conn.cursor()
        # Verify unique slug excluding this record
        cursor.execute("SELECT id FROM reports WHERE slug = ? AND id != ?", (slug, report_id))
        if cursor.fetchone():
            slug = f"{slug}-{datetime.datetime.now().strftime('%H%M%S')}"
            
        content = data.get("content", existing["content"])
        content_html = render_markdown(content)
        reading_time = estimate_reading_time(content)
        status = data.get("status", existing["status"])
        
        published_at = existing["published_at"]
        if status == "published" and not published_at:
            published_at = now
            
        cursor.execute("""
            UPDATE reports SET
                title = ?,
                slug = ?,
                category = ?,
                summary = ?,
                content = ?,
                content_html = ?,
                author = ?,
                source = ?,
                tags = ?,
                image_url = ?,
                image_caption = ?,
                status = ?,
                reading_time = ?,
                updated_at = ?,
                published_at = ?
            WHERE id = ?
        """, (
            title,
            slug,
            data.get("category", existing["category"]),
            data.get("summary", existing["summary"]),
            content,
            content_html,
            data.get("author", existing["author"]),
            data.get("source", existing["source"]),
            data.get("tags", existing["tags"]),
            data.get("image_url", existing["image_url"]),
            data.get("image_caption", existing["image_caption"]),
            status,
            reading_time,
            now,
            published_at,
            report_id
        ))
    conn.close()
    return True

def delete_report(report_id, db_path=None):
    """Delete a report by ID."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.close()
    return True

def get_report_by_id(report_id, db_path=None):
    """Retrieve single report by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_report_by_slug(slug, db_path=None):
    """Retrieve single report by its unique slug."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def list_reports(status=None, category=None, search=None, limit=None, offset=0, db_path=None):
    """List reports with optional filters and pagination."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT * FROM reports WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (title LIKE ? OR summary LIKE ? OR content LIKE ? OR tags LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])
        
    query += " ORDER BY CASE WHEN published_at IS NOT NULL THEN published_at ELSE updated_at END DESC"
    
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def count_reports(status=None, category=None, db_path=None):
    """Count reports matching specific filters."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT COUNT(*) as count FROM reports WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0

def get_dashboard_stats(db_path=None):
    """Compile aggregated metrics for the studio dashboard."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM reports")
    total = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as published FROM reports WHERE status = 'published'")
    published = cursor.fetchone()["published"]
    
    cursor.execute("SELECT COUNT(*) as drafts FROM reports WHERE status = 'draft'")
    drafts = cursor.fetchone()["drafts"]
    
    cursor.execute("SELECT category, COUNT(*) as count FROM reports GROUP BY category")
    by_category = {row["category"]: row["count"] for row in cursor.fetchall()}
    
    cursor.execute("SELECT value FROM settings WHERE key = 'last_build_time'")
    last_build_row = cursor.fetchone()
    last_build_time = last_build_row["value"] if last_build_row else None
    
    conn.close()
    return {
        "total": total,
        "published": published,
        "drafts": drafts,
        "by_category": by_category,
        "last_build_time": last_build_time
    }

def get_setting(key, default=None, db_path=None):
    """Get single configuration setting."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value, db_path=None):
    """Set or update configuration setting."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.close()

def log_publish_action(action, status, message, details="", db_path=None):
    """Record an audit trail of RSS builds and GitHub publication events."""
    conn = get_connection(db_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with conn:
        conn.execute("""
            INSERT INTO publish_logs (action, status, message, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (action, status, message, details, now))
    conn.close()

def get_recent_logs(limit=8, db_path=None):
    """Retrieve latest activity logs."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM publish_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def seed_sample_data(db_path=None):
    """Seed initial high-quality Arabic editorial reports if database is empty."""
    if count_reports(db_path=db_path) > 0:
        return
        
    sample_reports = [
        {
            "title": "تحولات ممرات التجارة الإقليمية: خريطة سلاسل الإمداد الجديدة",
            "slug": "regional-trade-corridors-supply-chains-2026",
            "category": "economy",
            "summary": "قراءة تحليلية في إعادة تشكيل موانئ وممرات الشحن الإقليمية وأثر التحولات الجيوسياسية على استقرار خطوط الإمداد العالمية.",
            "content": """## خريطة استراتيجية جديدة

تشهد المنطقة تحولاً جذرياً في بنيتها اللوجستية، حيث تتسابق الاقتصادات الإقليمية على توسعة الموانئ والمحطات البحرية وتدشين شبكات سكك حديدية عابرة للحدود.

### دوافع إعادة التموضع

1. **تقليل الاعتماد على نقاط الاختناق البحرية التقليدية**: البحث عن مسارات برية وبحرية بديلة وسريعة.
2. **تسريع وتيرة التجارة البينية**: رفع معدل الربط التجاري والصناعي المباشر.
3. **التكامل مع الموانئ الذكية**: توظيف إنترنت الأشياء والذكاء الاصطناعي في إدارة الحاويات وتتبع حركة البضائع.

> "لم تعد الممرات التجارية مجرد خطوط نقل بضائع، بل أضحت ركائز للسيادة الاقتصادية وبناء التحالفات الجيواقتصادية الجديدة."

### الخلاصة والتوقعات

يتوقع الخبراء أن تشهد السنوات الثلاث المقبلة ارتفاعاً بنسبة 28% في حجم التجارة المنقولة عبر الممرات المتعددة الوسائط، مما يعزز المرونة الاقتصادية في مواجهة التقلبات الدولية.""",
            "author": "وحدة التحليلات الاقتصادية - برق",
            "source": "إعداد تحريري موسع",
            "tags": "اقتصاد, سلاسل الإمداد, موانئ, تجارة إقليمية",
            "image_url": "https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=1200&q=80",
            "image_caption": "حركة الحاويات والموانئ التجارية الحديثة",
            "status": "published"
        },
        {
            "title": "الذكاء الاصطناعي السيادي: استراتيجيات الشرق الأوسط لبناء نماذج لغوية مستقلة",
            "slug": "sovereign-ai-arabic-llm-strategies",
            "category": "tech",
            "summary": "كيف تعمل مراكز الأبحاث والمبادرات التكنولوجية في العالم العربي على تدريب نماذج لغوية ضخمة تضمن الخصوصية الثقافية والسيادة الرقمية.",
            "content": """## صعود مفهوم السيادة الرقمية

مع تسارع سباق الذكاء الاصطناعي التوليدي حول العالم، تبرز مسألة **السيادة التكنولوجية والبيانية** كأولوية قصوى للدول والمؤسسات الإعلامية والبحثية.

### ركائز بناء النماذج اللغوية العربية

* **بناء مجموعات بيانات تدريبية موثوقة**: تنقية ملايين النصوص باللغة العربية الفصحى بمختلف فروعها المعرفية.
* **البنية التحتية للحوسبة السحابية**: الاستثمار في مراكز بيانات وطنية فائقة القدرة.
* **الأمان اللغوي والثقافي**: تدريب النماذج على استيعاب السياق الحضاري والخصوصيات التشريعية دون تحيز غربي أو تشويه معجمي.

### التحديات القائمة

تتمثل العقبة الكبرى في وفرة الرقائق الإلكترونية المتخصصة والحاجة إلى كوادر بحثية متقدمة في هندسة النماذج العصبية التوليدية.""",
            "author": "مختبر برق للتقنية والإعلام",
            "source": "ChatGPT مع معالجة وتدقيق تحريري",
            "tags": "ذكاء اصطناعي, نماذج عربية, سيادة تقنية, بيانات",
            "image_url": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1200&q=80",
            "image_caption": "تطور الذكاء الاصطناعي والحوسبة اللغوية المتقدمة",
            "status": "published"
        },
        {
            "title": "تقدير موقف: موازين القوى في البحر الأحمر وانعكاساتها الاستراتيجية",
            "slug": "strategic-assessment-red-sea-balance-of-power",
            "category": "analysis",
            "summary": "دراسة متأنية للتحركات البحرية الإقليمية والدولية في مضيق باب المندب وتأثيراتها المتوقعة على الاستقرار الأمني الإقليمي.",
            "content": """## خلفية المشهد

يشكل البحر الأحمر شرياناً حيوياً يمر عبره أكثر من 12% من إجمالي حركة التجارة البحرية العالمية وما يقرب من ثلث حركة الحاويات العالمية.

### سيناريوهات التطور الميداني

* **السيناريو الأول**: استمرار نمط الاستنزاف المحدود مع بقاء وتيرة الشحن تحت الحماية البحرية المشتركة.
* **السيناريو الثاني**: التوصل إلى تفاهمات تهدئة إقليمية تنعكس مباشرة على حركة الملاحة.
* **السيناريو الثالث**: تصعيد مفاجئ يجبر شركات الشحن العالمية على التوسع الدائم في طريق رأس الرجاء الصالح.

### التوصيات لصناع القرار

ضرورة تعزيز قنوات التنسيق البحري المشترك ودعم استراتيجيات خفض التصعيد لمنع تحول الممر إلى ساحة صراع مفتوح.""",
            "author": "مركز برق للدراسات الاستراتيجية",
            "source": "إعداد استراتيجي خاص",
            "tags": "أمن بحري, البحر الأحمر, جيوسياسة, تقدير موقف",
            "image_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1200&q=80",
            "image_caption": "مضيق مائي واستراتيجيات الأمن الملاحي",
            "status": "published"
        },
        {
            "title": "أزمة المياه العذبة ومشاريع التحلية بالطاقة المتجددة: مسودة تقرير تحليلي",
            "slug": "freshwater-desalination-renewable-energy-draft",
            "category": "reports",
            "summary": "مسودة عمل ترصد الجيل الجديد من محطات تحلية مياه البحر المعتمدة على الطاقة الشمسية وطاقة الرياح.",
            "content": """## نظرة عامة على أزمة الشح المائي

تتطلب التنمية المستدامة حلولاً جذرية لخفض البصمة الكربونية لمحطات التحلية التقليدية.

### المحاور الجاري تدقيقها:
1. نسبة خفض استهلاك الكهرباء لكل متر مكعب من المياه المحلاة.
2. إدارة المحلول الملحي المركز وحماية البيئة البحرية.
3. خطط الربط مع مزارع الطاقة الكهروضوئية.""",
            "author": "فريق التحرير - قسم البيئة والتنمية",
            "source": "مسودة واردة من ChatGPT",
            "tags": "بيئة, طاقة متجددة, تحلية مياه, استدامة",
            "image_url": "",
            "image_caption": "",
            "status": "draft"
        }
    ]
    
    for item in sample_reports:
        create_report(item, db_path=db_path)
