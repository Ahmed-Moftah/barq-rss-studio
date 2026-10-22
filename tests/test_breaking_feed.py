import unittest
import tempfile
import os
import shutil
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from config import Config
import database
import rss_generator
import github_publisher
import importer
from app import create_app

class BreakingFeedTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_breaking.db")
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

    def test_category_configuration(self):
        """Verify 'breaking' is a valid editorial category in Config."""
        cat = Config.get_category_by_id("breaking")
        self.assertIsNotNone(cat)
        self.assertEqual(cat["id"], "breaking")
        self.assertEqual(cat["name"], "عاجل")
        self.assertEqual(cat["slug"], "breaking")
        self.assertTrue(any(c["id"] == "breaking" for c in Config.CATEGORIES))

    def test_importer_category_mapping(self):
        """Verify Arabic text keywords map properly to 'breaking'."""
        self.assertEqual(importer.map_category_string("عاجل"), "breaking")
        self.assertEqual(importer.map_category_string("خبر عاجل"), "breaking")
        self.assertEqual(importer.map_category_string("تطورات عاجلة وحصرية"), "breaking")
        self.assertEqual(importer.map_category_string("breaking"), "breaking")

    def test_empty_breaking_feed_xml(self):
        """Verify feeds/breaking.xml is valid RSS 2.0 with 0 items when no reports exist."""
        result = rss_generator.build_all_feeds(output_dir=self.dist_dir, db_path=self.db_path)
        breaking_file = os.path.join(self.dist_dir, "feeds", "breaking.xml")
        self.assertTrue(os.path.exists(breaking_file), "feeds/breaking.xml should be generated even when empty")

        with open(breaking_file, "r", encoding="utf-8") as f:
            xml_content = f.read()

        root = ET.fromstring(xml_content)
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.attrib.get("version"), "2.0")

        channel = root.find("channel")
        self.assertIsNotNone(channel)
        self.assertIn("عاجل", channel.find("title").text)

        atom_link = channel.find("{http://www.w3.org/2005/Atom}link")
        self.assertIsNotNone(atom_link)
        self.assertTrue(atom_link.attrib.get("href").endswith("/feeds/breaking.xml"))

        # Zero items
        items = channel.findall("item")
        self.assertEqual(len(items), 0)

    def test_draft_breaking_report_excluded_from_feeds(self):
        """Draft reports in 'breaking' category must NEVER appear in public feeds."""
        database.create_report({
            "title": "خبر عاجل قيد التحرير (مسودة)",
            "slug": "breaking-draft-report",
            "category": "breaking",
            "summary": "موجز مسودة عاجلة",
            "content": "محتوى مسودة عاجلة غير معتمدة",
            "status": "draft"
        }, db_path=self.db_path)

        rss_generator.build_all_feeds(output_dir=self.dist_dir, db_path=self.db_path)

        breaking_file = os.path.join(self.dist_dir, "feeds", "breaking.xml")
        with open(breaking_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("breaking-draft-report", content)
        self.assertNotIn("خبر عاجل قيد التحرير", content)

        master_file = os.path.join(self.dist_dir, "feed.xml")
        with open(master_file, "r", encoding="utf-8") as f:
            master_content = f.read()
        self.assertNotIn("breaking-draft-report", master_content)

    def test_published_breaking_report_in_both_feeds(self):
        """Published breaking report must appear in breaking.xml and feed.xml with matching metadata."""
        rep_id = database.create_report({
            "title": "إعلان عاجل: تطورات استراتيجية طارئة",
            "slug": "urgent-strategic-development",
            "category": "breaking",
            "summary": "موجز التطور العاجل",
            "content": "نص التقرير الإخباري العاجل بالكامل مع تفاصيل الحدث.",
            "author": "غرفة الأخبار العاجلة",
            "image_url": "https://example.com/breaking-news.jpg",
            "status": "published"
        }, db_path=self.db_path)

        rss_generator.build_all_feeds(output_dir=self.dist_dir, db_path=self.db_path)

        # 1. Check breaking.xml
        breaking_file = os.path.join(self.dist_dir, "feeds", "breaking.xml")
        with open(breaking_file, "r", encoding="utf-8") as f:
            breaking_xml = f.read()

        root_b = ET.fromstring(breaking_xml)
        items_b = root_b.findall("./channel/item")
        self.assertEqual(len(items_b), 1)
        item_b = items_b[0]
        self.assertEqual(item_b.find("title").text, "إعلان عاجل: تطورات استراتيجية طارئة")
        self.assertTrue(item_b.find("link").text.endswith("/articles/urgent-strategic-development.html"))
        self.assertEqual(item_b.find("guid").text, item_b.find("link").text)
        self.assertIn("تفاصيل الحدث", item_b.find("description").text)

        # Enclosure
        enclosure = item_b.find("enclosure")
        self.assertIsNotNone(enclosure)
        self.assertEqual(enclosure.attrib.get("url"), "https://example.com/breaking-news.jpg")

        # 2. Check master feed.xml
        master_file = os.path.join(self.dist_dir, "feed.xml")
        with open(master_file, "r", encoding="utf-8") as f:
            master_xml = f.read()

        root_m = ET.fromstring(master_xml)
        items_m = [it for it in root_m.findall("./channel/item") if it.find("title").text == "إعلان عاجل: تطورات استراتيجية طارئة"]
        self.assertEqual(len(items_m), 1, "Published breaking item MUST also appear in master feed.xml")
        item_m = items_m[0]

        # Verify matching GUID and metadata between feeds
        self.assertEqual(item_b.find("guid").text, item_m.find("guid").text)
        self.assertEqual(item_b.find("pubDate").text, item_m.find("pubDate").text)
        self.assertEqual(item_b.find("link").text, item_m.find("link").text)

        # 3. Check another category feed does NOT contain this item
        politics_file = os.path.join(self.dist_dir, "feeds", "politics.xml")
        with open(politics_file, "r", encoding="utf-8") as f:
            politics_xml = f.read()
        self.assertNotIn("urgent-strategic-development", politics_xml)

    def test_feed_catalog_contains_breaking(self):
        """Verify feed-catalog.json includes the new 'breaking' feed."""
        github_publisher.export_static_site(output_dir=self.dist_dir, db_path=self.db_path)
        catalog_path = os.path.join(self.dist_dir, "feed-catalog.json")
        self.assertTrue(os.path.exists(catalog_path))

        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        breaking_entries = [c for c in catalog["category_feeds"] if c["id"] == "breaking"]
        self.assertEqual(len(breaking_entries), 1)
        entry = breaking_entries[0]
        self.assertEqual(entry["name"], "عاجل")
        self.assertTrue(entry["url"].endswith("/feeds/breaking.xml"))

    def test_flask_route_serve_breaking_rss(self):
        """Verify the Flask route /feeds/breaking.xml serves valid RSS."""
        response = self.client.get("/feeds/breaking.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"application/rss+xml", response.content_type.encode("utf-8"))
        self.assertIn("عاجل".encode("utf-8"), response.data)
        self.assertIn(b"<rss version=\"2.0\"", response.data)

if __name__ == "__main__":
    unittest.main()
