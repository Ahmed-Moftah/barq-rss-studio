import unittest
import tempfile
import os
import shutil
from app import create_app
import database

class RoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_studio.db")
        self.dist_dir = os.path.join(self.temp_dir, "dist")
        os.makedirs(self.dist_dir, exist_ok=True)
        
        self.app = create_app({
            "TESTING": True,
            "DB_PATH": self.db_path,
            "DIST_DIR": self.dist_dir,
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_dashboard_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("استوديو برق".encode("utf-8"), response.data)

    def test_reports_list_route(self):
        response = self.client.get("/reports")
        self.assertEqual(response.status_code, 200)

    def test_create_and_preview_report(self):
        response = self.client.post("/reports/new", data={
            "title": "تقرير اختبار المسارات",
            "slug": "test-route-report",
            "category": "politics",
            "summary": "موجز تجريبي",
            "content": "محتوى التقرير التحريري",
            "author": "محرر تجريبي",
            "status": "published"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("تقرير اختبار المسارات".encode("utf-8"), response.data)

    def test_feed_xml_endpoint(self):
        # Insert a published report
        database.create_report({
            "title": "تقرير الخلاصة المباشرة",
            "slug": "direct-rss-report",
            "category": "tech",
            "content": "محتوى تقني",
            "status": "published"
        }, db_path=self.db_path)

        response = self.client.get("/feed.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<rss version=\"2.0\"", response.data)
        self.assertIn("تقرير الخلاصة المباشرة".encode("utf-8"), response.data)

    def test_category_feed_endpoint(self):
        response = self.client.get("/feeds/tech.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<rss version=\"2.0\"", response.data)

    def test_api_parse_chatgpt(self):
        response = self.client.post("/api/parse-chatgpt", json={
            "text": "# عنوان من الذكاء الاصطناعي\n**التصنيف:** اقتصاد وأعمال\n**الموجز:** فكرة سريعة\n\nنص التقرير..."
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["title"], "عنوان من الذكاء الاصطناعي")
        self.assertEqual(data["data"]["category"], "economy")

    def test_api_publish_endpoint(self):
        response = self.client.post("/api/publish", json={
            "commit_message": "اختبار النشر التلقائي"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(os.path.exists(os.path.join(self.dist_dir, "feed.xml")))
        self.assertTrue(os.path.exists(os.path.join(self.dist_dir, "index.html")))

if __name__ == "__main__":
    unittest.main()
