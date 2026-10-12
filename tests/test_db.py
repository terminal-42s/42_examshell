"""
Unit tests for db.py in 42 Examshell with submitted_code and error_reason.
"""

import tempfile
import unittest
from pathlib import Path

from db import ExamDatabase, detect_error_reason, format_duration


class TestExamDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_stats.db"
        self.db = ExamDatabase(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seed_exercises_count_and_levels(self):
        exercises = self.db.get_all_exercises()
        self.assertEqual(len(exercises), 55, "There must be exactly 55 exercises seeded.")

        level0 = self.db.get_exercises_by_level(0)
        level1 = self.db.get_exercises_by_level(1)
        level2 = self.db.get_exercises_by_level(2)
        level3 = self.db.get_exercises_by_level(3)

        self.assertEqual(len(level0), 12)
        self.assertEqual(len(level1), 18)
        self.assertEqual(len(level2), 15)
        self.assertEqual(len(level3), 10)

    def test_detect_error_reason(self):
        self.assertEqual(detect_error_reason(True, ""), "Success")
        self.assertEqual(
            detect_error_reason(False, "Program terminated with Segmentation fault (core dumped)"),
            "Segmentation Fault",
        )
        self.assertEqual(
            detect_error_reason(False, "TIMEOUT: Process killed after 10s"),
            "Memory Leak / Timeout",
        )
        self.assertEqual(
            detect_error_reason(False, "gcc: error: undefined reference to 'ft_putchar'"),
            "Compilation Error",
        )
        self.assertEqual(
            detect_error_reason(False, "FAIL: Expected Output: 'foo' Your Output: 'bar'"),
            "Wrong Output / Mismatch",
        )
        self.assertEqual(
            detect_error_reason(False, "Norme: Major error line 12"),
            "Norme Error",
        )

    def test_record_attempt_with_code_and_reason(self):
        code_sample = '#include <unistd.h>\nint main() { write(1, "a", 1); return 0; }'
        trace_sample = "Segmentation fault (SIGSEGV)"

        attempt_id = self.db.record_attempt(
            exercise_id="first_word",
            success=False,
            duration_seconds=125,
            error_trace=trace_sample,
            submitted_code=code_sample,
        )
        self.assertGreater(attempt_id, 0)

        attempt = self.db.get_attempt_by_id(attempt_id)
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.exercise_id, "first_word")
        self.assertFalse(attempt.success)
        self.assertEqual(attempt.duration_seconds, 125)
        self.assertEqual(attempt.error_trace, trace_sample)
        self.assertEqual(attempt.submitted_code, code_sample)
        self.assertEqual(attempt.error_reason, "Segmentation Fault")

        # Check latest attempt id
        latest_id = self.db.get_latest_attempt_id()
        self.assertEqual(latest_id, attempt_id)

    def test_schema_migration_preserves_data(self):
        # Create an attempt
        self.db.record_attempt("fizzbuzz", True, 45, submitted_code="/* valid code */")
        # Re-initialize database to trigger migration path
        self.db.init_db()
        history = self.db.get_attempts_for_exercise("fizzbuzz")
        self.assertEqual(len(history), 1)
        self.assertTrue(history[0].success)
        self.assertEqual(history[0].submitted_code, "/* valid code */")

    def test_get_exercises_by_pattern_with_spaces(self):
        direct_lookup = self.db.get_exercises_by_pattern("ASCII Direct Lookup")
        direct_ids = [e.id for e in direct_lookup]
        self.assertEqual(sorted(direct_ids), ["inter", "union"])

        skip_ws = self.db.get_exercises_by_pattern("Skip Whitespace")
        self.assertGreaterEqual(len(skip_ws), 11)
        self.assertIn("first_word", [e.id for e in skip_ws])
        self.assertIn("ft_split", [e.id for e in skip_ws])

        tabela_ascii = self.db.get_exercises_by_pattern("Tabela ASCII")
        self.assertGreaterEqual(len(tabela_ascii), 10)
        self.assertIn("rot_13", [e.id for e in tabela_ascii])
        self.assertIn("camel_to_snake", [e.id for e in tabela_ascii])

    def test_timeline_stats_and_day_details(self):
        # Record attempts for multiple exercises
        self.db.record_attempt("first_word", True, 60, submitted_code="/* ok */")
        self.db.record_attempt("rot_13", False, 120, error_trace="Mismatch on input abc", submitted_code="/* fail */")
        self.db.record_attempt("inter", True, 90, submitted_code="/* lookup */")

        timeline = self.db.get_timeline_stats()
        self.assertGreaterEqual(len(timeline), 1)

        today_entry = timeline[0]
        self.assertIn("date", today_entry)
        self.assertEqual(today_entry["total_attempts"], 3)
        self.assertEqual(today_entry["successful_attempts"], 2)
        self.assertEqual(today_entry["failed_attempts"], 1)
        self.assertAlmostEqual(today_entry["success_rate"], 66.7, places=1)
        self.assertEqual(sorted(today_entry["exercises_done"]), ["first_word", "inter", "rot_13"])

        # Test day details
        day_details = self.db.get_day_details(today_entry["date"])
        self.assertEqual(day_details["total_attempts"], 3)
        self.assertEqual(day_details["successful_attempts"], 2)
        self.assertEqual(len(day_details["attempts"]), 3)
        self.assertGreater(len(day_details["patterns_breakdown"]), 0)

        # Test filtered attempts
        filtered_succ = self.db.get_filtered_attempts(status="success")
        self.assertEqual(len(filtered_succ), 2)

        filtered_fail = self.db.get_filtered_attempts(status="failed")
        self.assertEqual(len(filtered_fail), 1)
        self.assertEqual(filtered_fail[0]["exercise_id"], "rot_13")

        filtered_pattern = self.db.get_filtered_attempts(pattern="ASCII Direct Lookup")
        self.assertEqual(len(filtered_pattern), 1)
        self.assertEqual(filtered_pattern[0]["exercise_id"], "inter")

    def test_ai_interactions_recording_and_retrieval(self):
        att_id = self.db.record_attempt("inter", False, 100, error_trace="Bus error")

        # Record user message and assistant reply
        msg1_id = self.db.record_ai_interaction(
            exercise_id="inter",
            role="user",
            message="Por que meu código deu bus error?",
            attempt_id=att_id,
        )
        self.assertGreater(msg1_id, 0)

        msg2_id = self.db.record_ai_interaction(
            exercise_id="inter",
            role="assistant",
            message="Verifique o alinhamento de memória e limites de ponteiro.",
            attempt_id=att_id,
            tokens_used=450,
            cost_usd=0.0035,
        )
        self.assertGreater(msg2_id, 0)

        # Retrieve interactions
        history = self.db.get_ai_interactions(exercise_id="inter", attempt_id=att_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertIn("bus error", history[0]["message"])
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["tokens_used"], 450)

        # Clear interactions
        self.db.clear_ai_interactions(exercise_id="inter")
        cleared = self.db.get_ai_interactions(exercise_id="inter")
        self.assertEqual(len(cleared), 0)

    def test_record_attempt_with_self_assessment_and_update_feedback(self):
        att_id = self.db.record_attempt(
            exercise_id="ft_split",
            success=True,
            duration_seconds=300,
            submitted_code="/* split code */",
            user_notes="Revisar alocação da matriz",
            independence_status="alone",
            stuck_point="Malloc dos ponteiros",
        )
        self.assertGreater(att_id, 0)

        attempt = self.db.get_attempt_by_id(att_id)
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.user_notes, "Revisar alocação da matriz")
        self.assertEqual(attempt.independence_status, "alone")
        self.assertEqual(attempt.stuck_point, "Malloc dos ponteiros")

        # Update feedback
        ok = self.db.update_attempt_feedback(
            attempt_id=att_id,
            user_notes="Notas atualizadas: funcionou perfeitamente!",
            independence_status="alone",
            stuck_point="Nenhum",
        )
        self.assertTrue(ok)

        updated = self.db.get_attempt_by_id(att_id)
        self.assertEqual(updated.user_notes, "Notas atualizadas: funcionou perfeitamente!")
        self.assertEqual(updated.stuck_point, "Nenhum")

    def test_deep_analytics_report(self):
        # Seed attempts with reflexive assessment
        self.db.record_attempt(
            "first_word", True, 45, submitted_code="/* ok */",
            independence_status="alone", stuck_point=""
        )
        self.db.record_attempt(
            "ft_split", False, 180, submitted_code="/* fail */", error_trace="Segfault",
            independence_status="searched", stuck_point="Sintaxe do malloc"
        )
        self.db.record_attempt(
            "ft_split", True, 120, submitted_code="/* ok */",
            independence_status="alone", stuck_point="Malloc dos ponteiros"
        )

        report = self.db.get_deep_analytics_report()
        self.assertIn("autonomy_report", report)
        self.assertIn("level_report", report)
        self.assertIn("exercise_report", report)
        self.assertIn("daily_report", report)

        auto = report["autonomy_report"]
        self.assertGreaterEqual(auto["total_submissions"], 3)
        self.assertGreaterEqual(auto["alone_count"], 2)
        self.assertGreaterEqual(auto["searched_count"], 1)
        self.assertGreater(len(auto["top_stuck_points"]), 0)

        # Level report should cover levels 0 to 3
        self.assertEqual(len(report["level_report"]), 4)

        # Filter by level
        lvl_report = self.db.get_deep_analytics_report(level=0)
        self.assertEqual(len(lvl_report["level_report"]), 1)
        self.assertEqual(lvl_report["level_report"][0]["level"], 0)


if __name__ == "__main__":
    unittest.main()
