import unittest
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime, timezone
import rss_generator

class RSSTestCase(unittest.TestCase):
    def test_rfc822_date_formatting(self):
        dt = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)
        formatted = rss_generator.format_rfc822(dt)
        self.assertIn("2026", formatted)
        # Verify email.utils can parse it back
        parsed_tuple = email.utils.parsedate_to_datetime(formatted)
        self.assertEqual(parsed_tuple.year, 2026)
        self.assertEqual(parsed_tuple.month, 10)

    def test_rss2_xml_validity(self):
        channel_info = {
            "title": "برق | استوديو التقارير",
            "base_url": "https://ahmed-moftah.github.io/barq-rss-studio",
            "link": "https://ahmed-moftah.github.io/barq-rss-studio",
            "description": "خلاصة التقارير التحريرية القياسية",
            "language": "ar"
        }
        items = [
            {
                "title": "تقرير عن الذكاء الاصطناعي العربي",
                "slug": "arabic-ai-report",
                "category": "tech",
                "summary": "ملخص تقرير الذكاء الاصطناعي.",
                "content_html": "<p>نص التقرير <strong>التحليلي</strong> الكامل.</p>",
                "author": "فريق التحرير التقني",
                "published_at": "2026-10-22T08:00:00+00:00",
                "image_url": "https://example.com/image.jpg"
            }
        ]

        xml_output = rss_generator.generate_feed_xml(channel_info, items)
        
        # Verify XML well-formedness
        root = ET.fromstring(xml_output)
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.attrib.get("version"), "2.0")

        channel = root.find("channel")
        self.assertIsNotNone(channel)
        self.assertEqual(channel.find("language").text, "ar")
        self.assertEqual(channel.find("title").text, "برق | استوديو التقارير")

        item = channel.find("item")
        self.assertIsNotNone(item)
        self.assertEqual(item.find("title").text, "تقرير عن الذكاء الاصطناعي العربي")
        self.assertEqual(item.find("link").text, "https://ahmed-moftah.github.io/barq-rss-studio/articles/arabic-ai-report.html")
        
        # Enclosure test
        enclosure = item.find("enclosure")
        self.assertIsNotNone(enclosure)
        self.assertEqual(enclosure.attrib.get("url"), "https://example.com/image.jpg")
        self.assertEqual(enclosure.attrib.get("type"), "image/jpeg")

        # Full content test in both description and content:encoded
        desc_text = item.find("description").text
        self.assertIn("نص التقرير", desc_text)
        self.assertIn("التحليلي", desc_text)

    def test_draft_exclusion_from_rss(self):
        channel_info = {
            "title": "برق",
            "base_url": "https://ahmed-moftah.github.io/barq-rss-studio"
        }
        items = [
            {"title": "تقرير منشور", "slug": "pub", "status": "published", "content": "محتوى"},
            {"title": "مسودة سرية", "slug": "draft", "status": "draft", "content": "محتوى مسودة"}
        ]
        xml_output = rss_generator.generate_feed_xml(channel_info, items)
        self.assertIn("تقرير منشور", xml_output)
        self.assertNotIn("مسودة سرية", xml_output)

    def test_managing_editor_placeholder_omission(self):
        # 1. Placeholder .local email should be cleanly omitted from XML
        channel_info = {
            "title": "برق",
            "managing_editor": "فريق التحرير (editor@barq.local)"
        }
        xml_out = rss_generator.generate_feed_xml(channel_info, [])
        self.assertNotIn("<managingEditor>", xml_out)

        # 2. Valid email should be included
        channel_info_valid = {
            "title": "برق",
            "managing_editor": "editor@barq-news.com"
        }
        xml_out_valid = rss_generator.generate_feed_xml(channel_info_valid, [])
        self.assertIn("<managingEditor><![CDATA[editor@barq-news.com]]></managingEditor>", xml_out_valid)

    def test_cdata_wrapping_special_characters(self):
        text = 'عنوان يحتوي على "علامات تنصيص" و <رموز> و ]]> تسلسل'
        wrapped = rss_generator.wrap_cdata(text)
        self.assertTrue(wrapped.startswith("<![CDATA["))
        self.assertTrue(wrapped.endswith("]]>"))

if __name__ == "__main__":
    unittest.main()
