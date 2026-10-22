import os
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from config import Config
import database
import rss_generator

def check_public_url_reachability(url=None, timeout=3):
    """
    Check if the public GitHub Pages XML feed URL is actually accessible online.
    Returns dictionary with status code and accessibility flag.
    """
    target = url or f"{Config.PUBLIC_BASE_URL}/feed.xml"
    req = urllib.request.Request(
        target,
        headers={"User-Agent": "BARQ-RSS-Studio-Validator/2.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            return {
                "accessible": (code == 200),
                "status_code": code,
                "url": target,
                "error": None
            }
    except urllib.error.HTTPError as e:
        code = e.code
        try:
            e.close()
        except Exception:
            pass
        return {
            "accessible": False,
            "status_code": code,
            "url": target,
            "error": f"HTTP {code}: {e.reason}"
        }
    except Exception as e:
        return {
            "accessible": False,
            "status_code": None,
            "url": target,
            "error": str(e)
        }

def render_static_article_html(report, base_url, site_name):
    """
    Generate clean, standalone editorial HTML page for GitHub Pages hosting.
    """
    title = report.get("title", "")
    summary = report.get("summary", "")
    content_html = report.get("content_html", "")
    author = report.get("author", "فريق تحرير برق")
    source = report.get("source", "إعداد تحريري")
    tags = [t.strip() for t in (report.get("tags") or "").split(",") if t.strip()]
    image_url = report.get("image_url", "")
    image_caption = report.get("image_caption", "")
    reading_time = report.get("reading_time", 3)
    slug = report.get("slug", "")
    article_url = f"{base_url}/articles/{slug}.html"
    
    cat_id = report.get("category", "reports")
    cat_obj = Config.get_category_by_id(cat_id)
    cat_name = cat_obj.get("name", "تقارير")
    
    tags_html = "".join([f'<span class="badge tag-badge">{t}</span>' for t in tags])
    
    image_block = ""
    if image_url:
        caption_html = f'<figcaption class="article-caption">{image_caption}</figcaption>' if image_caption else ""
        image_block = f'''
        <figure class="article-cover">
            <img src="{image_url}" alt="{title}" loading="lazy" />
            {caption_html}
        </figure>
        '''

    html = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {site_name}</title>
    <meta name="description" content="{summary}">
    <link rel="canonical" href="{article_url}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{summary}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{article_url}">
    {f'<meta property="og:image" content="{image_url}">' if image_url else ""}
    
    <!-- Prevent SEO duplication with primary RSS consumer -->
    <meta name="robots" content="noindex, nofollow">
    
    <!-- RSS Autodiscovery -->
    <link rel="alternate" type="application/rss+xml" title="خلاصة تقارير برق RSS 2.0" href="{base_url}/feed.xml">
    <link rel="alternate" type="application/rss+xml" title="خلاصة {cat_name}" href="{base_url}/feeds/{cat_id}.xml">

    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-body: #0b1120;
            --surface-card: #131c31;
            --surface-card-hover: #1c2744;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-gold: #f59e0b;
            --accent-blue: #38bdf8;
            --border-subtle: #1e293b;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-body);
            color: var(--text-main);
            font-family: 'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, 'Segoe UI', Tahoma, sans-serif;
            line-height: 1.85;
            padding: 0;
            direction: rtl;
        }}
        .header-bar {{
            background: rgba(11, 17, 32, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--border-subtle);
            padding: 1rem 1.5rem;
            position: sticky;
            top: 0;
            z-index: 50;
        }}
        .header-container {{
            max-width: 860px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .brand-link {{
            color: var(--accent-gold);
            font-size: 1.15rem;
            font-weight: 800;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .feed-btn {{
            background: #2563eb;
            color: #ffffff;
            font-size: 0.85rem;
            font-weight: 600;
            padding: 0.45rem 0.9rem;
            border-radius: 6px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .container {{
            max-width: 820px;
            margin: 2.5rem auto 5rem;
            padding: 0 1.25rem;
        }}
        .article-card {{
            background: var(--surface-card);
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 2.5rem 2.2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        }}
        .article-meta-top {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.25rem;
            font-size: 0.85rem;
        }}
        .cat-badge {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-gold);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-weight: 600;
        }}
        .meta-item {{
            color: var(--text-muted);
        }}
        .article-title {{
            font-family: 'Cairo', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.35;
            color: #ffffff;
            margin-bottom: 1.25rem;
        }}
        .article-summary {{
            font-size: 1.15rem;
            color: #cbd5e1;
            background: rgba(255, 255, 255, 0.03);
            border-right: 4px solid var(--accent-gold);
            padding: 1rem 1.25rem;
            border-radius: 0 8px 8px 0;
            margin-bottom: 2rem;
        }}
        .article-cover img {{
            width: 100%;
            height: auto;
            max-height: 440px;
            object-fit: cover;
            border-radius: 10px;
            margin-bottom: 0.5rem;
        }}
        .article-caption {{
            color: var(--text-muted);
            font-size: 0.8rem;
            text-align: center;
            margin-bottom: 2rem;
        }}
        .article-body {{
            font-size: 1.1rem;
            color: #e2e8f0;
        }}
        .article-body h2 {{
            font-family: 'Cairo', sans-serif;
            font-size: 1.5rem;
            color: var(--accent-gold);
            margin: 2rem 0 1rem;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid var(--border-subtle);
        }}
        .article-body h3 {{
            font-family: 'Cairo', sans-serif;
            font-size: 1.25rem;
            color: #ffffff;
            margin: 1.5rem 0 0.8rem;
        }}
        .article-body p {{
            margin-bottom: 1.25rem;
        }}
        .article-body ul, .article-body ol {{
            margin: 1rem 1.5rem 1.5rem 0;
            padding-right: 1rem;
        }}
        .article-body li {{
            margin-bottom: 0.5rem;
        }}
        .article-body blockquote {{
            background: rgba(56, 189, 248, 0.08);
            border-right: 4px solid var(--accent-blue);
            padding: 1rem 1.25rem;
            border-radius: 0 8px 8px 0;
            font-style: italic;
            margin: 1.5rem 0;
            color: #f1f5f9;
        }}
        .article-footer {{
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-subtle);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        .tag-badge {{
            background: rgba(255, 255, 255, 0.06);
            color: #94a3b8;
            font-size: 0.8rem;
            padding: 0.3rem 0.65rem;
            border-radius: 6px;
            margin-left: 0.4rem;
        }}
        .back-link {{
            color: var(--accent-gold);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.95rem;
        }}
    </style>
</head>
<body>
    <header class="header-bar">
        <div class="header-container">
            <a href="{base_url}/" class="brand-link">
                <span>⚡ {site_name}</span>
            </a>
            <div style="display: flex; gap: 0.5rem;">
                <a href="{base_url}/feed.xml" class="feed-btn" target="_blank">
                    <span>خلاصة RSS</span> 📡
                </a>
                <a href="{base_url}/" class="feed-btn" style="background: #334155;">
                    <span>الرئيسية</span> 🏠
                </a>
            </div>
        </div>
    </header>

    <main class="container">
        <article class="article-card">
            <div class="article-meta-top">
                <span class="cat-badge">{cat_name}</span>
                <span class="meta-item">✍️ {author}</span>
                <span class="meta-item">⏳ قراءة {reading_time} دقائق</span>
                <span class="meta-item">📌 المصدر: {source}</span>
            </div>

            <h1 class="article-title">{title}</h1>

            {f'<div class="article-summary">{summary}</div>' if summary else ""}

            {image_block}

            <div class="article-body">
                {content_html}
            </div>

            <footer class="article-footer">
                <div class="tags-list">
                    {tags_html}
                </div>
                <a href="{base_url}/" class="back-link">← العودة إلى قائمة التقارير والخلاصات</a>
            </footer>
        </article>
    </main>
</body>
</html>
'''
    return html

def render_public_index_html(reports, categories_info, base_url, site_name, site_desc):
    """
    Generate modern Arabic RTL RSS Hub landing page for GitHub Pages.
    """
    category_cards_html = ""
    for cat in Config.CATEGORIES:
        cid = cat["id"]
        cname = cat["name"]
        cdesc = cat["description"]
        cfeed = f"{base_url}/feeds/{cid}.xml"
        
        # Count items
        c_count = sum(1 for r in reports if r.get("category") == cid)
        
        category_cards_html += f'''
        <div class="cat-card">
            <div class="cat-header">
                <span class="cat-pill" style="color: {cat['badge_color']}; background: {cat['badge_bg']};">{cname}</span>
                <span class="cat-count">{c_count} تقرير</span>
            </div>
            <p class="cat-desc">{cdesc}</p>
            <div class="cat-links">
                <a href="{cfeed}" target="_blank" class="rss-link-btn">
                    <span>خلاصة RSS</span> 📡
                </a>
                <button class="copy-btn" onclick="navigator.clipboard.writeText('{cfeed}'); alert('تم نسخ رابط الخلاصة!');">
                    <span>نسخ الرابط</span> 📋
                </button>
            </div>
        </div>
        '''

    articles_cards_html = ""
    for r in reports[:15]:
        slug = r.get("slug")
        title = r.get("title")
        summary = r.get("summary") or ""
        author = r.get("author") or "فريق تحرير برق"
        reading_time = r.get("reading_time", 3)
        cat_id = r.get("category", "reports")
        cat_obj = Config.get_category_by_id(cat_id)
        cat_name = cat_obj.get("name", "تقرير")
        art_url = f"{base_url}/articles/{slug}.html"
        
        articles_cards_html += f'''
        <article class="article-row">
            <div class="row-meta">
                <span class="cat-pill-sm">{cat_name}</span>
                <span class="row-author">✍️ {author}</span>
                <span class="row-time">⏳ {reading_time} د</span>
            </div>
            <h3 class="row-title">
                <a href="{art_url}">{title}</a>
            </h3>
            <p class="row-summary">{summary[:180]}{'...' if len(summary) > 180 else ''}</p>
            <div class="row-footer">
                <a href="{art_url}" class="read-more-btn">قراءة التقرير بالكامل ←</a>
            </div>
        </article>
        '''

    html = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_name} | بوابة خلاصات RSS والتقارير</title>
    <meta name="description" content="{site_desc}">
    <link rel="canonical" href="{base_url}/">
    
    <!-- RSS Autodiscovery -->
    <link rel="alternate" type="application/rss+xml" title="خلاصة تقارير برق الشاملة" href="{base_url}/feed.xml">
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --bg-body: #090e1a;
            --surface: #111a2e;
            --surface-hover: #16223d;
            --border: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-gold: #f59e0b;
            --accent-blue: #2563eb;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-body);
            color: var(--text-main);
            font-family: 'IBM Plex Sans Arabic', -apple-system, sans-serif;
            line-height: 1.8;
            direction: rtl;
        }}
        .header {{
            background: linear-gradient(180deg, #10192e 0%, #090e1a 100%);
            border-bottom: 1px solid var(--border);
            padding: 3.5rem 1.5rem 3rem;
            text-align: center;
        }}
        .brand-badge {{
            display: inline-block;
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-gold);
            padding: 0.35rem 1rem;
            border-radius: 30px;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 1rem;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}
        .site-title {{
            font-family: 'Cairo', sans-serif;
            font-size: 2.6rem;
            font-weight: 900;
            color: #ffffff;
            margin-bottom: 0.75rem;
            letter-spacing: -0.5px;
        }}
        .site-desc {{
            color: #cbd5e1;
            font-size: 1.15rem;
            max-width: 720px;
            margin: 0 auto 2rem;
        }}
        .master-feed-box {{
            display: inline-flex;
            flex-wrap: wrap;
            gap: 1rem;
            justify-content: center;
            align-items: center;
            background: var(--surface);
            padding: 1rem 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }}
        .feed-main-url {{
            direction: ltr;
            background: #060a14;
            color: #38bdf8;
            font-family: monospace;
            padding: 0.45rem 1rem;
            border-radius: 6px;
            border: 1px solid var(--border);
            font-size: 0.9rem;
        }}
        .btn-subscribe {{
            background: #f59e0b;
            color: #0b1120;
            font-weight: 700;
            padding: 0.5rem 1.25rem;
            border-radius: 8px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: opacity 0.2s;
        }}
        .btn-subscribe:hover {{ opacity: 0.9; }}
        .section {{
            max-width: 1040px;
            margin: 3.5rem auto;
            padding: 0 1.25rem;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.75rem;
        }}
        .section-title {{
            font-family: 'Cairo', sans-serif;
            font-size: 1.6rem;
            font-weight: 800;
            color: #ffffff;
        }}
        .cats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
            gap: 1.25rem;
        }}
        .cat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s, border-color 0.2s;
        }}
        .cat-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(245, 158, 11, 0.4);
        }}
        .cat-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .cat-pill {{
            font-size: 0.8rem;
            font-weight: 700;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
        }}
        .cat-count {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        .cat-desc {{
            color: #cbd5e1;
            font-size: 0.92rem;
            margin-bottom: 1.25rem;
            flex-grow: 1;
        }}
        .cat-links {{
            display: flex;
            gap: 0.6rem;
        }}
        .rss-link-btn {{
            flex: 1;
            background: #1e293b;
            color: #f8fafc;
            text-decoration: none;
            text-align: center;
            padding: 0.45rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            border: 1px solid #334155;
        }}
        .copy-btn {{
            background: transparent;
            color: var(--text-muted);
            border: 1px solid #334155;
            padding: 0.45rem 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-family: inherit;
        }}
        .copy-btn:hover {{
            color: #ffffff;
            border-color: var(--accent-gold);
        }}
        .articles-list {{
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }}
        .article-row {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.75rem;
            transition: background 0.2s;
        }}
        .article-row:hover {{
            background: var(--surface-hover);
        }}
        .row-meta {{
            display: flex;
            gap: 0.75rem;
            align-items: center;
            font-size: 0.82rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}
        .cat-pill-sm {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-gold);
            padding: 0.15rem 0.6rem;
            border-radius: 4px;
            font-weight: 600;
        }}
        .row-title {{
            font-family: 'Cairo', sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        .row-title a {{
            color: #ffffff;
            text-decoration: none;
        }}
        .row-title a:hover {{
            color: var(--accent-gold);
        }}
        .row-summary {{
            color: #cbd5e1;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }}
        .read-more-btn {{
            color: var(--accent-gold);
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            padding: 3rem 1rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <header class="header">
        <span class="brand-badge">⚡ شبكة برق الإعلامية</span>
        <h1 class="site-title">{site_name}</h1>
        <p class="site-desc">{site_desc}</p>
        
        <div class="master-feed-box">
            <span>📡 الخلاصة الرئيسية:</span>
            <span class="feed-main-url">{base_url}/feed.xml</span>
            <a href="{base_url}/feed.xml" target="_blank" class="btn-subscribe">
                <span>فتح الخلاصة</span>
            </a>
            <button class="copy-btn" onclick="navigator.clipboard.writeText('{base_url}/feed.xml'); alert('تم نسخ رابط الخلاصة الشاملة!');">
                نسخ الرابط 📋
            </button>
        </div>
    </header>

    <main>
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">خلاصات الأقسام المتخصصة (RSS 2.0)</h2>
            </div>
            <div class="cats-grid">
                {category_cards_html}
            </div>
        </section>

        <section class="section">
            <div class="section-header">
                <h2 class="section-title">أحدث التقارير التحريرية المنشورة</h2>
            </div>
            <div class="articles-list">
                {articles_cards_html}
            </div>
        </section>
    </main>

    <footer class="footer">
        <p>جميع الحقوق محفوظة © شبكة برق الإعلامية 2026 | مولد خلاصات RSS 2.0 المتوافق قياسياً مع GitHub Pages</p>
    </footer>
</body>
</html>
'''
    return html

def export_static_site(output_dir=None, db_path=None):
    """
    Build the complete static output ready for GitHub Pages:
    - Master feed.xml and rss.xml
    - Per-category feeds feeds/*.xml
    - Article static reader pages articles/*.html
    - Public index.html portal
    - feed-catalog.json
    """
    dist_path = Path(output_dir or Config.DIST_DIR)
    articles_dir = dist_path / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Build feeds
    feed_results = rss_generator.build_all_feeds(output_dir=dist_path, db_path=db_path)
    
    base_url = database.get_setting("public_base_url", Config.PUBLIC_BASE_URL, db_path=db_path).rstrip("/")
    site_name = database.get_setting("site_name", Config.SITE_NAME, db_path=db_path)
    site_desc = database.get_setting("site_description", Config.SITE_DESCRIPTION, db_path=db_path)
    
    # 2. Fetch all published reports
    published = database.list_reports(status="published", db_path=db_path)
    
    exported_articles = []
    # 3. Generate article HTML pages
    for report in published:
        slug = report.get("slug")
        if not slug:
            continue
        art_html = render_static_article_html(report, base_url, site_name)
        art_file = articles_dir / f"{slug}.html"
        art_file.write_text(art_html, encoding="utf-8")
        exported_articles.append(str(art_file))
        
    # 4. Generate public portal index.html
    index_html = render_public_index_html(published, Config.CATEGORIES, base_url, site_name, site_desc)
    index_file = dist_path / "index.html"
    index_file.write_text(index_html, encoding="utf-8")
    
    # 5. Generate feed catalog JSON
    catalog_data = {
        "site_name": site_name,
        "base_url": base_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "master_feed": f"{base_url}/feed.xml",
        "category_feeds": [
            {
                "id": c["id"],
                "name": c["name"],
                "url": f"{base_url}/feeds/{c['id']}.xml",
                "count": c["count"]
            }
            for c in feed_results["category_feeds"]
        ],
        "published_count": len(published)
    }
    catalog_file = dist_path / "feed-catalog.json"
    catalog_file.write_text(json.dumps(catalog_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # 6. Create .nojekyll to ensure GitHub Pages serves XML & raw assets directly without Jekyll
    nojekyll_file = dist_path / ".nojekyll"
    nojekyll_file.touch(exist_ok=True)
    
    database.log_publish_action(
        action="build_static_site",
        status="success",
        message=f"تم بناء {len(published)} تقرير وجميع خلاصات RSS بنجاح",
        details=f"المسار: {dist_path}",
        db_path=db_path
    )
    
    return {
        "success": True,
        "dist_dir": str(dist_path),
        "articles_count": len(exported_articles),
        "feeds_count": len(feed_results["category_feeds"]) + 1,
        "feed_results": feed_results,
        "index_file": str(index_file)
    }

def publish_to_github(commit_message=None, output_dir=None, db_path=None):
    """
    Automate building static site and committing/pushing to Git/GitHub Pages.
    """
    # First export static files
    export_result = export_static_site(output_dir=output_dir, db_path=db_path)
    
    msg = commit_message or f"تحديث ونشر خلاصات برق التحريرية [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}]"
    
    # Check git repo status in current workspace
    repo_dir = str(Config.BASE_DIR)
    git_remote = database.get_setting("git_remote", Config.GIT_REMOTE, db_path=db_path)
    git_branch = database.get_setting("git_branch", Config.GIT_BRANCH, db_path=db_path)
    
    def run_git(args):
        git_env = os.environ.copy()
        git_env["GIT_TERMINAL_PROMPT"] = "0"
        return subprocess.run(
            ["git"] + args,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            env=git_env
        )
        
    git_check = run_git(["status"])
    if git_check.returncode != 0:
        # Not a git repo or git error
        database.log_publish_action(
            action="git_publish",
            status="info",
            message="تم تصدير ملفات RSS بنجاح محلياً (المستودع لم يتم تهيئة Git به بعد)",
            details=git_check.stderr,
            db_path=db_path
        )
        return {
            "success": True,
            "git_executed": False,
            "message": "تم تصدير جميع خلاصات RSS وصفحات الموقع محلياً إلى مجلد dist بنجاح.",
            "export_result": export_result
        }
        
    # If git repo exists, stage dist files and commit to main development branch
    run_git(["add", "dist"])
    commit_res = run_git(["commit", "-m", msg])
    
    # Check if remote is configured
    remote_check = run_git(["remote", "get-url", git_remote])
    push_output = ""
    push_success = False
    
    if remote_check.returncode == 0:
        # Create a root tree containing ONLY the contents of dist/
        tree_res = run_git(["write-tree", "--prefix=dist/"])
        if tree_res.returncode == 0:
            tree_id = tree_res.stdout.strip()
            
            # Find parent for gh-pages branch to maintain linear history
            parent_args = []
            remote_parent = run_git(["rev-parse", "--verify", f"{git_remote}/{git_branch}"])
            if remote_parent.returncode == 0:
                parent_args = ["-p", remote_parent.stdout.strip()]
            else:
                local_parent = run_git(["rev-parse", "--verify", git_branch])
                if local_parent.returncode == 0:
                    parent_args = ["-p", local_parent.stdout.strip()]
                    
            commit_tree_res = run_git(["commit-tree", tree_id] + parent_args + ["-m", msg])
            if commit_tree_res.returncode == 0:
                gh_pages_commit = commit_tree_res.stdout.strip()
                # Update local gh-pages branch
                run_git(["update-ref", f"refs/heads/{git_branch}", gh_pages_commit])
                
                # Push ONLY dist contents to the root of gh-pages branch on GitHub
                push_res = run_git(["push", git_remote, f"{gh_pages_commit}:refs/heads/{git_branch}"])
                push_output = push_res.stdout or push_res.stderr
                push_success = (push_res.returncode == 0)
                
                # Also push main branch to keep development code in sync
                run_git(["push", git_remote, "main"])
                
                if push_success:
                    status_label = "success"
                    summary_msg = f"تم توليد ونشر محتويات مجلد dist حصرياً إلى جذر فرع {git_branch} على GitHub Pages بنجاح."
                else:
                    status_label = "warning"
                    summary_msg = f"تم التوليد محلياً، لكن تعذر الدفع لفرع {git_branch}: {push_output}"
            else:
                status_label = "warning"
                summary_msg = f"فشل إنشاء نقطة الالتزام لفرع {git_branch}: {commit_tree_res.stderr}"
        else:
            status_label = "warning"
            summary_msg = f"فشل تجهيز شجرة مجلد dist: {tree_res.stderr}"
    else:
        push_output = f"الريموت '{git_remote}' غير مربوط بمستودع خارجي حالياً."
        status_label = "local_only"
        summary_msg = f"تم توليد الخلاصات محلياً بنجاح في مجلد dist. (الرفع البعيد معلق: ريموت '{git_remote}' غير مربوط بمستودع GitHub بعد)."
        
    database.log_publish_action(
        action="git_publish",
        status=status_label,
        message=summary_msg,
        details=f"Commit: {commit_res.stdout}\nPush: {push_output}",
        db_path=db_path
    )
    
    # Check public URL reachability for real diagnostic feedback
    public_base = database.get_setting("public_base_url", Config.PUBLIC_BASE_URL, db_path=db_path)
    public_reachability = check_public_url_reachability(f"{public_base}/feed.xml")
    
    return {
        "success": True,  # Process ran without crash
        "local_generation_success": True,
        "remote_deployment_success": push_success,
        "status_label": status_label,
        "message": summary_msg,
        "git_executed": True,
        "pushed": push_success,
        "commit_message": msg,
        "git_output": f"{commit_res.stdout}\n{push_output}".strip(),
        "export_result": export_result,
        "public_url_diagnostic": public_reachability
    }
