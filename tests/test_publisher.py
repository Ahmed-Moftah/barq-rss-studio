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
        
        # Create reports in 2 categories
        database.create_report({
            "title": "تقرير سياسي استراتيجي",
            "slug": "political-report-2026",
            "category": "politics",
            "summary": "موجز سياسي",
            "content": "## تفاصيل سياسية\nنص تحليلي معمق.",
            "status": "published"
        }, db_path=self.db_path)

        database.create_report({
            "title": "تقرير تقني في الحوسبة السحابية",
            "slug": "cloud-tech-report",
            "category": "tech",
            "summary": "موجز تقني",
            "content": "## تفاصيل تقنية\nنص عن مراكز البيانات.",
            "status": "published"
        }, db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_export_static_site_structure(self):
        res = github_publisher.export_static_site(output_dir=self.dist_dir, db_path=self.db_path)
        self.assertTrue(res["success"])
        self.assertEqual(res["articles_count"], 2)

        # 1. Master RSS feeds
        master_feed_xml = os.path.join(self.dist_dir, "feed.xml")
        master_rss_xml = os.path.join(self.dist_dir, "rss.xml")
        self.assertTrue(os.path.exists(master_feed_xml))
        self.assertTrue(os.path.exists(master_rss_xml))

        # Check master feed contains both items
        root = ET.parse(master_feed_xml).getroot()
        items = root.findall("./channel/item")
        self.assertEqual(len(items), 2)

        # 2. Category RSS feeds
        politics_xml = os.path.join(self.dist_dir, "feeds", "politics.xml")
        tech_xml = os.path.join(self.dist_dir, "feeds", "tech.xml")
        self.assertTrue(os.path.exists(politics_xml))
        self.assertTrue(os.path.exists(tech_xml))

        pol_root = ET.parse(politics_xml).getroot()
        pol_items = pol_root.findall("./channel/item")
        self.assertEqual(len(pol_items), 1)
        self.assertEqual(pol_items[0].find("title").text, "تقرير سياسي استراتيجي")

        # 3. Static Article Pages
        art1 = os.path.join(self.dist_dir, "articles", "political-report-2026.html")
        art2 = os.path.join(self.dist_dir, "articles", "cloud-tech-report.html")
        self.assertTrue(os.path.exists(art1))
        self.assertTrue(os.path.exists(art2))

        # Verify RTL and content in HTML
        with open(art1, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn('dir="rtl"', content)
            self.assertIn("تقرير سياسي استراتيجي", content)
            self.assertIn("تفاصيل سياسية", content)

        # 4. Public portal index.html and feed catalog
        index_file = os.path.join(self.dist_dir, "index.html")
        catalog_file = os.path.join(self.dist_dir, "feed-catalog.json")
        self.assertTrue(os.path.exists(index_file))
        self.assertTrue(os.path.exists(catalog_file))

if __name__ == "__main__":
    unittest.main()
