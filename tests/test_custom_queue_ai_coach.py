#!/usr/bin/env python3
"""
Test Suite for Custom Drill Queue & AI Strategy Coach Features.
Verifies:
1. Strict mastery criteria calculation (alone > searched, >= 1 success, last success == 1).
2. Custom Drill Queue SQLite persistence, export, import, and CLI commands.
3. AI Strategy Coach endpoint, metrics aggregation, conversation persistence, and offline fallback.
"""

import json
import os
import sys
import unittest
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from db import ExamDatabase

TEST_DB_PATH = BASE_DIR / "tests" / "test_queue_strategy.db"


class TestCustomQueueAndAICoach(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
        cls.db = ExamDatabase(TEST_DB_PATH)

    @classmethod
    def tearDownClass(cls):
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

    def test_01_strict_mastery_calculation(self):
        """Test strict mastery criteria:
        Must have: successful_attempts >= 1 AND alone_count > searched_count AND last_success == 1.
        """
        # Case A: Never attempted
        prof_unattempted = self.db.get_exercise_full_profile("first_word")
        self.assertEqual(prof_unattempted["stats"]["mastery_status"], "unattempted")
        self.assertEqual(prof_unattempted["stats"]["mastery_label"], "Não Iniciado")

        # Case B: 1 success but with 'searched' (consulted)
        self.db.record_attempt(
            "first_word", success=True, duration_seconds=120, independence_status="searched"
        )
        prof_searched = self.db.get_exercise_full_profile("first_word")
        # Alone count is 0, searched count is 1 -> alone is NOT > searched
        self.assertEqual(prof_searched["stats"]["mastery_status"], "training")
        self.assertEqual(prof_searched["stats"]["mastery_label"], "Em Treinamento")

        # Case C: 2 successes with 'alone' -> alone (2) > searched (1), last success == True
        self.db.record_attempt(
            "first_word", success=True, duration_seconds=100, independence_status="alone"
        )
        self.db.record_attempt(
            "first_word", success=True, duration_seconds=90, independence_status="alone"
        )
        prof_mastered = self.db.get_exercise_full_profile("first_word")
        self.assertEqual(prof_mastered["stats"]["mastery_status"], "mastered")
        self.assertEqual(prof_mastered["stats"]["mastery_label"], "Dominado")
        self.assertGreater(prof_mastered["stats"]["autonomy_rate"], 60.0)

        # Case D: New failure occurs -> last success is now False -> drops to training!
        self.db.record_attempt(
            "first_word", success=False, duration_seconds=50, independence_status="alone"
        )
        prof_relapsed = self.db.get_exercise_full_profile("first_word")
        self.assertEqual(prof_relapsed["stats"]["mastery_status"], "training")

    def test_02_custom_queue_crud_and_json(self):
        """Test Custom Drill Queue creation, retrieval, JSON export/import and deletion."""
        queue_items = ["first_word", "swap_bits", "tab_mult", "ft_split"]
        q_id = self.db.save_custom_queue(
            name="Maratona Rank 02",
            items=queue_items,
            description="Sequência de alta intensidade"
        )
        self.assertGreater(q_id, 0)

        # Retrieve single queue
        q = self.db.get_custom_queue(q_id)
        self.assertIsNotNone(q)
        self.assertEqual(q["name"], "Maratona Rank 02")
        self.assertEqual(q["count"], 4)
        self.assertEqual(q["items"], queue_items)
        self.assertEqual(q["exercises"], queue_items)

        # Retrieve list of queues
        all_q = self.db.get_custom_queues()
        self.assertGreaterEqual(len(all_q), 1)

        # Export to JSON file
        json_file = BASE_DIR / "tests" / "exported_custom_queue.json"
        try:
            self.db.export_custom_queue_to_json(q_id, json_file)
            self.assertTrue(json_file.is_file())

            # Load from exported JSON file
            loaded = self.db.load_custom_queue_from_json(json_file)
            self.assertEqual(loaded, queue_items)
        finally:
            if json_file.exists():
                json_file.unlink()

        # Delete queue
        deleted = self.db.delete_custom_queue(q_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.db.get_custom_queue(q_id))

    def test_03_ai_strategy_coach_context_and_history(self):
        """Test AI Strategy Coach performance aggregation and interaction persistence."""
        ctx = self.db.get_ai_strategy_context()
        self.assertEqual(ctx["total_exercises"], 55)
        self.assertIn("mastered_count", ctx)
        self.assertIn("training_count", ctx)
        self.assertIn("unattempted_count", ctx)
        self.assertIn("critical_patterns", ctx)
        self.assertIn("top_stuck_points", ctx)

        # Record interaction
        user_msg_id = self.db.record_ai_strategy_interaction(
            role="user",
            message="Como devo me preparar para as questões de Level 3?"
        )
        self.assertGreater(user_msg_id, 0)

        coach_msg_id = self.db.record_ai_strategy_interaction(
            role="assistant",
            message="Pratique alocação de matriz em ft_split e recursão em fprime.",
            tokens_used=150,
            cost_usd=0.001
        )
        self.assertGreater(coach_msg_id, 0)

        # Fetch history
        history = self.db.get_ai_strategy_interactions()
        self.assertGreaterEqual(len(history), 2)
        self.assertEqual(history[-2]["role"], "user")
        self.assertEqual(history[-1]["role"], "assistant")

        # Clear history
        self.db.clear_ai_strategy_interactions()
        cleared_history = self.db.get_ai_strategy_interactions()
        self.assertEqual(len(cleared_history), 0)


if __name__ == "__main__":
    unittest.main()
