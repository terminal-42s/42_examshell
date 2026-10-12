"""
Unit tests for server.py HTTP endpoints and API routing.
"""

import json
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from http.server import HTTPServer

from db import ExamDatabase
import server


class TestServerAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup test server on ephemeral port (e.g. 58921)
        cls.port = 58921
        cls.server = HTTPServer(("127.0.0.1", cls.port), server.DashboardRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_dashboard_html(self):
        url = f"http://127.0.0.1:{self.port}/"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            content_type = resp.headers.get("Content-Type", "")
            self.assertIn("text/html", content_type)
            html = resp.read().decode("utf-8")
            self.assertIn("Examshell", html)
            self.assertIn("Tutor Pedagógico 42", html)

    def test_get_api_stats(self):
        url = f"http://127.0.0.1:{self.port}/api/stats"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["total_exercises"], 55)
            self.assertIn("pattern_summary", data)
            self.assertIn("exercises", data)
            self.assertEqual(len(data["exercises"]), 55)

    def test_get_api_latest_and_history(self):
        url = f"http://127.0.0.1:{self.port}/api/latest"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("latest_attempt_id", data)

        url_hist = f"http://127.0.0.1:{self.port}/api/history"
        with urllib.request.urlopen(url_hist) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("attempts", data)

    def test_get_api_timeline_and_day_details(self):
        # Timeline endpoint
        url_tl = f"http://127.0.0.1:{self.port}/api/stats/timeline"
        with urllib.request.urlopen(url_tl) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("timeline", data)

        # Day details endpoint (today's date)
        import datetime
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        url_day = f"http://127.0.0.1:{self.port}/api/stats/day-details?date={today_str}"
        with urllib.request.urlopen(url_day) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("date", data)
            self.assertIn("attempts", data)
            self.assertIn("patterns_breakdown", data)

        # History with query parameters
        url_filt = f"http://127.0.0.1:{self.port}/api/history?status=success&limit=10"
        with urllib.request.urlopen(url_filt) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("attempts", data)

    def test_post_ai_tutor_response(self):
        url = f"http://127.0.0.1:{self.port}/api/ai-tutor"
        payload = json.dumps({
            "exercise_id": "first_word",
            "code": "#include <unistd.h>\nint main(int ac, char **av) { write(1, av[1][0], 1); return 0; }",
            "trace": "Segmentation fault (core dumped)"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("tutor_response", data)
            if data.get("azure_configured"):
                self.assertIn("usage", data)
                self.assertIn("prompt_tokens", data["usage"])
                self.assertIn("total_tokens", data["usage"])
            resp_lower = data["tutor_response"].lower()
            self.assertTrue(
                "segmentation fault" in resp_lower or "segmentação" in resp_lower or "ponteiro" in resp_lower,
                f"Tutor response does not discuss memory/segmentation issue: {data['tutor_response'][:100]}"
            )

    def test_ai_chat_history_and_clear_endpoints(self):
        # 1. Query history for first_word
        url_hist = f"http://127.0.0.1:{self.port}/api/ai-chat/history?exercise_id=first_word"
        with urllib.request.urlopen(url_hist) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["exercise_id"], "first_word")
            self.assertIn("messages", data)

        # 2. Clear history for first_word
        url_clear = f"http://127.0.0.1:{self.port}/api/ai-chat/clear"
        payload = json.dumps({"exercise_id": "first_word"}).encode("utf-8")
        req = urllib.request.Request(url_clear, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")

        # 3. Verify history is empty
        with urllib.request.urlopen(url_hist) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(len(data["messages"]), 0)

    def test_reports_analytics_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/reports/analytics"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("autonomy_report", data)
            self.assertIn("level_report", data)
            self.assertIn("exercise_report", data)
            self.assertIn("daily_report", data)
            self.assertEqual(len(data["level_report"]), 4)

    def test_attempt_feedback_endpoint(self):
        # 1. Record an attempt directly via database
        att_id = server.db.record_attempt(
            "first_word", True, 45, submitted_code="/* ok */"
        )

        # 2. Update feedback via POST /api/attempts/<id>/feedback
        url_fb = f"http://127.0.0.1:{self.port}/api/attempts/{att_id}/feedback"
        payload = json.dumps({
            "independence_status": "alone",
            "stuck_point": "Nenhum",
            "user_notes": "Memorizei o algoritmo!",
        }).encode("utf-8")

        req = urllib.request.Request(url_fb, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["attempt"]["independence_status"], "alone")
            self.assertEqual(data["attempt"]["stuck_point"], "Nenhum")

        # 3. Verify attempt details returned by GET /api/attempt/<id>
        url_att = f"http://127.0.0.1:{self.port}/api/attempt/{att_id}"
        with urllib.request.urlopen(url_att) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["independence_status"], "alone")
            self.assertEqual(data["stuck_point"], "Nenhum")
            self.assertEqual(data["user_notes"], "Memorizei o algoritmo!")


if __name__ == "__main__":
    unittest.main()
