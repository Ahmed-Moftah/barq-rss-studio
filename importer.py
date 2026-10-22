import json
import re
from config import Config

def map_category_string(cat_str):
    """
    Map Arabic category name or loose string to registered category ID.
    """
    if not cat_str:
        return "reports"
    text = cat_str.strip().lower()
    
    # Check direct match with IDs or slugs
    for cat in Config.CATEGORIES:
        if text == cat["id"] or text == cat["slug"] or text == cat["name"].lower():
            return cat["id"]
            
    # Fuzzy keyword mapping
    if any(k in text for k in ["عاجل", "خبر عاجل", "تطورات عاجلة", "طارئ", "breaking"]):
        return "breaking"
    if any(k in text for k in ["سياس", "دبلوماس", "علاقات دولية", "politics"]):
        return "politics"
    if any(k in text for k in ["اقتصاد", "مال", "أعمال", "أسواق", "استثمار", "تجارة", "economy"]):
        return "economy"
    if any(k in text for k in ["صح", "طب", "علاج", "دواء", "مستشفى", "أوبئة", "health", "medical"]):
        return "health"
    if any(k in text for k in ["فن", "ثقاف", "أدب", "سينما", "موسيقى", "مسرح", "فنون", "arts", "culture"]):
        return "arts"
    if any(k in text for k in ["رياض", "كرة", "دوري", "بطول", "مبارا", "sports"]):
        return "sports"
    if any(k in text for k in ["تكنول", "تقني", "ذكاء", "برمج", "سايبر", "رقمي", "tech"]):
        return "tech"
    if any(k in text for k in ["أخبار عامة", "موجز", "أحداث", "news", "general"]):
        return "news"
    if any(k in text for k in ["تحليل", "تقدير موقف", "استراتيج", "رأي", "analysis"]):
        return "analysis"
    if any(k in text for k in ["تحقيق", "استقصا", "وثائق", "investigation"]):
        return "investigations"
        
    return "reports"

def parse_chatgpt_report(raw_text):
    """
    Intelligently parse raw ChatGPT generated editorial text, Markdown, or JSON.
    Returns a dictionary ready for the report editor.
    """
    if not raw_text or not raw_text.strip():
        return {
            "title": "",
            "category": "reports",
            "summary": "",
            "content": "",
            "tags": "",
            "author": "فريق تحرير برق",
            "source": "ChatGPT / إعداد تحريري"
        }
        
    trimmed = raw_text.strip()
    
    # 1. Try parsing JSON if input is wrapped in JSON format
    if (trimmed.startswith("{") and trimmed.endswith("}")) or ("```json" in trimmed):
        json_candidate = trimmed
        if "```json" in json_candidate:
            match = re.search(r'```json\s*(\{.*?\})\s*```', json_candidate, re.DOTALL)
            if match:
                json_candidate = match.group(1)
        try:
            data = json.loads(json_candidate)
            return {
                "title": data.get("title", "").strip(),
                "category": map_category_string(data.get("category", "")),
                "summary": data.get("summary", "").strip(),
                "content": data.get("content", "").strip(),
                "tags": data.get("tags", "").strip(),
                "author": data.get("author", "فريق تحرير برق").strip(),
                "source": data.get("source", "ChatGPT / استيراد مباشر").strip(),
                "image_url": data.get("image_url", "").strip(),
                "image_caption": data.get("image_caption", "").strip(),
            }
        except Exception:
            pass

    # 2. Heuristic text & Markdown parsing
    lines = trimmed.splitlines()
    title = ""
    category = "reports"
    summary = ""
    tags = ""
    author = "فريق تحرير برق"
    source = "ChatGPT / إعداد تحريري"
    image_url = ""
    image_caption = ""
    
    metadata_line_indices = set()
    
    # Check for metadata tags in the first 20 lines
    max_scan = min(len(lines), 20)
    for i in range(max_scan):
        line = lines[i].strip()
        if not line:
            continue
            
        # Title check: explicit label with or without markdown heading "#" or "**"
        m_title = re.match(r'^(?:#{1,6}\s*)?\*{0,2}(?:عنوان التقرير|العنوان|title)\s*[:：]\s*\*{0,2}\s*(.+)$', line, re.IGNORECASE)
        if m_title and not title:
            title = m_title.group(1).strip().strip('*# ')
            metadata_line_indices.add(i)
            continue

        # If it's a top-level markdown heading without explicit label, e.g. "# مسارات التحول"
        m_h1 = re.match(r'^#\s+(.+)$', line)
        if m_h1 and not title:
            title = m_h1.group(1).strip().strip('*# ')
            metadata_line_indices.add(i)
            continue
            
        # Category check: "**التصنيف:** ...", "القسم: ..."
        m_cat = re.match(r'^\*{0,2}(?:التصنيف|القسم|الفئة|category)\s*[:：]\s*\*{0,2}\s*(.+)$', line, re.IGNORECASE)
        if m_cat:
            cat_val = m_cat.group(1).strip().strip('* ')
            category = map_category_string(cat_val)
            metadata_line_indices.add(i)
            continue
            
        # Summary check: "**الموجز:** ...", "الملخص: ..."
        m_sum = re.match(r'^\*{0,2}(?:الموجز|الملخص|الخلاصة|موجز التقرير|summary|abstract)\s*[:：]\s*\*{0,2}\s*(.+)$', line, re.IGNORECASE)
        if m_sum:
            summary = m_sum.group(1).strip().strip('* ')
            metadata_line_indices.add(i)
            continue
            
        # Tags check: "**الوسوم:** ...", "الكلمات المفتاحية: ..."
        m_tags = re.match(r'^\*{0,2}(?:الوسوم|الكلمات المفتاحية|الوسوم المقترحة|tags|keywords)\s*[:：]\s*\*{0,2}\s*(.+)$', line, re.IGNORECASE)
        if m_tags:
            tags = m_tags.group(1).strip().strip('* ')
            metadata_line_indices.add(i)
            continue
            
        # Author check: "**الكاتب:** ...", "إعداد: ..."
        m_auth = re.match(r'^\*{0,2}(?:الكاتب|المعد|المؤلف|إعداد|بقلم|author)\s*[:：]\s*\*{0,2}\s*(.+)$', line, re.IGNORECASE)
        if m_auth:
            author = m_auth.group(1).strip().strip('* ')
            metadata_line_indices.add(i)
            continue
            
        # Source check: "**المصدر:** ..."
        m_src = re.match(r'^\*{0,2}(?:المصدر|source)\s*[:：]\s*\*{0,2}\s*(.+)$', line, re.IGNORECASE)
        if m_src:
            source = m_src.group(1).strip().strip('* ')
            metadata_line_indices.add(i)
            continue

    # Fallback for title: if no explicit title label was found, look for first markdown H1 or first non-empty line
    if not title:
        for i, line in enumerate(lines):
            l = line.strip()
            if l.startswith("# "):
                title = l.lstrip("# ").strip()
                metadata_line_indices.add(i)
                break
        if not title and lines:
            for i, line in enumerate(lines):
                if line.strip():
                    title = line.strip().strip('*# ')
                    metadata_line_indices.add(i)
                    break

    # Build the body content excluding recognized metadata header lines
    body_lines = []
    for i, line in enumerate(lines):
        if i in metadata_line_indices:
            continue
        body_lines.append(line)
        
    content = "\n".join(body_lines).strip()
    
    # Fallback for summary: if not provided, take the first paragraph of content
    if not summary and content:
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for p in paragraphs:
            # Ignore headings
            if not p.startswith("#") and len(p) > 20:
                # Truncate to reasonable summary length
                summary = p[:280] + ("..." if len(p) > 280 else "")
                break
                
    return {
        "title": title,
        "category": category,
        "summary": summary,
        "content": content,
        "tags": tags,
        "author": author,
        "source": source,
        "image_url": image_url,
        "image_caption": image_caption
    }
