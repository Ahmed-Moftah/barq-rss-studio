import unittest
import tempfile
import os
import shutil
import json
import io

from config import Config
import database
import importer
import rss_generator
from app import create_app

class BulkImportTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_bulk_studio.db")
        self.dist_dir = os.path.join(self.temp_dir, "dist")
        os.makedirs(self.dist_dir, exist_ok=True)
        database.init_db(self.db_path)
        
        self.app = create_app({
            "TESTING": True,
            "DB_PATH": self.db_path,
            "DIST_DIR": self.dist_dir,
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_valid_batch_import_preview_and_execute(self):
        """Test valid batch of 10-20 reports parsing, previewing, and persisting as drafts."""
        reports = []
        for i in range(1, 13):
            reports.append({
                "title": f"تقرير تحليلي رقم {i}: مسارات الطاقة والتنمية",
                "category": "breaking" if i == 1 else ("economy" if i % 2 == 0 else "tech"),
                "summary": f"موجز تحليلي مركز للتقرير رقم {i}.",
                "content": f"## المحور الأول للتقرير {i}\nتفاصيل المحتوى التحريري الكامل مع بيانات وإحصاءات دقيقة لعام 2026.",
                "slug": f"energy-report-slug-{i}",
                "tags": f"طاقة, تنمية, تقرير-{i}",
                "author": f"محرر تحليلي {i}",
                "source": f"https://example.com/source-{i}",
                "image_url": f"https://example.com/images/hero-{i}.jpg",
                "image_caption": f"صورة تعبيرية للتقرير {i}"
            })

        payload = {"reports": reports}
        raw_json = json.dumps(payload, ensure_ascii=False)

        # 1. Preview API
        resp_preview = self.client.post("/api/import/preview", json={"text": raw_json})
        self.assertEqual(resp_preview.status_code, 200)
        preview_data = resp_preview.get_json()
        self.assertTrue(preview_data["success"])
        self.assertEqual(preview_data["total_count"], 12)
        self.assertEqual(preview_data["valid_count"], 12)
        self.assertEqual(preview_data["duplicate_count"], 0)
        self.assertEqual(preview_data["invalid_count"], 0)

        # Verify breaking category mapping on item 1
        self.assertEqual(preview_data["reports"][0]["data"]["category"], "breaking")
        self.assertEqual(preview_data["reports"][0]["category_meta"]["name"], "عاجل")

        # 2. Execute API
        valid_items = [r["data"] for r in preview_data["reports"]]
        resp_exec = self.client.post("/api/import/execute", json={"reports": valid_items})
        self.assertEqual(resp_exec.status_code, 200)
        exec_data = resp_exec.get_json()
        self.assertTrue(exec_data["success"])
        self.assertEqual(exec_data["imported_count"], 12)
        self.assertEqual(exec_data["failed_count"], 0)

        # 3. Verify in database
        db_reports = database.list_reports(db_path=self.db_path)
        # initial seeded reports (4) + 12 newly imported = 16
        self.assertEqual(len(db_reports), 16)
        imported_drafts = [r for r in db_reports if "مسارات الطاقة والتنمية" in r["title"]]
        self.assertEqual(len(imported_drafts), 12)
        for rep in imported_drafts:
            self.assertEqual(rep["status"], "draft", "All imported reports MUST strictly be drafts!")
            self.assertIsNone(rep["published_at"])

    def test_invalid_items_handling(self):
        """Test that items missing title or content are flagged with validation errors."""
        invalid_batch = {
            "reports": [
                {
                    # Missing title
                    "category": "tech",
                    "content": "محتوى بدون عنوان"
                },
                {
                    # Missing content
                    "title": "عنوان بدون محتوى",
                    "category": "politics"
                },
                {
                    # Valid item
                    "title": "تقرير سليم تماماً",
                    "category": "breaking",
                    "content": "محتوى مكتمل وصالح"
                }
            ]
        }

        res = importer.parse_bulk_chatgpt_json(invalid_batch, db_path=self.db_path)
        self.assertTrue(res["success"])
        self.assertEqual(res["total_count"], 3)
        self.assertEqual(res["valid_count"], 1)
        self.assertEqual(res["invalid_count"], 2)

        rep0 = res["reports"][0]
        self.assertFalse(rep0["is_valid"])
        self.assertTrue(any("عنوان" in e for e in rep0["errors"]))

        rep1 = res["reports"][1]
        self.assertFalse(rep1["is_valid"])
        self.assertTrue(any("محتوى" in e for e in rep1["errors"]))

        rep2 = res["reports"][2]
        self.assertTrue(rep2["is_valid"])
        self.assertEqual(len(rep2["errors"]), 0)

    def test_duplicate_detection_against_db_and_intra_batch(self):
        """Test duplicate detection by slug/title against existing DB reports and within same batch."""
        # Seed an existing report in DB
        database.create_report({
            "title": "تقرير سابق منشور عن التضخم العالمي",
            "slug": "existing-inflation-report-2026",
            "category": "economy",
            "content": "محتوى مسجل في قاعدة البيانات",
            "status": "published"
        }, db_path=self.db_path)

        batch = {
            "reports": [
                {
                    # Duplicate slug
                    "title": "عنوان مختلف ولكن نفس الرابط اللطيف",
                    "slug": "existing-inflation-report-2026",
                    "content": "محتوى تجريبي"
                },
                {
                    # Duplicate title
                    "title": "تقرير سابق منشور عن التضخم العالمي",
                    "slug": "different-slug-here",
                    "content": "محتوى تجريبي آخر"
                },
                {
                    # Intra-batch duplicate 1
                    "title": "تقرير جديد غير مكرر في القاعدة",
                    "slug": "new-unique-report",
                    "content": "محتوى أولي"
                },
                {
                    # Intra-batch duplicate 2 (matches item above)
                    "title": "تقرير جديد غير مكرر في القاعدة",
                    "slug": "new-unique-report-duplicate",
                    "content": "محتوى مكرر داخل نفس الملف"
                }
            ]
        }

        res = importer.parse_bulk_chatgpt_json(batch, db_path=self.db_path)
        self.assertTrue(res["success"])
        reports = res["reports"]

        # Item 0: Duplicate by slug against DB
        self.assertTrue(reports[0]["is_duplicate"])
        self.assertIn("الرابط اللطيف", reports[0]["duplicate_reason"])

        # Item 1: Duplicate by title against DB
        self.assertTrue(reports[1]["is_duplicate"])
        self.assertIn("العنوان", reports[1]["duplicate_reason"])

        # Item 2: Unique first occurrence
        self.assertFalse(reports[2]["is_duplicate"])

        # Item 3: Intra-batch duplicate
        self.assertTrue(reports[3]["is_duplicate"])
        self.assertIn("نفس ملف الاستيراد", reports[3]["duplicate_reason"])

        # Verify existing report was NOT modified or deleted
        existing = database.get_report_by_slug("existing-inflation-report-2026", db_path=self.db_path)
        self.assertIsNotNone(existing)
        self.assertEqual(existing["status"], "published")
        self.assertEqual(existing["title"], "تقرير سابق منشور عن التضخم العالمي")

    def test_arabic_utf8_preservation(self):
        """Test complete preservation of Arabic UTF-8 text, diacritics, and formatting."""
        arabic_title = "تَقْدِيرُ مَوْقِف: «مَسَارَاتُ التَّحَوُّلِ الاقْتِصَادِيِّ ٢٠٢٦»"
        arabic_summary = "قِرَاءَةٌ اسْتِرَاتِيجِيَّةٌ فِي تَحَوُّلَاتِ أَسْوَاقِ الطَّاقَةِ وَالتِّجَارَةِ الإِقْلِيمِيَّةِ."
        arabic_content = """# الْمُقَدِّمَةُ التَّحْرِيرِيَّةُ
تَشْهَدُ المِنْطَقَةُ حَرَكَةً اسْتِثْمَارِيَّةً مُتَسَارِعَةً...

* **الْمِحْوَرُ الأَوَّل**: رَبْطُ شَبَكَاتِ الكَهْرَبَاءِ.
* **الْمِحْوَرُ الثَّانِي**: شَرََاكَاتُ الهِيدْرُوجِينِ الأَخْضَرِ.

## الْخَاتِمَةُ
تَتَطَلَّبُ المَرْحَلَةُ تَنْسِيقاً مُتَوَاصِلاً بَيْنَ كَافَّةِ الأَطْرَافِ."""

        batch = {
            "reports": [
                {
                    "title": arabic_title,
                    "category": "analysis",
                    "summary": arabic_summary,
                    "content": arabic_content,
                    "tags": "طاقة, اقتصاد, تقدير موقف, ٢٠٢٦",
                    "author": "فَرِيقُ التَّحْلِيلِ التَّحْرِيرِيِّ",
                    "source": "إِعْدَادٌ خَاصٌّ / بَرْق"
                }
            ]
        }

        res = importer.parse_bulk_chatgpt_json(batch, db_path=self.db_path)
        self.assertTrue(res["success"])
        rep_data = res["reports"][0]["data"]

        # Save to DB
        created = database.bulk_create_reports([rep_data], db_path=self.db_path)
        self.assertEqual(created["imported_count"], 1)

        rep_id = created["imported"][0]["id"]
        saved = database.get_report_by_id(rep_id, db_path=self.db_path)

        self.assertEqual(saved["title"], arabic_title)
        self.assertEqual(saved["summary"], arabic_summary)
        self.assertEqual(saved["content"], arabic_content)
        self.assertEqual(saved["author"], "فَرِيقُ التَّحْلِيلِ التَّحْرِيرِيِّ")
        self.assertIn("الْمِحْوَرُ الأَوَّل", saved["content_html"])

    def test_draft_status_enforcement_and_rss_exclusion(self):
        """Even if payload says published, status must be draft and excluded from RSS."""
        batch = {
            "reports": [
                {
                    "title": "محاولة نشر مباشر غير معتمد",
                    "category": "breaking",
                    "content": "محتوى تقرير عاجل يحاول النشر بدون موافقة",
                    "status": "published",
                    "published_at": "2026-10-22T10:00:00Z"
                }
            ]
        }

        res = importer.parse_bulk_chatgpt_json(batch, db_path=self.db_path)
        rep_data = res["reports"][0]["data"]
        self.assertEqual(rep_data["status"], "draft", "Importer must override status to draft!")

        # Execute creation
        database.bulk_create_reports([rep_data], db_path=self.db_path)
        saved = database.get_report_by_slug(rep_data["slug"], db_path=self.db_path)
        self.assertEqual(saved["status"], "draft")
        self.assertIsNone(saved["published_at"])

        # Build feeds
        rss_generator.build_all_feeds(output_dir=self.dist_dir, db_path=self.db_path)

        # Verify not in master feed.xml
        master_feed = os.path.join(self.dist_dir, "feed.xml")
        with open(master_feed, "r", encoding="utf-8") as f:
            feed_content = f.read()
        self.assertNotIn("محاولة نشر مباشر غير معتمد", feed_content)

        # Verify not in breaking.xml
        breaking_feed = os.path.join(self.dist_dir, "feeds", "breaking.xml")
        with open(breaking_feed, "r", encoding="utf-8") as f:
            breaking_content = f.read()
        self.assertNotIn("محاولة نشر مباشر غير معتمد", breaking_content)

    def test_category_mapping_all_categories_including_breaking(self):
        """Verify automatic mapping for all 11 registered categories."""
        mappings = [
            ("عاجل", "breaking"),
            ("شؤون سياسية ودولية", "politics"),
            ("اقتصاد وأسواق المال", "economy"),
            ("صحة عامة وطب", "health"),
            ("ثقافة وأدب وفنون", "arts"),
            ("شؤون رياضية وبطولات", "sports"),
            ("الذكاء الاصطناعي والتكنولوجيا", "tech"),
            ("أخبار عامة وموجز", "news"),
            ("تقدير موقف استراتيجي", "analysis"),
            ("تقارير خاصة وشاملة", "reports"),
            ("تحقيق استقصائي موثق", "investigations"),
        ]

        for arabic_str, expected_id in mappings:
            mapped_id = importer.map_category_string(arabic_str)
            self.assertEqual(mapped_id, expected_id, f"Failed mapping '{arabic_str}' to '{expected_id}'")

    def test_preservation_of_full_article_content_and_metadata(self):
        """Verify images, captions, tags, source URLs, and long markdown content are preserved."""
        long_content = "## التوطئة\n" + ("فقرة تفصيلية مطولة تحتوي على تحليلات نوعية ومعلومات مدققة.\n\n" * 15)
        item = {
            "title": "تقرير معمق ذو محتوى طويل وصورة خارجية",
            "category": "reports",
            "summary": "موجز شامل ووافي للتقرير.",
            "content": long_content,
            "tags": ["استثمار", "تقنية", "بنية تحتية"],
            "author": "وحدة الدراسات المعمقة",
            "source": "https://barq.example.com/editorial-source-doc",
            "image_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1200",
            "image_caption": "صورة تعبيرية رسمية للحدث - حقوق التوزيع محفوظة"
        }

        res = importer.validate_report_dict(item)
        self.assertTrue(res["is_valid"])
        data = res["data"]

        self.assertEqual(data["content"], long_content.strip())
        self.assertEqual(data["tags"], "استثمار, تقنية, بنية تحتية")
        self.assertEqual(data["source"], "https://barq.example.com/editorial-source-doc")
        self.assertEqual(data["image_url"], "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=1200")
        self.assertEqual(data["image_caption"], "صورة تعبيرية رسمية للحدث - حقوق التوزيع محفوظة")

        # Invalidate wrong image scheme
        item_bad_img = dict(item)
        item_bad_img["image_url"] = "ftp://invalid-server.com/image.png"
        res_bad = importer.validate_report_dict(item_bad_img)
        self.assertEqual(res_bad["data"]["image_url"], "")

    def test_backward_compatibility_single_imports(self):
        """Verify single report import in markdown and single JSON formats still works seamlessly."""
        # 1. Single markdown text
        md_sample = """# عنوان التقرير المفرد
**التصنيف:** تكنولوجيا وابتكار
**الموجز:** فكرة التقرير المفرد.
**الكاتب:** محرر فردي

نص المقال المفرد هنا..."""
        parsed_md = importer.parse_chatgpt_report(md_sample)
        self.assertEqual(parsed_md["title"], "عنوان التقرير المفرد")
        self.assertEqual(parsed_md["category"], "tech")
        self.assertIn("فكرة التقرير المفرد", parsed_md["summary"])

        # 2. Single JSON format
        json_single = """{
            "title": "تقرير JSON مفرد",
            "category": "breaking",
            "content": "نص التقرير المفرد"
        }"""
        parsed_json = importer.parse_chatgpt_report(json_single)
        self.assertEqual(parsed_json["title"], "تقرير JSON مفرد")
        self.assertEqual(parsed_json["category"], "breaking")

        # 3. Bulk JSON accidentally passed to parse_chatgpt_report
        bulk_json = """{
            "reports": [
                {
                    "title": "التقرير الأول من الدفعة",
                    "category": "economy",
                    "content": "محتوى التقرير الأول"
                },
                {
                    "title": "التقرير الثاني من الدفعة",
                    "category": "sports",
                    "content": "محتوى التقرير الثاني"
                }
            ]
        }"""
        parsed_bulk_fallback = importer.parse_chatgpt_report(bulk_json)
        self.assertEqual(parsed_bulk_fallback["title"], "التقرير الأول من الدفعة")
        self.assertEqual(parsed_bulk_fallback["category"], "economy")

    def test_template_export_download(self):
        """Verify template download API returns valid schema JSON with instructions and sample reports."""
        resp = self.client.get("/api/import/template")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment; filename=chatgpt-bulk-import-template.json", resp.headers.get("Content-Disposition", ""))
        self.assertIn("application/json", resp.content_type)

        data = json.loads(resp.data.decode("utf-8"))
        self.assertIn("$schema_instructions", data)
        self.assertIn("reports", data)
        self.assertGreaterEqual(len(data["reports"]), 2)
        
        # Verify instructions explain required & optional fields
        instr = data["$schema_instructions"]
        self.assertIn("required_fields", instr)
        self.assertIn("optional_fields", instr)
        self.assertIn("valid_categories", instr)

    def test_batch_size_limits(self):
        """Verify rejecting empty batches or batches exceeding 20 reports."""
        # 1. Empty batch
        empty_res = importer.parse_bulk_chatgpt_json({"reports": []}, db_path=self.db_path)
        self.assertFalse(empty_res["success"])
        self.assertIn("فارغ", empty_res["error"])

        # 2. Batch > 20 reports
        too_many_reports = [{"title": f"T{i}", "content": f"C{i}"} for i in range(21)]
        overlimit_res = importer.parse_bulk_chatgpt_json({"reports": too_many_reports}, db_path=self.db_path)
        self.assertFalse(overlimit_res["success"])
        self.assertIn("الحد الأقصى", overlimit_res["error"])

        # 3. Batch exactly 20 reports
        allowed_20 = [{"title": f"T{i}", "content": f"C{i}"} for i in range(20)]
        allowed_res = importer.parse_bulk_chatgpt_json({"reports": allowed_20}, db_path=self.db_path)
        self.assertTrue(allowed_res["success"])
        self.assertEqual(allowed_res["total_count"], 20)

    def test_file_upload_preview(self):
        """Test uploading a JSON file via multipart/form-data to /api/import/preview."""
        sample_json = json.dumps({
            "reports": [
                {
                    "title": "تقرير مرفوع كملف",
                    "category": "breaking",
                    "content": "محتوى التقرير المرفوع"
                }
            ]
        }, ensure_ascii=False).encode("utf-8")

        data = {
            "file": (io.BytesIO(sample_json), "batch.json")
        }
        resp = self.client.post("/api/import/preview", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res = resp.get_json()
        self.assertTrue(res["success"])
        self.assertEqual(res["total_count"], 1)
        self.assertEqual(res["reports"][0]["data"]["title"], "تقرير مرفوع كملف")

if __name__ == "__main__":
    unittest.main()
