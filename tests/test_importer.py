import unittest
import importer

class ImporterTestCase(unittest.TestCase):
    def test_parse_structured_markdown(self):
        sample = """# عنوان التقرير: الصعود الرقمي للذكاء الاصطناعي في الإعلام
**التصنيف:** تكنولوجيا وابتكار
**الموجز:** قراءة في دور النماذج اللغوية في أتمتة العمل الصحفي وغرف الأخبار.
**الوسوم:** ذكاء اصطناعي, إعلام, تقنية
**الكاتب:** وحدة التحقيقات التقنية
**المصدر:** ChatGPT / إعداد مشترك

## المقدمة
تشهد صناعة الصحافة تحولات جذرية متسارعة...

### المحاور الأساسية
* المحور الأول: توليد الخلاصات الآلية.
* المحور الثاني: تدقيق المحتوى."""

        parsed = importer.parse_chatgpt_report(sample)
        self.assertEqual(parsed["title"], "الصعود الرقمي للذكاء الاصطناعي في الإعلام")
        self.assertEqual(parsed["category"], "tech")
        self.assertIn("قراءة في دور النماذج اللغوية", parsed["summary"])
        self.assertIn("ذكاء اصطناعي", parsed["tags"])
        self.assertEqual(parsed["author"], "وحدة التحقيقات التقنية")
        self.assertIn("المقدمة", parsed["content"])

    def test_parse_json_format(self):
        json_sample = """{
            "title": "مستقبل تجارة الغاز المسال",
            "category": "اقتصاد",
            "summary": "تحليل مسارات الطلب الآسيوي على الغاز.",
            "content": "محتوى التقرير الاقتصادي المعمق...",
            "tags": "غاز, طاقة, اقتصاد",
            "author": "المكتب الاستشاري"
        }"""
        parsed = importer.parse_chatgpt_report(json_sample)
        self.assertEqual(parsed["title"], "مستقبل تجارة الغاز المسال")
        self.assertEqual(parsed["category"], "economy")
        self.assertEqual(parsed["author"], "المكتب الاستشاري")
        self.assertIn("تحليل مسارات", parsed["summary"])

    def test_category_fuzzy_mapping(self):
        self.assertEqual(importer.map_category_string("عاجل"), "breaking")
        self.assertEqual(importer.map_category_string("خبر عاجل الآن"), "breaking")
        self.assertEqual(importer.map_category_string("breaking"), "breaking")
        self.assertEqual(importer.map_category_string("شؤون سياسية ودولية"), "politics")
        self.assertEqual(importer.map_category_string("اقتصاد وأسواق المال"), "economy")
        self.assertEqual(importer.map_category_string("الذكاء الاصطناعي والتقنية"), "tech")
        self.assertEqual(importer.map_category_string("تقدير موقف استراتيجي"), "analysis")
        self.assertEqual(importer.map_category_string("تحقيق استقصائي سري"), "investigations")
        self.assertEqual(importer.map_category_string("أخبار متنوعة"), "reports")

if __name__ == "__main__":
    unittest.main()
