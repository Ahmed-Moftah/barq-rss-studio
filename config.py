import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DIST_DIR = BASE_DIR / "dist"

# Ensure runtime directories exist
DATA_DIR.mkdir(exist_ok=True)
DIST_DIR.mkdir(exist_ok=True)

class Config:
    BASE_DIR = str(BASE_DIR)
    SECRET_KEY = os.environ.get("SECRET_KEY", "barq-editorial-rss-secret-key-2026")
    DB_PATH = str(DATA_DIR / "studio.db")
    DIST_DIR = str(DIST_DIR)
    
    # Editorial & Site Identity
    SITE_NAME = "برق | استوديو التقارير التحريرية"
    SITE_SLOGAN = "منظومة إدارة المحتوى التحريري وتوليد خلاصات RSS القياسية"
    SITE_DESCRIPTION = "منصة مستقلة لإدارة وصياغة التقارير التحريرية لشبكة برق، وتوليد خلاصات RSS 2.0 المتوافقة قياسياً والنشر السريع على GitHub Pages."
    SITE_LANGUAGE = "ar"
    SITE_MANAGING_EDITOR = "فريق تحرير برق (editorial@barq.local)"
    SITE_WEBMASTER = "قسم التقنية والنشر (tech@barq.local)"
    SITE_COPYRIGHT = "جميع الحقوق محفوظة © شبكة برق الإعلامية 2026"
    
    # Default Public Base URL for GitHub Pages / Feed links
    # Users can update this in the application settings interface or via environment variable
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://barq-media.github.io/rss-studio").rstrip("/")
    
    # Git & GitHub Pages automated deployment configuration
    GIT_REMOTE = os.environ.get("GIT_REMOTE", "origin")
    GIT_BRANCH = os.environ.get("GIT_BRANCH", "gh-pages")
    GIT_AUTO_COMMIT = os.environ.get("GIT_AUTO_COMMIT", "True").lower() in ("true", "1", "yes")
    
    # Standard Editorial Categories (Configurable)
    CATEGORIES = [
        {
            "id": "politics",
            "name": "شؤون سياسية",
            "slug": "politics",
            "description": "قراءات معمقة وتحليلات للأحداث والتطورات السياسية إقليمياً ودولياً",
            "badge_color": "#1d4ed8",  # blue
            "badge_bg": "#dbeafe"
        },
        {
            "id": "economy",
            "name": "اقتصاد وأعمال",
            "slug": "economy",
            "description": "تقارير الأسواق والتحولات المالية والاستثمارات وسلاسل الإمداد",
            "badge_color": "#047857",  # green
            "badge_bg": "#d1fae5"
        },
        {
            "id": "health",
            "name": "صحة وعافية",
            "slug": "health",
            "description": "تغطيات وأبحاث الطب والصحة العامة والتطورات العلاجية",
            "badge_color": "#0891b2",  # cyan
            "badge_bg": "#cffafe"
        },
        {
            "id": "arts",
            "name": "ثقافة وفنون",
            "slug": "arts",
            "description": "تغطيات فكرية وأدبية وفنية ونقد سينمائي وإبداعي",
            "badge_color": "#d97706",  # amber
            "badge_bg": "#fef3c7"
        },
        {
            "id": "sports",
            "name": "شؤون رياضية",
            "slug": "sports",
            "description": "تحليلات الأداء الرياضي والبطولات الإقليمية والعالمية",
            "badge_color": "#ea580c",  # orange
            "badge_bg": "#ffedd5"
        },
        {
            "id": "tech",
            "name": "تكنولوجيا وابتكار",
            "slug": "tech",
            "description": "مستجدات الذكاء الاصطناعي، الأمن السيبراني والاقتصاد الرقمي",
            "badge_color": "#6d28d9",  # purple
            "badge_bg": "#ede9fe"
        },
        {
            "id": "news",
            "name": "أخبار عامة",
            "slug": "news",
            "description": "متابعات إخبارية شاملة وموجز يومي لأبرز الأحداث",
            "badge_color": "#475569",  # slate
            "badge_bg": "#f1f5f9"
        },
        {
            "id": "analysis",
            "name": "تقديرات موقف",
            "slug": "analysis",
            "description": "أوراق تقدير موقف وتحليلات استراتيجية للأبعاد الأمنية والجيوسياسية",
            "badge_color": "#b45309",  # amber
            "badge_bg": "#fef3c7"
        },
        {
            "id": "reports",
            "name": "تقارير خاصة",
            "slug": "reports",
            "description": "تقارير استقصائية وتغطيات شاملة للأحداث البارزة",
            "badge_color": "#b91c1c",  # red
            "badge_bg": "#fee2e2"
        },
        {
            "id": "investigations",
            "name": "تحقيقات استقصائية",
            "slug": "investigations",
            "description": "ملفات بحثية استقصائية معززة بالبيانات والقرائن",
            "badge_color": "#0f766e",  # teal
            "badge_bg": "#ccfbf1"
        }
    ]

    @classmethod
    def get_category_by_id(cls, cat_id):
        for cat in cls.CATEGORIES:
            if cat["id"] == cat_id or cat["slug"] == cat_id:
                return cat
        return cls.CATEGORIES[8]  # Default to 'reports'
