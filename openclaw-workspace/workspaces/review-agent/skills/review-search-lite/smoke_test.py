import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import review_search


SEARCH_HTML = """
<html>
  <body>
    <a href="/Restaurant_Review-g293916-d12345-Reviews-Eat_Me_Bangkok-Bangkok.html">Eat Me Bangkok</a>
    <a href="/Restaurant_Review-g293916-d67890-Reviews-Other_Cafe-Bangkok.html">Other Cafe</a>
  </body>
</html>
"""

PAGE_HTML = """
<html>
  <head>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": "Eat Me Bangkok",
        "address": {
          "streetAddress": "1 Soi Phiphat 2",
          "addressLocality": "Bangkok",
          "addressCountry": "Thailand"
        },
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "4.5",
          "reviewCount": "1234"
        },
        "review": [
          {
            "@type": "Review",
            "author": {"@type": "Person", "name": "Alex"},
            "datePublished": "2026-03-01",
            "reviewBody": "Inventive dishes and warm service.",
            "reviewRating": {"@type": "Rating", "ratingValue": "5"}
          }
        ]
      }
    </script>
  </head>
</html>
"""


class ReviewSearchLiteTests(unittest.TestCase):
    def test_tripadvisor_search_candidates_are_extracted(self):
        paths = review_search._extract_tripadvisor_paths(SEARCH_HTML)
        self.assertEqual(len(paths), 2)
        best_path = max(
            paths,
            key=lambda path: review_search._score_tripadvisor_candidate(path, "Eat Me Bangkok", "Bangkok"),
        )
        self.assertIn("Eat_Me_Bangkok", best_path)

    def test_tripadvisor_page_jsonld_is_parsed(self):
        jsonld = review_search._extract_jsonld_objects(PAGE_HTML)
        place = review_search._parse_tripadvisor_place_from_jsonld(
            jsonld,
            "https://www.tripadvisor.com/Restaurant_Review-g293916-d12345-Reviews-Eat_Me_Bangkok-Bangkok.html",
            "Eat Me Bangkok",
        )
        self.assertIsNotNone(place)
        self.assertEqual(place.name, "Eat Me Bangkok")
        self.assertEqual(place.review_count, 1234)
        self.assertAlmostEqual(place.rating or 0.0, 4.5)

        reviews = review_search._extract_tripadvisor_reviews_from_jsonld(jsonld)
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].author, "Alex")
        self.assertEqual(reviews[0].content, "Inventive dishes and warm service.")

    def test_inline_summary_includes_quote_when_available(self):
        summary = review_search._build_inline_summary(
            requested_place_name="Eat Me Bangkok",
            place={"name": "Eat Me Bangkok", "rating": 4.5, "review_count": 1234},
            review={"content": "Inventive dishes and warm service."},
            fallback_summary=None,
        )
        self.assertIn("Eat Me Bangkok", summary)
        self.assertIn("4.5 stars from 1,234 reviews", summary)
        self.assertIn('"Inventive dishes and warm service."', summary)

    def test_inline_summary_omits_quote_when_only_summary_exists(self):
        summary = review_search._build_inline_summary(
            requested_place_name="Eat Me Bangkok",
            place={"name": "Eat Me Bangkok"},
            review=None,
            fallback_summary={"average_rating": 4.5, "total_reviews": 1234},
        )
        self.assertIn("4.5 stars from 1,234 reviews", summary)
        self.assertNotIn('"', summary)

    def test_extract_first_json_object(self):
        payload = review_search._extract_first_json_object(
            '```json\n{"resolved_name":"Mono Cafe Bangkok","average_rating":4.4,"total_reviews":4000}\n```'
        )
        self.assertIsNotNone(payload)
        self.assertEqual(payload["resolved_name"], "Mono Cafe Bangkok")
        self.assertEqual(payload["total_reviews"], 4000)


if __name__ == "__main__":
    unittest.main()
