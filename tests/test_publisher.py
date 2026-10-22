import unittest
import tempfile
import os
import shutil
import xml.etree.ElementTree as ET
import database
import github_publisher
from config import Config

class PublisherTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.dist_dir = os.path.join(self.temp_dir, "dist")
        
        database.init_db(db_path=self.db_path)
        
        # 1. Politics report
        database.create_report({
            "title": "تقرير سياسي استراتيجي",
            "slug": "political-report-2026",
            "category": "politics",
            "summary": "موجز سياسي",
            "content": "## تفاصيل سياسية\nنص تحليلي معمق.",
            "status": "published"
        }, db_path=self.db_path)

        # 2. Tech report
        database.create_report({
            "title": "تقرير تقني في الحوسبة السحابية",
            "slug": "cloud-tech-report",
            "category": "tech",
            "summary": "موجز تقني",
            "content": "## تفاصيل تقنية\nنص عن مراكز البيانات.",
            "status": "published"
        }, db_path=self.db_path)

        # 3. Health report with external image enclosure
        database.create_report({
            "title": "تقرير طبي عن اللقاحات الجديدة",
            "slug": "health-vaccine-report",
            "category": "health",
            "summary": "موجز التقرير الطبي",
            "content": "## التطورات العلاجية\nأبحاث طبية موسعة.",
            "image_url": "https://external-cdn.com/photos/vaccine.jpg",
            "status": "published"
        }, db_path=self.db_path)

        # 4. Draft report (MUST NEVER appear in public RSS)
        database.create_report({
            "title": "مسودة غير معتمدة للنشر",
            "slug": "secret-draft-report",
            "category": "politics",
            "summary": "موجز المسودة",
            "content": "مسودة سرية",
            "status": "draft"
        }, db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_export_static_site_structure(self):
        res = github_publisher.export_static_site(output_dir=self.dist_dir, db_path=self.db_path)
        self.assertTrue(res["success"])
        # Only 3 published reports exported to articles (draft excluded)
        self.assertEqual(res["articles_count"], 3)

        # 1. Master RSS feeds
        master_feed_xml = os.path.join(self.dist_dir, "feed.xml")
        master_rss_xml = os.path.join(self.dist_dir, "rss.xml")
        self.assertTrue(os.path.exists(master_feed_xml))
        self.assertTrue(os.path.exists(master_rss_xml))

        # Check master feed contains exactly the 3 published items (draft omitted)
        root = ET.parse(master_feed_xml).getroot()
        items = root.findall("./channel/item")
        self.assertEqual(len(items), 3)

        # Check no duplicated GUIDs
        guids = [it.find("guid").text for it in items]
        self.assertEqual(len(guids), len(set(guids)), "Duplicate GUIDs detected in master feed!")

        # Verify draft is NEVER in master feed
        item_titles = [it.find("title").text for it in items]
        self.assertNotIn("مسودة غير معتمدة للنشر", item_titles)

        # 2. Category RSS feeds - verify category item appears in category AND master
        health_xml = os.path.join(self.dist_dir, "feeds", "health.xml")
        self.assertTrue(os.path.exists(health_xml))

        health_root = ET.parse(health_xml).getroot()
        health_items = health_root.findall("./channel/item")
        self.assertEqual(len(health_items), 1)
        self.assertEqual(health_items[0].find("title").text, "تقرير طبي عن اللقاحات الجديدة")

        # Verify external image enclosure on health report
        enclosure = health_items[0].find("enclosure")
        self.assertIsNotNone(enclosure)
        self.assertEqual(enclosure.attrib.get("url"), "https://external-cdn.com/photos/vaccine.jpg")
        self.assertEqual(enclosure.attrib.get("type"), "image/jpeg")

        # Verify that health report is also in master feed
        self.assertIn("تقرير طبي عن اللقاحات الجديدة", item_titles)

        # Verify politics feed does not include the draft
        politics_xml = os.path.join(self.dist_dir, "feeds", "politics.xml")
        pol_root = ET.parse(politics_xml).getroot()
        pol_items = pol_root.findall("./channel/item")
        self.assertEqual(len(pol_items), 1)
        self.assertEqual(pol_items[0].find("title").text, "تقرير سياسي استراتيجي")

        # 3. Static Article Pages & SEO Noindex check
        art_health = os.path.join(self.dist_dir, "articles", "health-vaccine-report.html")
        self.assertTrue(os.path.exists(art_health))
        with open(art_health, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn('dir="rtl"', content)
            self.assertIn('<meta name="robots" content="noindex, nofollow">', content)

        # Verify draft article HTML was NOT generated
        art_draft = os.path.join(self.dist_dir, "articles", "secret-draft-report.html")
        self.assertFalse(os.path.exists(art_draft))

        # 4. Check all 10 category feeds are generated
        for cat in Config.CATEGORIES:
            cat_feed = os.path.join(self.dist_dir, "feeds", f"{cat['id']}.xml")
            self.assertTrue(os.path.exists(cat_feed), f"Missing feed for category {cat['id']}")

if __name__ == "__main__":
    unittest.main()
