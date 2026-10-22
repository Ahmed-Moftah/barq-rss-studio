import unittest
import tempfile
import os
import database
from config import Config

class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        database.init_db(self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_create_and_fetch_report(self):
        data = {
            "title": "تقرير تجريبي عن أسواق الطاقة في المنطقة",
            "category": "economy",
            "summary": "ملخص تحليلي لحركة أسواق النفط والغاز.",
            "content": "## المحور الأول\nتفاصيل الأداء الفصلي لمشاريع الطاقة المتجددة.",
            "author": "فريق التحرير الاقتصادي",
            "source": "إعداد تحريري",
            "tags": "طاقة, نفط, اقتصاد",
            "status": "published"
        }
        report_id = database.create_report(data, db_path=self.temp_db_path)
        self.assertIsNotNone(report_id)

        report = database.get_report_by_id(report_id, db_path=self.temp_db_path)
        self.assertEqual(report["title"], data["title"])
        self.assertEqual(report["category"], "economy")
        self.assertEqual(report["status"], "published")
        self.assertIn("المحور الأول", report["content_html"])
        self.assertTrue(len(report["slug"]) > 0)

    def test_arabic_slug_generation(self):
        slug = database.slugify("تحولات ممرات التجارة 2026")
        self.assertIn("تحولات-ممرات-التجارة-2026", slug)

    def test_update_and_delete_report(self):
        data = {
            "title": "عنوان أولي",
            "category": "tech",
            "content": "محتوى أولي",
            "status": "draft"
        }
        report_id = database.create_report(data, db_path=self.temp_db_path)
        
        # Update
        database.update_report(report_id, {"title": "عنوان معدل", "status": "published"}, db_path=self.temp_db_path)
        updated = database.get_report_by_id(report_id, db_path=self.temp_db_path)
        self.assertEqual(updated["title"], "عنوان معدل")
        self.assertEqual(updated["status"], "published")

        # Delete
        database.delete_report(report_id, db_path=self.temp_db_path)
        deleted = database.get_report_by_id(report_id, db_path=self.temp_db_path)
        self.assertIsNone(deleted)

    def test_dashboard_stats(self):
        database.create_report({"title": "T1", "category": "tech", "content": "C1", "status": "published"}, db_path=self.temp_db_path)
        database.create_report({"title": "T2", "category": "politics", "content": "C2", "status": "draft"}, db_path=self.temp_db_path)
        
        stats = database.get_dashboard_stats(db_path=self.temp_db_path)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["published"], 1)
        self.assertEqual(stats["drafts"], 1)
        self.assertEqual(stats["by_category"].get("tech"), 1)

if __name__ == "__main__":
    unittest.main()
