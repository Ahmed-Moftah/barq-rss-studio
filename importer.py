import json
import re
from config import Config
import database

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
            # If bulk payload was passed to single importer, take first report
            if isinstance(data, dict) and "reports" in data and isinstance(data["reports"], list) and data["reports"]:
                data = data["reports"][0]
            elif isinstance(data, list) and data:
                data = data[0]
                
            return {
                "title": data.get("title", "").strip(),
                "category": map_category_string(data.get("category", "")),
                "summary": data.get("summary", "").strip(),
                "content": data.get("content", "").strip(),
                "tags": ", ".join(data.get("tags")) if isinstance(data.get("tags"), list) else str(data.get("tags", "")).strip(),
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

def validate_report_dict(item, existing_info=None, seen_in_batch=None):
    """
    Validate a single report dictionary against editorial safety, schema, and duplication rules.
    Returns:
        dict: {
            "is_valid": bool,
            "errors": list of str,
            "is_duplicate": bool,
            "duplicate_reason": str,
            "data": normalized report dict,
            "category_meta": category object
        }
    """
    if not isinstance(item, dict):
        return {
            "is_valid": False,
            "errors": ["التقرير ليس كائناً برمجياً صالحاً (JSON Object)."],
            "is_duplicate": False,
            "duplicate_reason": "",
            "data": {},
            "category_meta": Config.get_category_by_id("reports")
        }

    errors = []
    
    # 1. Title validation
    raw_title = item.get("title")
    title = str(raw_title).strip() if raw_title is not None else ""
    if not title:
        errors.append("حقل عنوان التقرير (title) مطلوب ولا يمكن تركه فارغاً.")
        
    # 2. Content validation
    raw_content = item.get("content")
    content = str(raw_content).strip() if raw_content is not None else ""
    if not content:
        errors.append("حقل محتوى التقرير (content) مطلوب.")

    # 3. Category mapping (supports all registered categories including 'breaking')
    raw_cat = item.get("category", "")
    cat_id = map_category_string(str(raw_cat) if raw_cat else "")
    cat_meta = Config.get_category_by_id(cat_id)
    
    # 4. Summary & fallback
    raw_summary = item.get("summary")
    summary = str(raw_summary).strip() if raw_summary else ""
    if not summary and content:
        # Fallback to first non-heading paragraph
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for p in paragraphs:
            if not p.startswith("#") and len(p) > 20:
                summary = p[:280] + ("..." if len(p) > 280 else "")
                break
        if not summary:
            summary = title[:280]

    # 5. Slug generation & normalization
    raw_slug = item.get("slug")
    if raw_slug and str(raw_slug).strip():
        slug = database.slugify(str(raw_slug).strip())
    else:
        slug = database.slugify(title) if title else "untitled-report"

    # 6. Tags normalization
    raw_tags = item.get("tags", "")
    if isinstance(raw_tags, list):
        tags = ", ".join(str(t).strip() for t in raw_tags if str(t).strip())
    else:
        tags = str(raw_tags).strip() if raw_tags else ""

    # 7. Author & Source metadata
    raw_author = item.get("author")
    author = str(raw_author).strip() if raw_author else "فريق تحرير برق"
    
    raw_source = item.get("source")
    source = str(raw_source).strip() if raw_source else "ChatGPT / استيراد مجمع"

    # 8. Externally hosted image URL & caption
    raw_image_url = item.get("image_url")
    image_url = str(raw_image_url).strip() if raw_image_url else ""
    if image_url and not (image_url.lower().startswith("http://") or image_url.lower().startswith("https://")):
        # Only accept externally hosted HTTP/HTTPS URLs
        image_url = ""

    raw_caption = item.get("image_caption")
    image_caption = str(raw_caption).strip() if raw_caption else ""

    # 9. Strict Editorial Safety: Always draft, never published automatically
    status = "draft"

    # 10. Duplicate Detection (against database and current batch)
    is_duplicate = False
    duplicate_reason = ""
    
    norm_slug = slug.lower()
    norm_title = title.lower()

    if existing_info:
        if norm_slug in existing_info.get("slugs", set()):
            is_duplicate = True
            existing_rep = existing_info.get("by_slug", {}).get(norm_slug, {})
            st_arabic = "منشور" if existing_rep.get("status") == "published" else "مسودة"
            duplicate_reason = f"يوجد تقرير مسجل مسبقاً بنفس الرابط اللطيف ({slug}) - الحالة: {st_arabic}"
        elif norm_title in existing_info.get("titles", set()):
            is_duplicate = True
            existing_rep = existing_info.get("by_title", {}).get(norm_title, {})
            st_arabic = "منشور" if existing_rep.get("status") == "published" else "مسودة"
            duplicate_reason = f"يوجد تقرير مسجل مسبقاً بنفس العنوان في قاعدة البيانات - الحالة: {st_arabic}"

    if seen_in_batch is not None and not is_duplicate and title:
        if norm_slug in seen_in_batch.get("slugs", set()) or norm_title in seen_in_batch.get("titles", set()):
            is_duplicate = True
            duplicate_reason = "مكرر داخل نفس ملف الاستيراد"
        else:
            seen_in_batch.setdefault("slugs", set()).add(norm_slug)
            seen_in_batch.setdefault("titles", set()).add(norm_title)

    normalized_data = {
        "title": title,
        "slug": slug,
        "category": cat_id,
        "summary": summary,
        "content": content,
        "tags": tags,
        "author": author,
        "source": source,
        "image_url": image_url,
        "image_caption": image_caption,
        "status": status
    }

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "is_duplicate": is_duplicate,
        "duplicate_reason": duplicate_reason,
        "data": normalized_data,
        "category_meta": cat_meta
    }

def parse_bulk_chatgpt_json(raw_input, db_path=None):
    """
    Parse a JSON document containing 1–20 editorial reports from ChatGPT.
    Supports:
      - JSON string or dictionary with {"reports": [ ... ]}
      - JSON string or list [ ... ]
      - Single report dictionary/string (wrapped automatically in a list of 1)
    Validates reports, detects duplicates, enforces draft status, and maps categories.
    """
    if not raw_input:
        return {
            "success": False,
            "error": "لم يتم إرسال أي بيانات أو ملف للاستيراد."
        }

    # 1. Parse JSON if string
    if isinstance(raw_input, (dict, list)):
        data = raw_input
    else:
        text = str(raw_input).strip()
        if not text:
            return {
                "success": False,
                "error": "محتوى ملف الاستيراد فارغ."
            }
        
        # Clean markdown code block fences if ChatGPT wrapped the response
        if "```json" in text:
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        elif "```" in text:
            match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()
                
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"خطأ في قراءة ملف JSON: يرجى التأكد من صحة التنسيق وصحة الأقواس (السطر {e.lineno}، العمود {e.colno})."
            }

    # 2. Extract reports list
    reports_list = []
    if isinstance(data, dict):
        if "reports" in data and isinstance(data["reports"], list):
            reports_list = data["reports"]
        elif "title" in data and "content" in data:
            # Single report object wrapped
            reports_list = [data]
        else:
            return {
                "success": False,
                "error": "بنية الملف غير متوافقة: يجب أن يحتوي الملف على مفتاح 'reports' يضم مصفوفة من التقارير التحريرية."
            }
    elif isinstance(data, list):
        reports_list = data
    else:
        return {
            "success": False,
            "error": "تنسيق البيانات غير مدعوم: يجب أن يكون الملف كائن JSON يحتوي على مصفوفة 'reports'."
        }

    # 3. Check batch size limits (1 to 20 reports)
    total_count = len(reports_list)
    if total_count == 0:
        return {
            "success": False,
            "error": "ملف الاستيراد فارغ ولا يحتوي على أي تقارير."
        }
    if total_count > 20:
        return {
            "success": False,
            "error": f"تتجاوز الدفعة الحد الأقصى المسموح به (الحد الأقصى هو 20 تقريراً لكل دفعة، بينما يحتوي الملف على {total_count} تقريراً). يرجى تقليص الدفعة أو تقسيم الملف."
        }

    # 4. Fetch existing database identifiers for duplicate detection
    existing_info = database.get_existing_identifiers(db_path=db_path)
    seen_in_batch = {"slugs": set(), "titles": set()}

    processed_reports = []
    for idx, item in enumerate(reports_list, start=1):
        res = validate_report_dict(item, existing_info=existing_info, seen_in_batch=seen_in_batch)
        res["index"] = idx
        processed_reports.append(res)

    valid_count = sum(1 for r in processed_reports if r["is_valid"] and not r["is_duplicate"])
    duplicate_count = sum(1 for r in processed_reports if r["is_duplicate"])
    invalid_count = sum(1 for r in processed_reports if not r["is_valid"])

    return {
        "success": True,
        "total_count": total_count,
        "valid_count": valid_count,
        "duplicate_count": duplicate_count,
        "invalid_count": invalid_count,
        "reports": processed_reports
    }

def get_chatgpt_bulk_import_template():
    """
    Generate downloadable JSON template conforming to the BARQ bulk import schema.
    Contains instructions and sample reports for ChatGPT.
    """
    categories_info = [
        {"id": c["id"], "name": c["name"], "slug": c["slug"], "description": c["description"]}
        for c in Config.CATEGORIES
    ]
    
    return {
        "$schema_instructions": {
            "title": "قالب استيراد التقارير التحريرية المجمعة من ChatGPT — استوديو برق",
            "version": "2.0",
            "batch_limits": "من 1 إلى 20 تقريراً تحريرياً في الملف الواحد",
            "required_fields": {
                "title": "عنوان التقرير الصحفي (مطلوب - نص دقيق وموجز)",
                "content": "المحتوى الكامل للتقرير بصيغة Markdown أو نصوص منسقة (مطلوب)"
            },
            "optional_fields": {
                "category": "القسم التحريري (افتراضياً 'reports' أو اختر من الأقسام المعتمدة أدناه)",
                "summary": "موجز التقرير التحريري (إذا تُرك فارغاً يُستخلص تلقائياً من الفقرة الأولى)",
                "slug": "الاسم اللطيف للرابط (يُولد تلقائياً من العنوان بحروف عربية أو لاتينية)",
                "tags": "الكلمات المفتاحية مفصولة بفواصل",
                "author": "اسم الكاتب أو الفريق التحريري (افتراضياً 'فريق تحرير برق')",
                "source": "رابط المصدر الأصلي أو جهة الإعداد للمراجعة التحريرية الداخلية",
                "image_url": "رابط الصورة البارزة المستضافة خارجياً (روابط HTTPS فقط)",
                "image_caption": "شرح الصورة وحقوق الملكية الفكرية والتصوير"
            },
            "valid_categories": categories_info,
            "editorial_safety_rules": [
                "تُستورد كافة التقارير تلقائياً بحالة مسودة (Draft) للأمان التحريري التام.",
                "لا تُنشر أي مسودة في خلاصات RSS حتى يتم اعتمادها صراحة من قبل رئيس التحرير.",
                "روابط الصور يجب أن تكون روابط خارجية مباشرة (HTTPS) دون حفظ أو تنزيل ملفات على الخادم.",
                "حقول المصادر تُحفظ للمراجعة التحريرية الداخلية ولا تُنشأ روابط خارجية بديلة في خلاصات RSS."
            ]
        },
        "reports": [
            {
                "title": "إعلان عاجل: تطورات استراتيجية طارئة في مسارات الملاحة الدولية",
                "category": "breaking",
                "summary": "موجز تحريري عاجل يوضح أبرز المستجدات والتداعيات الأولية على حركة التجارة وسلاسل الإمداد الإقليمية.",
                "content": "## تفاصيل الحدث العاجل\nأعلنت الجهات المعنية اليوم عن تطورات ميدانية متسارعة أدت إلى تعديل مؤقت في مسارات الإبحار...\n\n### الإجراءات المتخذة\n1. تفعيل خطط الطوارئ البديلة لضمان تدفق الشحنات.\n2. تكثيف دوريات الرقابة الملاحية في المضائق المشتركة.\n3. التنسيق المستمر مع الشركاء الإقليميين والدوليين.\n\n### التداعيات المتوقعة\nتشير التقديرات الأولية إلى استقرار الإمدادات دون تأثيرات هيكلية على الأسواق الرئيسية.",
                "slug": "urgent-strategic-development-navigation-2026",
                "tags": "عاجل, ملاحة, أمن بحري, تجارة دولية",
                "author": "غرفة الأخبار العاجلة",
                "source": "https://example.com/source-verification-doc",
                "image_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=1200",
                "image_caption": "سفن تجارية في ممر مائي دولي - وكالات / أرشيف"
            },
            {
                "title": "تحولات أسواق الهيدروجين الأخضر: خريطة الاستثمارات الجديدة لعام 2026",
                "category": "economy",
                "summary": "قراءة في تدفقات رؤوس الأموال ومشاريع الطاقة النظيفة وسلاسل الإمداد العالمية في الشرق الأوسط.",
                "content": "## مقدمة التقرير\nتشهد استثمارات الطاقة المتجددة قفزة نوعية مدفوعة بالسياسات الصناعية الجديدة والتحولات الاقتصادية...\n\n### المحاور الرئيسية\n* **المحور الأول**: مشروعات التحالفات الإقليمية الكبرى لتصدير الأمونيا الخضراء.\n* **المحور الثاني**: اقتصاديات النقل والتخزين وتحديث البنية التحتية للموانئ.\n\n### الخاتمة والتوقعات\nمن المرجح أن تسهم التسهيلات التمويلية في تسريع وتيرة الربط الكهربائي وتوطين التقنيات المتقدمة.",
                "slug": "green-hydrogen-investments-map-2026",
                "tags": "اقتصاد, طاقة متجددة, هيدروجين, استثمار",
                "author": "فريق التحليلات الاقتصادية",
                "source": "منتدى الطاقة الدولي / تقرير خاص",
                "image_url": "https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?w=1200",
                "image_caption": "محطة طاقة متجددة ومشاريع استثمارية خضراء"
            }
        ]
    }

