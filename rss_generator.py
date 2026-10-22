import os
import email.utils
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from config import Config
import database

def format_rfc822(date_input):
    """
    Convert ISO string or datetime object to standard RFC 822 format (e.g., Thu, 22 Oct 2026 03:40:00 +0000).
    """
    if not date_input:
        dt = datetime.now(timezone.utc)
    elif isinstance(date_input, datetime):
        dt = date_input if date_input.tzinfo else date_input.replace(tzinfo=timezone.utc)
    else:
        try:
            # Handle ISO string with or without Z/offset
            clean_str = date_input.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc)
            
    return email.utils.format_datetime(dt)

def wrap_cdata(text):
    """Wrap string in XML CDATA block with safe escaping of any existing sequence."""
    if text is None:
        return "<![CDATA[]]>"
    safe_text = str(text).replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{safe_text}]]>"

def detect_mime_type(url):
    """Guess image mime type from file extension."""
    if not url:
        return "image/jpeg"
    lower = url.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".svg"):
        return "image/svg+xml"
    return "image/jpeg"

def generate_feed_xml(channel_info, items, self_url=None):
    """
    Generate standard-compliant RSS 2.0 XML string.
    """
    base_url = channel_info.get("base_url", Config.PUBLIC_BASE_URL).rstrip("/")
    site_title = channel_info.get("title", Config.SITE_NAME)
    site_link = channel_info.get("link", base_url)
    description = channel_info.get("description", Config.SITE_DESCRIPTION)
    language = channel_info.get("language", "ar")
    managing_editor = channel_info.get("managing_editor", Config.SITE_MANAGING_EDITOR)
    copyright_text = channel_info.get("copyright", Config.SITE_COPYRIGHT)
    last_build_date = format_rfc822(channel_info.get("last_build_date"))
    
    feed_self_link = self_url or f"{base_url}/feed.xml"
    
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">',
        '  <channel>',
        f'    <title>{wrap_cdata(site_title)}</title>',
        f'    <link>{xml_escape(site_link)}</link>',
        f'    <description>{wrap_cdata(description)}</description>',
        f'    <language>{language}</language>',
        f'    <copyright>{wrap_cdata(copyright_text)}</copyright>',
        f'    <managingEditor>{wrap_cdata(managing_editor)}</managingEditor>',
        f'    <lastBuildDate>{last_build_date}</lastBuildDate>',
        '    <generator>BARQ Editorial RSS Studio 2.0</generator>',
        f'    <atom:link href="{xml_escape(feed_self_link)}" rel="self" type="application/rss+xml" />',
        '    <image>',
        f'      <url>{xml_escape(base_url)}/assets/logo.png</url>',
        f'      <title>{wrap_cdata(site_title)}</title>',
        f'      <link>{xml_escape(site_link)}</link>',
        '    </image>'
    ]
    
    for item in items:
        # Determine article link
        slug = item.get("slug", "")
        article_url = f"{base_url}/articles/{slug}.html"
        item_title = item.get("title", "بدون عنوان")
        pub_date = format_rfc822(item.get("published_at") or item.get("created_at"))
        author = item.get("author") or "فريق تحرير برق"
        summary = item.get("summary") or ""
        content_html = item.get("content_html") or item.get("content") or ""
        
        # Category resolution
        cat_id = item.get("category", "reports")
        cat_obj = Config.get_category_by_id(cat_id)
        cat_name = cat_obj.get("name", cat_id) if cat_obj else cat_id
        
        xml_lines.append('    <item>')
        xml_lines.append(f'      <title>{wrap_cdata(item_title)}</title>')
        xml_lines.append(f'      <link>{xml_escape(article_url)}</link>')
        xml_lines.append(f'      <guid isPermaLink="true">{xml_escape(article_url)}</guid>')
        xml_lines.append(f'      <pubDate>{pub_date}</pubDate>')
        xml_lines.append(f'      <dc:creator>{wrap_cdata(author)}</dc:creator>')
        xml_lines.append(f'      <category>{wrap_cdata(cat_name)}</category>')
        
        if summary:
            xml_lines.append(f'      <description>{wrap_cdata(summary)}</description>')
        else:
            xml_lines.append(f'      <description>{wrap_cdata(item_title)}</description>')
            
        xml_lines.append(f'      <content:encoded>{wrap_cdata(content_html)}</content:encoded>')
        
        # Enclosure for feature image
        img_url = item.get("image_url")
        if img_url:
            mime = detect_mime_type(img_url)
            xml_lines.append(f'      <enclosure url="{xml_escape(img_url)}" length="0" type="{mime}" />')
            
        xml_lines.append('    </item>')
        
    xml_lines.append('  </channel>')
    xml_lines.append('</rss>')
    
    return "\n".join(xml_lines)

def build_all_feeds(output_dir=None, db_path=None):
    """
    Generate master RSS feed and per-category feeds into output_dir.
    Returns dictionary with generated feed paths and metadata.
    """
    dist_path = Path(output_dir or Config.DIST_DIR)
    feeds_dir = dist_path / "feeds"
    feeds_dir.mkdir(parents=True, exist_ok=True)
    
    base_url = database.get_setting("public_base_url", Config.PUBLIC_BASE_URL, db_path=db_path).rstrip("/")
    site_name = database.get_setting("site_name", Config.SITE_NAME, db_path=db_path)
    site_description = database.get_setting("site_description", Config.SITE_DESCRIPTION, db_path=db_path)
    managing_editor = database.get_setting("managing_editor", Config.SITE_MANAGING_EDITOR, db_path=db_path)
    
    now_iso = datetime.now(timezone.utc).isoformat()
    database.set_setting("last_build_time", now_iso, db_path=db_path)
    
    # 1. Fetch all published reports
    published_items = database.list_reports(status="published", db_path=db_path)
    
    generated = {
        "master_feeds": [],
        "category_feeds": [],
        "total_published": len(published_items),
        "build_time": now_iso
    }
    
    # Master Feed: feed.xml
    master_info = {
        "title": site_name,
        "base_url": base_url,
        "link": base_url,
        "description": site_description,
        "managing_editor": managing_editor,
        "last_build_date": now_iso
    }
    master_xml = generate_feed_xml(master_info, published_items, self_url=f"{base_url}/feed.xml")
    
    # Write feed.xml and alias rss.xml
    (dist_path / "feed.xml").write_text(master_xml, encoding="utf-8")
    (dist_path / "rss.xml").write_text(master_xml, encoding="utf-8")
    generated["master_feeds"].append(str(dist_path / "feed.xml"))
    generated["master_feeds"].append(str(dist_path / "rss.xml"))
    
    # 2. Build Category Feeds
    for cat in Config.CATEGORIES:
        cat_id = cat["id"]
        cat_name = cat["name"]
        cat_desc = cat["description"]
        cat_items = [item for item in published_items if item.get("category") == cat_id]
        
        cat_info = {
            "title": f"{site_name} | {cat_name}",
            "base_url": base_url,
            "link": f"{base_url}/#category-{cat_id}",
            "description": f"{cat_desc} - خلاصة RSS لقسم {cat_name}",
            "managing_editor": managing_editor,
            "last_build_date": now_iso
        }
        
        cat_self_url = f"{base_url}/feeds/{cat_id}.xml"
        cat_xml = generate_feed_xml(cat_info, cat_items, self_url=cat_self_url)
        cat_file = feeds_dir / f"{cat_id}.xml"
        cat_file.write_text(cat_xml, encoding="utf-8")
        
        generated["category_feeds"].append({
            "id": cat_id,
            "name": cat_name,
            "file": str(cat_file),
            "url": cat_self_url,
            "count": len(cat_items)
        })
        
    return generated
