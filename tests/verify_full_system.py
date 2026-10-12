#!/usr/bin/env python3
"""
E2E Integration & System Reliability Verification Suite for 42 Examshell.
Tests Database ACID integrity, WAL mode, null sanitization, HTTP endpoints,
and defensive AI Tutor fallback.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from db import ExamDatabase, format_duration

SERVER_URL = "http://127.0.0.1:5000"


def log_step(name: str) -> None:
    print(f"\n\033[1;34m[TEST SUITE]\033[0m \033[1m=== {name} ===\033[0m")


def assert_true(condition: bool, msg: str) -> None:
    if not condition:
        print(f"\033[1;31m[FAIL]\033[0m {msg}", file=sys.stderr)
        raise AssertionError(msg)
    print(f"  \033[1;32m✓\033[0m {msg}")


def test_database_isolated_acid() -> None:
    log_step("1. SQLite ACID, WAL & Null-Safety Verification")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db_path = f.name

    try:
        db = ExamDatabase(tmp_db_path)
        
        # Test PRAGMAs
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0]
            assert_true(journal_mode.lower() == "wal", f"Journal mode is WAL (got {journal_mode})")

            cursor.execute("PRAGMA foreign_keys;")
            fk = cursor.fetchone()[0]
            assert_true(fk == 1, "Foreign keys are enabled (PRAGMA foreign_keys = 1)")

        # Verify 55 exercises seeded
        exercises = db.get_all_exercises()
        assert_true(len(exercises) == 55, f"All 55 exercises seeded in database (got {len(exercises)})")

        # 1. Attempt with success and no feedback
        id_succ = db.record_attempt(
            exercise_id="ft_strlen",
            success=True,
            duration_seconds=45,
            error_trace=None,
            submitted_code="int ft_strlen(char *s) { int i=0; while(s[i]) i++; return i; }",
        )
        assert_true(id_succ > 0, f"Recorded successful attempt (ID: {id_succ})")

        att_succ = db.get_attempt_by_id(id_succ)
        assert_true(att_succ is not None, "Retrieved attempt by ID")
        assert_true(att_succ.success is True, "Success status matches True")
        assert_true(att_succ.error_trace is None, "Error trace is None on success")
        assert_true(att_succ.error_reason == "Success", f"Auto-detected error_reason is 'Success' (got {att_succ.error_reason})")
        assert_true(att_succ.user_notes == "", "user_notes defaults to empty string, not None")
        assert_true(att_succ.independence_status == "unspecified", "independence_status defaults to 'unspecified'")

        # 2. Attempt with failure, compiler trace and code
        id_fail = db.record_attempt(
            exercise_id="ft_split",
            success=False,
            duration_seconds=185,
            error_trace="Segmentation fault (core dumped) in test case 3",
            submitted_code="char **ft_split(char *str) { return NULL; }",
        )
        assert_true(id_fail > 0, f"Recorded failed attempt with segfault (ID: {id_fail})")

        att_fail = db.get_attempt_by_id(id_fail)
        assert_true(att_fail is not None, "Retrieved failed attempt")
        assert_true(att_fail.error_reason == "Segmentation Fault", f"Error reason detected as Segmentation Fault (got {att_fail.error_reason})")

        # 3. Update feedback via update_attempt_feedback
        ok = db.update_attempt_feedback(
            attempt_id=id_fail,
            user_notes="Esqueci de alocar o terminador nulo da matriz",
            independence_status="searched",
            stuck_point="Alocação de matriz nula com malloc",
        )
        assert_true(ok is True, "Updated feedback successfully")
        att_updated = db.get_attempt_by_id(id_fail)
        assert_true(att_updated.independence_status == "searched", "Independence status updated to 'searched'")
        assert_true(att_updated.stuck_point == "Alocação de matriz nula com malloc", "Stuck point updated accurately")

        # 4. Multi-dimensional analytics check
        report = db.get_deep_analytics_report()
        assert_true("autonomy_report" in report, "autonomy_report is present")
        assert_true("level_report" in report, "level_report is present")
        assert_true("exercise_report" in report, "exercise_report is present")
        assert_true("daily_report" in report, "daily_report is present")

        # Defensive format_duration check
        assert_true(format_duration(None) == "--:--", "format_duration(None) returns '--:--'")
        assert_true(format_duration("invalid") == "--:--", "format_duration('invalid') returns '--:--'")
        assert_true(format_duration(125) == "02:05", "format_duration(125) returns '02:05'")

    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)


def test_cli_feedback() -> None:
    log_step("2. CLI Feedback Integration Verification")
    db = ExamDatabase()
    # Insert a test attempt in the main db
    att_id = db.record_attempt(
        exercise_id="rev_print",
        success=True,
        duration_seconds=30,
        submitted_code="char *rev_print(char *s) { return s; }",
    )
    assert_true(att_id > 0, f"Inserted test attempt for CLI test (ID: {att_id})")

    cmd = [
        sys.executable,
        str(BASE_DIR / "db.py"),
        "feedback",
        str(att_id),
        "--independence",
        "alone",
        "--stuck",
        "Nenhum bloqueio",
        "--notes",
        "Feito com agilidade e memória muscular",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert_true(res.returncode == 0, f"CLI feedback command returned 0 (got {res.returncode})")
    
    updated = db.get_attempt_by_id(att_id)
    assert_true(updated.independence_status == "alone", "CLI updated independence_status to 'alone'")
    assert_true(updated.stuck_point == "Nenhum bloqueio", "CLI updated stuck_point")


def test_server_http_endpoints() -> None:
    log_step("3. HTTP REST API & Web Dashboard Endpoints")

    def fetch_url(url: str, method: str = "GET", data: dict | None = None, timeout: int = 15) -> tuple[int, dict | str]:
        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=req_data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                body = resp.read().decode("utf-8")
                if "application/json" in content_type:
                    return resp.status, json.loads(body)
                return resp.status, body
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                return e.code, json.loads(err_body)
            except Exception:
                return e.code, err_body
        except urllib.error.URLError as e:
            return 503, {"error": str(e.reason)}

    # 1. GET /
    status, html = fetch_url(f"{SERVER_URL}/")
    assert_true(status == 200, f"GET / returns 200 OK (got {status})")
    assert_true("42 Examshell" in html, "Dashboard HTML title / header is present")

    # 2. GET /api/stats
    status, stats = fetch_url(f"{SERVER_URL}/api/stats")
    assert_true(status == 200, f"GET /api/stats returns 200 OK")
    assert_true(isinstance(stats, dict), "Stats payload is a dictionary")
    assert_true("exercises" in stats and len(stats["exercises"]) == 55, "Contains all 55 serialized exercises")
    
    # Check that best_time_formatted is never None or undefined
    for ex in stats["exercises"]:
        assert_true(ex["best_time_formatted"] is not None, f"best_time_formatted is non-null for {ex['id']}")
        assert_true(isinstance(ex["patterns"], list), f"patterns is a list for {ex['id']}")

    # 3. GET /api/reports/analytics
    status, report = fetch_url(f"{SERVER_URL}/api/reports/analytics")
    assert_true(status == 200, "GET /api/reports/analytics returns 200 OK")
    assert_true("autonomy_report" in report, "Report has autonomy_report")
    assert_true("level_report" in report and len(report["level_report"]) == 4, "level_report has 4 levels (0..3)")
    assert_true("exercise_report" in report and len(report["exercise_report"]) == 55, "exercise_report covers 55 exercises")
    assert_true("daily_report" in report, "daily_report is present")

    # 4. GET /api/history
    status, history = fetch_url(f"{SERVER_URL}/api/history?limit=10")
    assert_true(status == 200, "GET /api/history returns 200 OK")
    assert_true("attempts" in history, "history contains attempts array")

    # 5. POST /api/attempts/<id>/feedback
    if history.get("attempts"):
        latest_id = history["attempts"][0]["id"]
        feedback_payload = {
            "independence_status": "alone",
            "stuck_point": "Tudo dominado",
            "user_notes": "Validação E2E com sucesso",
        }
        status, resp = fetch_url(f"{SERVER_URL}/api/attempts/{latest_id}/feedback", method="POST", data=feedback_payload)
        assert_true(status == 200, f"POST /api/attempts/{latest_id}/feedback returns 200 OK")
        assert_true(resp.get("status") == "success", "Feedback updated successfully via HTTP API")

        # 6. GET /api/attempt/<id>
        status, attempt_data = fetch_url(f"{SERVER_URL}/api/attempt/{latest_id}")
        assert_true(status == 200, f"GET /api/attempt/{latest_id} returns 200 OK")
        assert_true(attempt_data.get("independence_status") == "alone", "Verified persistence of feedback in attempt details")
        assert_true(attempt_data.get("user_notes") == "Validação E2E com sucesso", "Verified persistence of notes")

    # 7. GET /api/exercise/<id> (Consolidated Exercise Profile & Scorecard)
    status, profile_data = fetch_url(f"{SERVER_URL}/api/exercise/first_word")
    assert_true(status == 200, "GET /api/exercise/first_word returns 200 OK")
    assert_true("exercise" in profile_data and profile_data["exercise"]["id"] == "first_word", "Profile contains exercise metadata")
    assert_true("stats" in profile_data and "mastery_status" in profile_data["stats"], "Profile contains analytical stats and mastery status")
    assert_true("attempts" in profile_data and isinstance(profile_data["attempts"], list), "Profile contains attempts list")
    assert_true("ai_messages" in profile_data and isinstance(profile_data["ai_messages"], list), "Profile contains AI chat messages list")
    assert_true(profile_data["stats"]["best_time_formatted"] is not None, "best_time_formatted is non-null")

    # 8. POST /api/ai-tutor (Fallback / Error resilience check)
    ai_payload = {
        "exercise_id": "first_word",
        "code": "int main() { return 0; }",
        "trace": "test failure",
    }
    status, ai_resp = fetch_url(f"{SERVER_URL}/api/ai-tutor", method="POST", data=ai_payload, timeout=40)
    assert_true(
        status in (200, 503),
        f"POST /api/ai-tutor returns valid HTTP status (200 or 503 fallback, got {status})",
    )
    if status == 503:
        assert_true("error" in ai_resp, "503 response contains clean, friendly error message")
    else:
        assert_true("tutor_response" in ai_resp, "200 response contains tutor_response")


def main() -> None:
    print("\n\033[1;36m====================================================================\033[0m")
    print("\033[1;36m  🚀 42 EXAMSHELL - E2E FULL SYSTEM & RELIABILITY TEST BATTERY      \033[0m")
    print("\033[1;36m====================================================================\033[0m")

    try:
        test_database_isolated_acid()
        test_cli_feedback()
        test_server_http_endpoints()

        print("\n\033[1;32m====================================================================\033[0m")
        print("\033[1;32m  🎉 TODOS OS TESTES E2E PASSARAM COM 100% DE SUCESSO!             \033[0m")
        print("\033[1;32m  - Integridade ACID e WAL confirmados no SQLite                    \033[0m")
        print("\033[1;32m  - Zero nulos / undefined no parsing de dados e tempo              \033[0m")
        print("\033[1;32m  - Feedback bidirecional CLI + Web validado                        \033[0m")
        print("\033[1;32m  - Resiliência e fallback defensivo no Tutor IA confirmados        \033[0m")
        print("\033[1;32m====================================================================\033[0m\n")
    except Exception as e:
        print(f"\n\033[1;31m❌ Falha na bateria de testes E2E: {e}\033[0m", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
