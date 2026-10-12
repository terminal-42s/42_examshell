"""
Database Access Layer and CLI for 42 Examshell Active Training Platform.

Manages SQLite storage for Rank 02 exercises in .resources/rank02/stats.db,
pattern classifications, attempt history with duration, submitted source code,
error traces, error reason classification, and algorithms for Spaced Repetition.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / ".resources" / "rank02" / "stats.db"

# 55 Rank 02 exercises mapped to exam levels and 13 technical patterns
EXERCISES_SEED_DATA: List[Dict[str, Any]] = [
    # Level 0 (12 exercises)
    {"id": "first_word", "level": 0, "patterns": ["CLI", "Skip Whitespace"]},
    {"id": "fizzbuzz", "level": 0, "patterns": ["Recursao Numerica"]},
    {"id": "ft_putstr", "level": 0, "patterns": ["Navegacao String"]},
    {"id": "ft_strcpy", "level": 0, "patterns": ["Navegacao String"]},
    {"id": "ft_strlen", "level": 0, "patterns": ["Navegacao String"]},
    {"id": "ft_swap", "level": 0, "patterns": ["Swapping"]},
    {"id": "repeat_alpha", "level": 0, "patterns": ["CLI", "Tabela ASCII"]},
    {"id": "rev_print", "level": 0, "patterns": ["CLI", "Swapping"]},
    {"id": "rot_13", "level": 0, "patterns": ["CLI", "Tabela ASCII"]},
    {"id": "rotone", "level": 0, "patterns": ["CLI", "Tabela ASCII"]},
    {"id": "search_and_replace", "level": 0, "patterns": ["CLI", "Navegacao String"]},
    {"id": "ulstr", "level": 0, "patterns": ["CLI", "Tabela ASCII"]},

    # Level 1 (18 exercises)
    {"id": "alpha_mirror", "level": 1, "patterns": ["CLI", "Tabela ASCII"]},
    {"id": "camel_to_snake", "level": 1, "patterns": ["CLI", "Tabela ASCII"]},
    {"id": "do_op", "level": 1, "patterns": ["CLI", "ft_atoi"]},
    {"id": "ft_atoi", "level": 1, "patterns": ["Skip Whitespace", "ft_atoi"]},
    {"id": "ft_strcmp", "level": 1, "patterns": ["Navegacao String"]},
    {"id": "ft_strcspn", "level": 1, "patterns": ["Navegacao String"]},
    {"id": "ft_strdup", "level": 1, "patterns": ["Heap Malloc"]},
    {"id": "ft_strrev", "level": 1, "patterns": ["Swapping"]},
    {"id": "inter", "level": 1, "patterns": ["CLI", "ASCII Direct Lookup"]},
    {"id": "is_power_of_2", "level": 1, "patterns": ["Bitwise"]},
    {"id": "last_word", "level": 1, "patterns": ["CLI", "Skip Whitespace"]},
    {"id": "max", "level": 1, "patterns": ["Navegacao Array"]},
    {"id": "print_bits", "level": 1, "patterns": ["Bitwise"]},
    {"id": "reverse_bits", "level": 1, "patterns": ["Bitwise"]},
    {"id": "snake_to_camel", "level": 1, "patterns": ["CLI", "Tabela ASCII"]},
    {"id": "swap_bits", "level": 1, "patterns": ["Bitwise"]},
    {"id": "union", "level": 1, "patterns": ["CLI", "ASCII Direct Lookup"]},
    {"id": "wdmatch", "level": 1, "patterns": ["CLI", "Matching Ponteiros"]},

    # Level 2 (15 exercises)
    {"id": "add_prime_sum", "level": 2, "patterns": ["CLI", "Recursao Numerica", "Matematica Primos"]},
    {"id": "epur_str", "level": 2, "patterns": ["CLI", "Skip Whitespace"]},
    {"id": "expand_str", "level": 2, "patterns": ["CLI", "Skip Whitespace"]},
    {"id": "ft_atoi_base", "level": 2, "patterns": ["Skip Whitespace", "Tabela ASCII", "ft_atoi"]},
    {"id": "ft_list_size", "level": 2, "patterns": ["LinkedList"]},
    {"id": "ft_range", "level": 2, "patterns": ["Heap Malloc"]},
    {"id": "ft_rrange", "level": 2, "patterns": ["Heap Malloc"]},
    {"id": "hidenp", "level": 2, "patterns": ["CLI", "Matching Ponteiros"]},
    {"id": "lcm", "level": 2, "patterns": ["Matematica MMC"]},
    {"id": "paramsum", "level": 2, "patterns": ["CLI", "Recursao Numerica"]},
    {"id": "pgcd", "level": 2, "patterns": ["CLI", "ft_atoi", "Matematica MDC"]},
    {"id": "print_hex", "level": 2, "patterns": ["CLI", "Recursao Numerica", "ft_atoi"]},
    {"id": "rstr_capitalizer", "level": 2, "patterns": ["CLI", "Skip Whitespace", "Tabela ASCII"]},
    {"id": "str_capitalizer", "level": 2, "patterns": ["CLI", "Skip Whitespace", "Tabela ASCII"]},
    {"id": "tab_mult", "level": 2, "patterns": ["CLI", "Recursao Numerica", "ft_atoi"]},

    # Level 3 (10 exercises)
    {"id": "flood_fill", "level": 3, "patterns": ["Grid DFS Bounds"]},
    {"id": "fprime", "level": 3, "patterns": ["CLI", "Fatoracao Prima"]},
    {"id": "ft_itoa", "level": 3, "patterns": ["Recursao Numerica", "Heap Malloc"]},
    {"id": "ft_list_foreach", "level": 3, "patterns": ["LinkedList"]},
    {"id": "ft_list_remove_if", "level": 3, "patterns": ["LinkedList"]},
    {"id": "ft_split", "level": 3, "patterns": ["Skip Whitespace", "Heap Malloc"]},
    {"id": "rev_wstr", "level": 3, "patterns": ["CLI", "Skip Whitespace"]},
    {"id": "rostring", "level": 3, "patterns": ["CLI", "Skip Whitespace"]},
    {"id": "sort_int_tab", "level": 3, "patterns": ["Swapping"]},
    {"id": "sort_list", "level": 3, "patterns": ["LinkedList", "Swapping"]},
]


def detect_error_reason(success: bool, error_trace: Optional[str]) -> str:
    """Classify the root cause of the error based on tester/compiler logs."""
    if success:
        return "Success"
    if not error_trace:
        return "Unknown / Unspecified"

    lower = error_trace.lower()
    if "segmentation fault" in lower or "sigsegv" in lower or "core dumped" in lower:
        return "Segmentation Fault"
    if "bus error" in lower or "sigbus" in lower:
        return "Bus Error"
    if "timeout" in lower or "infinite loop" in lower:
        return "Memory Leak / Timeout"
    if "norme" in lower or "norminette" in lower:
        return "Norme Error"
    if (
        "error:" in lower
        or "compilation error" in lower
        or "fatal error" in lower
        or "undefined reference" in lower
        or "clang: error" in lower
        or "gcc: error" in lower
    ):
        return "Compilation Error"
    if (
        "diff" in lower
        or "expected output" in lower
        or "your output" in lower
        or "fail" in lower
        or "ko" in lower
    ):
        return "Wrong Output / Mismatch"
    return "Test Failure / KO"


def format_duration(seconds: Any) -> str:
    """Format seconds into readable mm:ss defensively."""
    if seconds is None:
        return "--:--"
    try:
        sec = max(0, int(round(float(seconds))))
        m, s = divmod(sec, 60)
        return f"{m:02d}:{s:02d}"
    except (ValueError, TypeError):
        return "--:--"


@dataclass
class Exercise:
    id: str
    level: int
    patterns: List[str]

    @property
    def patterns_str(self) -> str:
        return ", ".join(self.patterns)


@dataclass
class Attempt:
    id: int
    exercise_id: str
    timestamp: str
    duration_seconds: int
    success: bool
    error_trace: Optional[str]
    submitted_code: Optional[str] = None
    error_reason: Optional[str] = None
    user_notes: Optional[str] = None
    independence_status: Optional[str] = None
    stuck_point: Optional[str] = None


@dataclass
class ExerciseStat:
    id: str
    level: int
    patterns: List[str]
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    success_rate: float
    avg_duration_seconds: float
    last_attempt_at: Optional[str]
    last_error_trace: Optional[str]
    last_error_reason: Optional[str]
    best_time_seconds: Optional[int]
    alone_count: int = 0
    searched_count: int = 0
    autonomy_rate: float = 0.0
    is_mastered: bool = False
    mastery_status: str = "unattempted"  # "unattempted", "training", "mastered"
    mastery_label: str = "Não Iniciado"


class ExamDatabase:
    """SQLite Database manager for Rank 02 exercises and attempt history."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            with conn:
                yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create tables if they don't exist and run non-destructive schema migrations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS exercises (
                    id TEXT PRIMARY KEY,
                    level INTEGER NOT NULL,
                    patterns TEXT NOT NULL
                );
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exercise_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds INTEGER NOT NULL DEFAULT 0,
                    success BOOLEAN NOT NULL CHECK (success IN (0, 1)),
                    error_trace TEXT,
                    submitted_code TEXT DEFAULT '',
                    error_reason TEXT DEFAULT '',
                    user_notes TEXT DEFAULT '',
                    independence_status TEXT DEFAULT '',
                    stuck_point TEXT DEFAULT '',
                    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
                );
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exercise_id TEXT NOT NULL,
                    attempt_id INTEGER,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    message TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
                    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE SET NULL
                );
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_drill_queues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT DEFAULT '',
                    items TEXT NOT NULL
                );
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_strategy_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    message TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Migration check: Ensure new columns exist even on pre-existing databases
            cursor.execute("PRAGMA table_info(attempts);")
            existing_cols = {row["name"] for row in cursor.fetchall()}
            if "submitted_code" not in existing_cols:
                cursor.execute("ALTER TABLE attempts ADD COLUMN submitted_code TEXT DEFAULT '';")
            if "error_reason" not in existing_cols:
                cursor.execute("ALTER TABLE attempts ADD COLUMN error_reason TEXT DEFAULT '';")
            if "user_notes" not in existing_cols:
                cursor.execute("ALTER TABLE attempts ADD COLUMN user_notes TEXT DEFAULT '';")
            if "independence_status" not in existing_cols:
                cursor.execute("ALTER TABLE attempts ADD COLUMN independence_status TEXT DEFAULT '';")
            if "stuck_point" not in existing_cols:
                cursor.execute("ALTER TABLE attempts ADD COLUMN stuck_point TEXT DEFAULT '';")

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_attempts_ex_id ON attempts(exercise_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_attempts_exercise ON attempts(exercise_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_attempts_timestamp ON attempts(timestamp);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_attempts_success ON attempts(success);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_attempts_independence ON attempts(independence_status);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ai_interactions_ex_id ON ai_interactions(exercise_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ai_interactions_attempt_id ON ai_interactions(attempt_id);"
            )

            conn.commit()

        self.seed_exercises()

    def seed_exercises(self) -> None:
        """Ensure all 55 exercises from Rank 02 are populated with patterns."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for ex in EXERCISES_SEED_DATA:
                patterns_val = ", ".join(ex["patterns"])
                cursor.execute(
                    """
                    INSERT INTO exercises (id, level, patterns)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        level = excluded.level,
                        patterns = excluded.patterns;
                    """,
                    (ex["id"], ex["level"], patterns_val),
                )
            conn.commit()

    def record_attempt(
        self,
        exercise_id: str,
        success: bool,
        duration_seconds: int,
        error_trace: Optional[str] = None,
        submitted_code: Optional[str] = None,
        error_reason: Optional[str] = None,
        user_notes: Optional[str] = None,
        independence_status: Optional[str] = None,
        stuck_point: Optional[str] = None,
    ) -> int:
        """Record an attempt for an exercise with code, error reason and reflexive self-assessment."""
        clean_trace = None if success else (error_trace or "").strip()
        if clean_trace == "":
            clean_trace = None

        clean_code = (submitted_code or "").strip()
        if not clean_code:
            clean_code = ""

        # Auto-classify error reason if not explicitly supplied
        if not error_reason:
            error_reason = detect_error_reason(success, clean_trace)

        clean_notes = (user_notes or "").strip()
        clean_indep = (independence_status or "").strip() or "unspecified"
        clean_stuck = (stuck_point or "").strip()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO attempts (
                    exercise_id, success, duration_seconds, error_trace, submitted_code, error_reason,
                    user_notes, independence_status, stuck_point
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    exercise_id,
                    1 if success else 0,
                    max(0, int(duration_seconds)),
                    clean_trace,
                    clean_code,
                    error_reason,
                    clean_notes,
                    clean_indep,
                    clean_stuck,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def update_attempt_feedback(
        self,
        attempt_id: int,
        user_notes: Optional[str] = None,
        independence_status: Optional[str] = None,
        stuck_point: Optional[str] = None,
    ) -> bool:
        """Update self-assessment and reflexive feedback for an existing attempt."""
        updates = []
        params = []
        if user_notes is not None:
            updates.append("user_notes = ?")
            params.append(user_notes.strip())
        if independence_status is not None:
            updates.append("independence_status = ?")
            params.append(independence_status.strip())
        if stuck_point is not None:
            updates.append("stuck_point = ?")
            params.append(stuck_point.strip())

        if not updates:
            return False

        params.append(int(attempt_id))
        query = f"UPDATE attempts SET {', '.join(updates)} WHERE id = ?;"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            conn.commit()
            return cursor.rowcount > 0

    def get_exercise(self, exercise_id: str) -> Optional[Exercise]:
        """Fetch exercise details by id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, level, patterns FROM exercises WHERE id = ?",
                (exercise_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            patterns = [p.strip() for p in row["patterns"].split(",") if p.strip()]
            return Exercise(id=row["id"], level=row["level"], patterns=patterns)

    def get_all_exercises(self) -> List[Exercise]:
        """Fetch all exercises ordered by level then name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, level, patterns FROM exercises ORDER BY level ASC, id ASC"
            )
            rows = cursor.fetchall()
            return [
                Exercise(
                    id=r["id"],
                    level=r["level"],
                    patterns=[p.strip() for p in r["patterns"].split(",") if p.strip()],
                )
                for r in rows
            ]

    def get_exercises_by_level(self, level: int) -> List[Exercise]:
        """Fetch exercises for a given level (0-3)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, level, patterns FROM exercises WHERE level = ? ORDER BY id ASC",
                (level,),
            )
            rows = cursor.fetchall()
            return [
                Exercise(
                    id=r["id"],
                    level=r["level"],
                    patterns=[p.strip() for p in r["patterns"].split(",") if p.strip()],
                )
                for r in rows
            ]

    def get_exercises_by_pattern(self, pattern: str) -> List[Exercise]:
        """Fetch exercises belonging to a specific technical pattern using LIKE."""
        target = pattern.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, level, patterns FROM exercises WHERE patterns LIKE ? ORDER BY level ASC, id ASC",
                (f"%{target}%",),
            )
            rows = cursor.fetchall()
            return [
                Exercise(
                    id=r["id"],
                    level=r["level"],
                    patterns=[p.strip() for p in r["patterns"].split(",") if p.strip()],
                )
                for r in rows
            ]

    def get_all_patterns(self) -> List[str]:
        """Return a sorted unique list of all technical patterns."""
        patterns_set = set()
        for ex in self.get_all_exercises():
            for p in ex.patterns:
                patterns_set.add(p)
        return sorted(patterns_set)

    def get_attempts_for_exercise(self, exercise_id: str) -> List[Attempt]:
        """Return history of attempts for a specific exercise."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, exercise_id, timestamp, duration_seconds, success,
                       COALESCE(error_trace, '') AS error_trace,
                       COALESCE(submitted_code, '') AS submitted_code,
                       COALESCE(error_reason, '') AS error_reason,
                       COALESCE(user_notes, '') AS user_notes,
                       COALESCE(NULLIF(independence_status, ''), 'unspecified') AS independence_status,
                       COALESCE(stuck_point, '') AS stuck_point
                FROM attempts
                WHERE exercise_id = ?
                ORDER BY timestamp DESC, id DESC
                """,
                (exercise_id,),
            )
            rows = cursor.fetchall()
            return [
                Attempt(
                    id=r["id"],
                    exercise_id=r["exercise_id"],
                    timestamp=r["timestamp"],
                    duration_seconds=r["duration_seconds"],
                    success=bool(r["success"]),
                    error_trace=r["error_trace"] if r["error_trace"] else None,
                    submitted_code=r["submitted_code"],
                    error_reason=r["error_reason"],
                    user_notes=r["user_notes"],
                    independence_status=r["independence_status"],
                    stuck_point=r["stuck_point"],
                )
                for r in rows
            ]

    def get_exercise_documentation(self, exercise_id: str, level: int) -> Dict[str, Any]:
        """Fetch and parse subject (sub.txt) and pseudocode (pseudo.md) for the exercise."""
        parent_dir = BASE_DIR.parent
        possible_dirs = [
            parent_dir / f"level{level}" / exercise_id,
            parent_dir / "level0" / exercise_id,
            parent_dir / "level1" / exercise_id,
            parent_dir / "level2" / exercise_id,
            parent_dir / "level3" / exercise_id,
        ]

        raw_subject = ""
        raw_pseudo = ""

        for p in possible_dirs:
            if not p.is_dir():
                continue
            sub_file = p / "sub.txt"
            if not sub_file.is_file():
                for cand in p.glob("sub*.txt"):
                    sub_file = cand
                    break
            if sub_file.is_file() and not raw_subject:
                try:
                    raw_subject = sub_file.read_text(encoding="utf-8", errors="replace").strip()
                except Exception:
                    pass

            pseudo_file = p / "pseudo.md"
            if pseudo_file.is_file() and not raw_pseudo:
                try:
                    raw_pseudo = pseudo_file.read_text(encoding="utf-8", errors="replace").strip()
                except Exception:
                    pass

            if raw_subject and raw_pseudo:
                break

        # Parsing structured fields from 42 subject file
        assignment_name = exercise_id
        expected_files = ""
        allowed_functions = ""
        description_text = raw_subject

        if raw_subject:
            lines = raw_subject.splitlines()
            body_start = 0
            for idx, line in enumerate(lines):
                line_stripped = line.strip()
                if line_stripped.startswith("Assignment name"):
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        assignment_name = parts[1].strip()
                elif line_stripped.startswith("Expected files"):
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        expected_files = parts[1].strip()
                elif line_stripped.startswith("Allowed functions"):
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        allowed_functions = parts[1].strip()
                elif line_stripped.startswith("---") or line_stripped.startswith("==="):
                    body_start = idx + 1
                    break

            if body_start > 0 and body_start < len(lines):
                description_text = "\n".join(lines[body_start:]).strip()

        return {
            "assignment_name": assignment_name,
            "expected_files": expected_files,
            "allowed_functions": allowed_functions,
            "subject_raw": raw_subject,
            "description_text": description_text,
            "pseudocode_raw": raw_pseudo,
        }

    def get_exercise_full_profile(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Fetch exercise metadata, documentation, performance stats, full attempt history, and AI chat."""
        ex = self.get_exercise(exercise_id)
        if not ex:
            return None

        docs = self.get_exercise_documentation(exercise_id, ex.level)
        attempts = self.get_attempts_for_exercise(exercise_id)
        ai_history = self.get_ai_interactions(exercise_id, limit=50)

        total_attempts = len(attempts)
        successful_attempts = sum(1 for a in attempts if a.success)
        failed_attempts = total_attempts - successful_attempts
        success_rate = round((successful_attempts / total_attempts * 100.0), 1) if total_attempts > 0 else 0.0

        durations = [a.duration_seconds for a in attempts]
        avg_dur = round(sum(durations) / total_attempts, 1) if total_attempts > 0 else 0.0
        success_durations = [a.duration_seconds for a in attempts if a.success]
        best_time = min(success_durations) if success_durations else None

        alone_count = sum(1 for a in attempts if a.independence_status == "alone")
        searched_count = sum(1 for a in attempts if a.independence_status == "searched")
        unspecified_count = max(0, total_attempts - (alone_count + searched_count))
        
        evaluated_indep = alone_count + searched_count
        # Percentual estrito de autonomia
        autonomy_rate = round((alone_count / evaluated_indep * 100.0), 1) if evaluated_indep > 0 else 0.0

        last_attempt = attempts[0] if attempts else None
        last_attempt_at = last_attempt.timestamp if last_attempt else None
        last_attempt_success = last_attempt.success if last_attempt else False
        last_error_reason = next((a.error_reason for a in attempts if a.error_reason and a.error_reason != "Success"), "")
        latest_stuck_point = next((a.stuck_point for a in attempts if a.stuck_point), "")
        latest_user_notes = next((a.user_notes for a in attempts if a.user_notes), "")

        # Regra de negócio estrita para "Dominado":
        # 1. Pelo menos 1 aprovação (successful_attempts >= 1)
        # 2. alone_count > searched_count
        # 3. Última tentativa recente aprovada (last_attempt_success == True)
        is_mastered = (successful_attempts >= 1) and (alone_count > searched_count) and last_attempt_success

        if total_attempts == 0:
            status = "unattempted"
            status_label = "Não Iniciado"
        elif is_mastered:
            status = "mastered"
            status_label = "Dominado"
        else:
            status = "training"
            status_label = "Em Treinamento"

        serialized_attempts = [
            {
                "id": a.id,
                "exercise_id": a.exercise_id,
                "timestamp": a.timestamp,
                "duration_seconds": a.duration_seconds,
                "duration_formatted": format_duration(a.duration_seconds),
                "success": a.success,
                "error_reason": a.error_reason or ("Success" if a.success else "Falha"),
                "submitted_code": a.submitted_code or "",
                "error_trace": a.error_trace or "",
                "user_notes": a.user_notes or "",
                "independence_status": a.independence_status or "unspecified",
                "stuck_point": a.stuck_point or "",
                "has_code": bool(a.submitted_code),
                "has_trace": bool(a.error_trace),
            }
            for a in attempts
        ]

        return {
            "exercise": {
                "id": ex.id,
                "level": ex.level,
                "patterns": ex.patterns,
                "docs": docs,
            },
            "stats": {
                "total_attempts": total_attempts,
                "successful_attempts": successful_attempts,
                "failed_attempts": failed_attempts,
                "success_rate": success_rate,
                "avg_duration_seconds": avg_dur,
                "avg_duration_formatted": format_duration(avg_dur),
                "best_time_seconds": best_time,
                "best_time_formatted": format_duration(best_time),
                "last_attempt_at": last_attempt_at or "",
                "alone_count": alone_count,
                "searched_count": searched_count,
                "unspecified_count": unspecified_count,
                "autonomy_rate": autonomy_rate,
                "mastery_status": status,
                "mastery_label": status_label,
                "last_error_reason": last_error_reason,
                "latest_stuck_point": latest_stuck_point,
                "latest_user_notes": latest_user_notes,
            },
            "attempts": serialized_attempts,
            "ai_messages": ai_history,
        }

    def record_ai_interaction(
        self,
        exercise_id: str,
        role: str,
        message: str,
        attempt_id: Optional[int] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> int:
        """Record a chat message between user and AI tutor for an exercise."""
        clean_msg = message.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ai_interactions (
                    exercise_id, attempt_id, role, message, tokens_used, cost_usd
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    exercise_id.strip(),
                    attempt_id,
                    role.strip(),
                    clean_msg,
                    max(0, int(tokens_used)),
                    max(0.0, float(cost_usd)),
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def get_ai_interactions(
        self,
        exercise_id: str,
        attempt_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation history for an exercise, optionally scoped to an attempt."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if attempt_id:
                cursor.execute(
                    """
                    SELECT id, exercise_id, attempt_id, role, message, tokens_used, cost_usd, timestamp
                    FROM ai_interactions
                    WHERE exercise_id = ? AND (attempt_id = ? OR attempt_id IS NULL)
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (exercise_id.strip(), attempt_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, exercise_id, attempt_id, role, message, tokens_used, cost_usd, timestamp
                    FROM ai_interactions
                    WHERE exercise_id = ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (exercise_id.strip(), limit),
                )
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "exercise_id": r["exercise_id"],
                    "attempt_id": r["attempt_id"],
                    "role": r["role"],
                    "message": r["message"],
                    "tokens_used": r["tokens_used"],
                    "cost_usd": r["cost_usd"],
                    "timestamp": r["timestamp"],
                }
                for r in rows
            ]

    def clear_ai_interactions(self, exercise_id: str) -> None:
        """Clear conversation history for a given exercise."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ai_interactions WHERE exercise_id = ?", (exercise_id.strip(),))
            conn.commit()

    def get_attempt_by_id(self, attempt_id: int) -> Optional[Attempt]:
        """Fetch a single attempt by primary key id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, exercise_id, timestamp, duration_seconds, success,
                       COALESCE(error_trace, '') AS error_trace,
                       COALESCE(submitted_code, '') AS submitted_code,
                       COALESCE(error_reason, '') AS error_reason,
                       COALESCE(user_notes, '') AS user_notes,
                       COALESCE(NULLIF(independence_status, ''), 'unspecified') AS independence_status,
                       COALESCE(stuck_point, '') AS stuck_point
                FROM attempts
                WHERE id = ?
                """,
                (attempt_id,),
            )
            r = cursor.fetchone()
            if not r:
                return None
            return Attempt(
                id=r["id"],
                exercise_id=r["exercise_id"],
                timestamp=r["timestamp"],
                duration_seconds=r["duration_seconds"],
                success=bool(r["success"]),
                error_trace=r["error_trace"] if r["error_trace"] else None,
                submitted_code=r["submitted_code"],
                error_reason=r["error_reason"],
                user_notes=r["user_notes"],
                independence_status=r["independence_status"],
                stuck_point=r["stuck_point"],
            )

    def get_all_attempts(self, limit: int = 200) -> List[Attempt]:
        """Fetch latest attempts across all exercises."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, exercise_id, timestamp, duration_seconds, success,
                       COALESCE(error_trace, '') AS error_trace,
                       COALESCE(submitted_code, '') AS submitted_code,
                       COALESCE(error_reason, '') AS error_reason,
                       COALESCE(user_notes, '') AS user_notes,
                       COALESCE(NULLIF(independence_status, ''), 'unspecified') AS independence_status,
                       COALESCE(stuck_point, '') AS stuck_point
                FROM attempts
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                Attempt(
                    id=r["id"],
                    exercise_id=r["exercise_id"],
                    timestamp=r["timestamp"],
                    duration_seconds=r["duration_seconds"],
                    success=bool(r["success"]),
                    error_trace=r["error_trace"] if r["error_trace"] else None,
                    submitted_code=r["submitted_code"],
                    error_reason=r["error_reason"],
                    user_notes=r["user_notes"],
                    independence_status=r["independence_status"],
                    stuck_point=r["stuck_point"],
                )
                for r in rows
            ]

    def get_latest_attempt_id(self) -> int:
        """Return the highest attempt ID recorded so far (for auto-polling)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) AS max_id FROM attempts")
            row = cursor.fetchone()
            return (row["max_id"] or 0) if row else 0

    def get_timeline_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return daily aggregated activity and accuracy metrics."""
        query = """
            SELECT 
                strftime('%Y-%m-%d', timestamp) AS date,
                COUNT(id) AS total_attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS successful_attempts,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failed_attempts,
                AVG(duration_seconds) AS avg_duration_seconds,
                GROUP_CONCAT(DISTINCT exercise_id) AS exercises_done
            FROM attempts
            WHERE (? IS NULL OR strftime('%Y-%m-%d', timestamp) >= ?)
              AND (? IS NULL OR strftime('%Y-%m-%d', timestamp) <= ?)
            GROUP BY date
            ORDER BY date ASC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (start_date, start_date, end_date, end_date))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                tot = r["total_attempts"] or 0
                succ = r["successful_attempts"] or 0
                fail = r["failed_attempts"] or 0
                rate = (succ / tot * 100.0) if tot > 0 else 0.0
                avg_dur = float(r["avg_duration_seconds"]) if r["avg_duration_seconds"] is not None else 0.0
                ex_list = [e.strip() for e in (r["exercises_done"] or "").split(",") if e.strip()]
                result.append(
                    {
                        "date": r["date"],
                        "total_attempts": tot,
                        "successful_attempts": succ,
                        "failed_attempts": fail,
                        "success_rate": round(rate, 1),
                        "avg_duration_seconds": round(avg_dur, 1),
                        "avg_duration_formatted": format_duration(avg_dur),
                        "exercises_done": sorted(ex_list),
                    }
                )
            return result

    def get_day_details(self, date_str: str) -> Dict[str, Any]:
        """Return complete details of all attempts and patterns practiced on a specific date."""
        target_date = date_str.strip()
        query = """
            SELECT 
                a.id,
                a.exercise_id,
                e.level,
                e.patterns,
                a.timestamp,
                strftime('%H:%M', a.timestamp) AS time_str,
                COALESCE(a.duration_seconds, 0) AS duration_seconds,
                a.success,
                COALESCE(a.error_reason, '') AS error_reason,
                COALESCE(a.user_notes, '') AS user_notes,
                COALESCE(NULLIF(a.independence_status, ''), 'unspecified') AS independence_status,
                COALESCE(a.stuck_point, '') AS stuck_point,
                (a.error_trace IS NOT NULL AND a.error_trace != '') AS has_trace,
                (a.submitted_code IS NOT NULL AND a.submitted_code != '') AS has_code
            FROM attempts a
            LEFT JOIN exercises e ON a.exercise_id = e.id
            WHERE strftime('%Y-%m-%d', a.timestamp) = ?
            ORDER BY a.timestamp ASC, a.id ASC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (target_date,))
            rows = cursor.fetchall()

            attempts_list = []
            pattern_counts: Dict[str, Dict[str, int]] = {}

            for r in rows:
                pats = [p.strip() for p in (r["patterns"] or "").split(",") if p.strip()]
                attempts_list.append(
                    {
                        "id": r["id"],
                        "exercise_id": r["exercise_id"],
                        "level": r["level"],
                        "patterns": pats,
                        "timestamp": r["timestamp"],
                        "time": r["time_str"],
                        "duration_seconds": r["duration_seconds"],
                        "duration_formatted": format_duration(r["duration_seconds"]),
                        "success": bool(r["success"]),
                        "error_reason": r["error_reason"] or ("Success" if r["success"] else "Failure"),
                        "user_notes": r["user_notes"] or "",
                        "independence_status": r["independence_status"] or "unspecified",
                        "stuck_point": r["stuck_point"] or "",
                        "has_trace": bool(r["has_trace"]),
                        "has_code": bool(r["has_code"]),
                    }
                )

                for p in pats:
                    if p not in pattern_counts:
                        pattern_counts[p] = {"total": 0, "success": 0}
                    pattern_counts[p]["total"] += 1
                    if r["success"]:
                        pattern_counts[p]["success"] += 1

            total = len(attempts_list)
            succ = sum(1 for a in attempts_list if a["success"])
            fail = total - succ
            rate = (succ / total * 100.0) if total > 0 else 0.0

            patterns_breakdown = []
            for p, d in sorted(pattern_counts.items(), key=lambda x: x[1]["total"], reverse=True):
                p_rate = (d["success"] / d["total"] * 100.0) if d["total"] > 0 else 0.0
                patterns_breakdown.append(
                    {
                        "pattern": p,
                        "count": d["total"],
                        "successes": d["success"],
                        "rate": round(p_rate, 1),
                    }
                )

            return {
                "date": target_date,
                "total_attempts": total,
                "successful_attempts": succ,
                "failed_attempts": fail,
                "success_rate": round(rate, 1),
                "attempts": attempts_list,
                "patterns_breakdown": patterns_breakdown,
            }

    def get_filtered_attempts(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        exercise_id: Optional[str] = None,
        pattern: Optional[str] = None,
        limit: int = 150,
    ) -> List[Dict[str, Any]]:
        """Filter attempts with multiple criteria (date range, status, pattern, exercise)."""
        conditions = []
        params = []

        if start_date:
            conditions.append("strftime('%Y-%m-%d', a.timestamp) >= ?")
            params.append(start_date.strip())
        if end_date:
            conditions.append("strftime('%Y-%m-%d', a.timestamp) <= ?")
            params.append(end_date.strip())
        if status in ("success", "1", "passed"):
            conditions.append("a.success = 1")
        elif status in ("failed", "0", "failure"):
            conditions.append("a.success = 0")
        if exercise_id:
            conditions.append("a.exercise_id = ?")
            params.append(exercise_id.strip())
        if pattern:
            conditions.append("e.patterns LIKE ?")
            params.append(f"%{pattern.strip()}%")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT 
                a.id,
                a.exercise_id,
                e.level,
                e.patterns,
                a.timestamp,
                strftime('%Y-%m-%d', a.timestamp) AS date_str,
                strftime('%H:%M', a.timestamp) AS time_str,
                COALESCE(a.duration_seconds, 0) AS duration_seconds,
                a.success,
                COALESCE(a.error_reason, '') AS error_reason,
                COALESCE(a.user_notes, '') AS user_notes,
                COALESCE(NULLIF(a.independence_status, ''), 'unspecified') AS independence_status,
                COALESCE(a.stuck_point, '') AS stuck_point,
                (a.error_trace IS NOT NULL AND a.error_trace != '') AS has_trace,
                (a.submitted_code IS NOT NULL AND a.submitted_code != '') AS has_code
            FROM attempts a
            LEFT JOIN exercises e ON a.exercise_id = e.id
            {where_clause}
            ORDER BY a.timestamp DESC, a.id DESC
            LIMIT ?
        """
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "exercise_id": r["exercise_id"],
                    "level": r["level"],
                    "patterns": [p.strip() for p in (r["patterns"] or "").split(",") if p.strip()],
                    "timestamp": r["timestamp"],
                    "date": r["date_str"],
                    "time": r["time_str"],
                    "duration_seconds": r["duration_seconds"],
                    "duration_formatted": format_duration(r["duration_seconds"]),
                    "success": bool(r["success"]),
                    "error_reason": r["error_reason"],
                    "user_notes": r["user_notes"] or "",
                    "independence_status": r["independence_status"] or "unspecified",
                    "stuck_point": r["stuck_point"] or "",
                    "has_trace": bool(r["has_trace"]),
                    "has_code": bool(r["has_code"]),
                }
                for r in rows
            ]

    def get_exercise_stats(self) -> List[ExerciseStat]:
        """Compile comprehensive statistics for every exercise with strict mastery and autonomy evaluation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    e.id,
                    e.level,
                    e.patterns,
                    COALESCE(COUNT(a.id), 0) AS total_attempts,
                    COALESCE(SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END), 0) AS successful_attempts,
                    COALESCE(SUM(CASE WHEN a.success = 0 THEN 1 ELSE 0 END), 0) AS failed_attempts,
                    COALESCE(SUM(CASE WHEN a.independence_status = 'alone' THEN 1 ELSE 0 END), 0) AS alone_count,
                    COALESCE(SUM(CASE WHEN a.independence_status = 'searched' THEN 1 ELSE 0 END), 0) AS searched_count,
                    COALESCE(AVG(a.duration_seconds), 0) AS avg_duration_seconds,
                    MAX(a.timestamp) AS last_attempt_at,
                    MIN(CASE WHEN a.success = 1 THEN a.duration_seconds ELSE NULL END) AS best_time_seconds,
                    (
                        SELECT a_last.success 
                        FROM attempts a_last 
                        WHERE a_last.exercise_id = e.id 
                        ORDER BY a_last.timestamp DESC, a_last.id DESC 
                        LIMIT 1
                    ) AS last_success,
                    COALESCE((
                        SELECT a2.error_trace 
                        FROM attempts a2 
                        WHERE a2.exercise_id = e.id AND a2.error_trace IS NOT NULL 
                        ORDER BY a2.timestamp DESC, a2.id DESC 
                        LIMIT 1
                    ), '') AS last_error_trace,
                    COALESCE((
                        SELECT a3.error_reason 
                        FROM attempts a3 
                        WHERE a3.exercise_id = e.id AND a3.error_reason IS NOT NULL AND a3.error_reason != 'Success'
                        ORDER BY a3.timestamp DESC, a3.id DESC 
                        LIMIT 1
                    ), '') AS last_error_reason
                FROM exercises e
                LEFT JOIN attempts a ON e.id = a.exercise_id
                GROUP BY e.id, e.level, e.patterns
                ORDER BY e.level ASC, e.id ASC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            stats: List[ExerciseStat] = []
            for r in rows:
                tot = r["total_attempts"] or 0
                succ = r["successful_attempts"] or 0
                fail = r["failed_attempts"] or 0
                alone = r["alone_count"] or 0
                searched = r["searched_count"] or 0
                last_succ = r["last_success"]

                rate = (succ / tot * 100.0) if tot > 0 else 0.0
                avg_dur = float(r["avg_duration_seconds"]) if r["avg_duration_seconds"] is not None else 0.0
                patterns = [p.strip() for p in r["patterns"].split(",") if p.strip()]

                eval_count = alone + searched
                autonomy = round((alone / eval_count * 100.0), 1) if eval_count > 0 else 0.0

                # Regra estrita:
                # 1. Pelo menos 1 aprovação (succ >= 1)
                # 2. alone_count > searched_count
                # 3. Última tentativa recente aprovada (last_succ == 1)
                is_mastered = (succ >= 1) and (alone > searched) and (last_succ == 1)

                if tot == 0:
                    m_status = "unattempted"
                    m_label = "Não Iniciado"
                elif is_mastered:
                    m_status = "mastered"
                    m_label = "Dominado"
                else:
                    m_status = "training"
                    m_label = "Em Treinamento"

                stats.append(
                    ExerciseStat(
                        id=r["id"],
                        level=r["level"],
                        patterns=patterns,
                        total_attempts=tot,
                        successful_attempts=succ,
                        failed_attempts=fail,
                        success_rate=rate,
                        avg_duration_seconds=avg_dur,
                        last_attempt_at=r["last_attempt_at"],
                        last_error_trace=r["last_error_trace"],
                        last_error_reason=r["last_error_reason"],
                        best_time_seconds=r["best_time_seconds"],
                        alone_count=alone,
                        searched_count=searched,
                        autonomy_rate=autonomy,
                        is_mastered=is_mastered,
                        mastery_status=m_status,
                        mastery_label=m_label,
                    )
                )
            return stats

    def get_review_queue(self) -> List[ExerciseStat]:
        """Prioritized spaced repetition / weakness queue."""
        stats = self.get_exercise_stats()

        def review_sort_key(stat: ExerciseStat) -> Tuple[int, int, float, int, str]:
            is_unattempted = 0 if stat.total_attempts == 0 else 1
            is_mastered_val = 1 if stat.is_mastered else 0
            success_rate = stat.success_rate
            failed_attempts = -stat.failed_attempts
            last_timestamp = stat.last_attempt_at or ""
            return (is_unattempted, is_mastered_val, success_rate, failed_attempts, last_timestamp)

        stats.sort(key=review_sort_key)
        return stats

    def get_overall_statistics(self) -> Dict[str, Any]:
        """Return high-level summary metrics with strict mastery and autonomy."""
        all_stats = self.get_exercise_stats()
        total_exercises = len(all_stats)

        mastered_list = [s for s in all_stats if s.is_mastered]
        training_list = [s for s in all_stats if not s.is_mastered and s.total_attempts > 0]
        unattempted_list = [s for s in all_stats if s.total_attempts == 0]

        mastered_count = len(mastered_list)
        training_count = len(training_list)
        unattempted_count = len(unattempted_list)
        pending_count = total_exercises - mastered_count
        training_count = sum(1 for s in all_stats if s.mastery_status == "training")
        unattempted_count = sum(1 for s in all_stats if s.mastery_status == "unattempted")

        pattern_aggregates: Dict[str, Dict[str, Any]] = {}
        for s in all_stats:
            for p in s.patterns:
                if p not in pattern_aggregates:
                    pattern_aggregates[p] = {
                        "total_exercises": 0,
                        "mastered": 0,
                        "training": 0,
                        "unattempted": 0,
                        "attempts": 0,
                        "successes": 0,
                        "failures": 0,
                        "alone_count": 0,
                        "searched_count": 0,
                        "total_duration": 0,
                    }
                pattern_aggregates[p]["total_exercises"] += 1
                if s.is_mastered:
                    pattern_aggregates[p]["mastered"] += 1
                elif s.total_attempts > 0:
                    pattern_aggregates[p]["training"] += 1
                else:
                    pattern_aggregates[p]["unattempted"] += 1
                pattern_aggregates[p]["attempts"] += s.total_attempts
                pattern_aggregates[p]["successes"] += s.successful_attempts
                pattern_aggregates[p]["failures"] += s.failed_attempts
                pattern_aggregates[p]["alone_count"] += s.alone_count
                pattern_aggregates[p]["searched_count"] += s.searched_count
                pattern_aggregates[p]["total_duration"] += int(s.avg_duration_seconds * s.total_attempts)

        pattern_summary: List[Dict[str, Any]] = []
        for pat, data in sorted(pattern_aggregates.items()):
            tot_att = data["attempts"]
            rate = (data["successes"] / tot_att * 100.0) if tot_att > 0 else 0.0
            avg_dur = (data["total_duration"] / tot_att) if tot_att > 0 else 0.0
            eval_pat = data["alone_count"] + data["searched_count"]
            pat_autonomy = round((data["alone_count"] / eval_pat * 100.0), 1) if eval_pat > 0 else 0.0
            pattern_summary.append(
                {
                    "pattern": pat,
                    "total_exercises": data["total_exercises"],
                    "mastered_exercises": data["mastered"],
                    "training_exercises": data["training"],
                    "unattempted_exercises": data["unattempted"],
                    "attempts": tot_att,
                    "successes": data["successes"],
                    "failures": data["failures"],
                    "alone_count": data["alone_count"],
                    "searched_count": data["searched_count"],
                    "autonomy_rate": pat_autonomy,
                    "accuracy_rate": round(rate, 1),
                    "avg_duration_seconds": avg_dur,
                    "avg_duration_formatted": format_duration(avg_dur),
                }
            )

        # Most vulnerable pattern (highest failure rate or lowest autonomy among attempted)
        attempted_patterns = [p for p in pattern_summary if p["attempts"] > 0]
        most_vulnerable_pattern = None
        if attempted_patterns:
            most_vulnerable_pattern = min(attempted_patterns, key=lambda x: (x["autonomy_rate"], x["accuracy_rate"]))

        # Error reasons summary
        error_reasons: Dict[str, int] = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT error_reason, COUNT(*) as count 
                FROM attempts 
                WHERE success = 0 AND error_reason != '' AND error_reason != 'Success'
                GROUP BY error_reason 
                ORDER BY count DESC
                """
            )
            for row in cursor.fetchall():
                error_reasons[row["error_reason"]] = row["count"]

        # Global totals
        total_attempts = sum(s.total_attempts for s in all_stats)
        total_successes = sum(s.successful_attempts for s in all_stats)
        global_accuracy = (total_successes / total_attempts * 100.0) if total_attempts > 0 else 0.0
        total_duration = sum(s.avg_duration_seconds * s.total_attempts for s in all_stats)
        global_avg_duration = (total_duration / total_attempts) if total_attempts > 0 else 0.0

        review_queue = self.get_review_queue()
        top_problematic = review_queue[:5]

        return {
            "total_exercises": total_exercises,
            "mastered_count": mastered_count,
            "pending_count": pending_count,
            "training_count": training_count,
            "unattempted_count": unattempted_count,
            "total_attempts": total_attempts,
            "total_successes": total_successes,
            "global_accuracy_rate": global_accuracy,
            "global_avg_duration_seconds": global_avg_duration,
            "global_avg_duration_formatted": format_duration(global_avg_duration),
            "completion_percentage": (mastered_count / total_exercises * 100.0) if total_exercises else 0.0,
            "most_vulnerable_pattern": most_vulnerable_pattern,
            "error_reasons_summary": error_reasons,
            "pattern_summary": pattern_summary,
            "top_problematic": top_problematic,
            "all_exercises_stats": all_stats,
        }

    def get_deep_analytics_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        level: Optional[int] = None,
        pattern: Optional[str] = None,
        exercise_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive multi-dimensional analytical reports:
        1. autonomy_report (alone vs searched, success rates, top stuck points)
        2. level_report (by Level 0..3: stats, mastery, reasons, stuck points)
        3. exercise_report (each of 55 exercises: alone, searched, min/avg/max duration, last faults)
        4. daily_report (by date: attempts, study time, success rate, autonomy rate, exercises done)
        """
        # Dynamic filter conditions
        conditions = []
        params = []
        if start_date:
            conditions.append("strftime('%Y-%m-%d', a.timestamp) >= ?")
            params.append(start_date.strip())
        if end_date:
            conditions.append("strftime('%Y-%m-%d', a.timestamp) <= ?")
            params.append(end_date.strip())
        if level is not None:
            conditions.append("e.level = ?")
            params.append(int(level))
        if pattern:
            conditions.append("e.patterns LIKE ?")
            params.append(f"%{pattern.strip()}%")
        if exercise_id:
            conditions.append("a.exercise_id = ?")
            params.append(exercise_id.strip())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # ------------------------------------------------------------------
            # 1. Autonomy & Blockages Report
            # ------------------------------------------------------------------
            query_autonomy = f"""
                SELECT
                    COUNT(a.id) AS total_attempts,
                    SUM(CASE WHEN a.independence_status = 'alone' THEN 1 ELSE 0 END) AS total_alone,
                    SUM(CASE WHEN a.independence_status = 'searched' THEN 1 ELSE 0 END) AS total_searched,
                    SUM(CASE WHEN a.independence_status = 'alone' AND a.success = 1 THEN 1 ELSE 0 END) AS success_alone,
                    SUM(CASE WHEN a.independence_status = 'searched' AND a.success = 1 THEN 1 ELSE 0 END) AS success_searched,
                    SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END) AS total_success
                FROM attempts a
                LEFT JOIN exercises e ON a.exercise_id = e.id
                {where_clause}
            """
            cursor.execute(query_autonomy, tuple(params))
            row_auto = cursor.fetchone()

            tot_att = row_auto["total_attempts"] or 0
            alone_att = row_auto["total_alone"] or 0
            search_att = row_auto["total_searched"] or 0
            succ_alone = row_auto["success_alone"] or 0
            succ_search = row_auto["success_searched"] or 0

            # Autonomy percentage
            specified_indep = alone_att + search_att
            autonomy_pct = round((alone_att / specified_indep * 100.0), 1) if specified_indep > 0 else (
                round((alone_att / tot_att * 100.0), 1) if tot_att > 0 else 0.0
            )
            success_rate_alone = round((succ_alone / alone_att * 100.0), 1) if alone_att > 0 else 0.0
            success_rate_searched = round((succ_search / search_att * 100.0), 1) if search_att > 0 else 0.0

            # Top 5 Stuck Points
            query_stuck = f"""
                SELECT stuck_point, COUNT(*) AS count
                FROM attempts a
                LEFT JOIN exercises e ON a.exercise_id = e.id
                {where_clause}
                {"AND" if where_clause else "WHERE"} (a.stuck_point IS NOT NULL AND a.stuck_point != '')
                GROUP BY a.stuck_point
                ORDER BY count DESC
                LIMIT 5
            """
            cursor.execute(query_stuck, tuple(params))
            top_stuck = [{"stuck_point": r["stuck_point"], "count": r["count"]} for r in cursor.fetchall()]

            searched_pct = round((search_att / specified_indep * 100.0), 1) if specified_indep > 0 else 0.0

            autonomy_report = {
                "total_attempts": tot_att,
                "total_submissions": tot_att,
                "total_evaluated": specified_indep,
                "total_alone": alone_att,
                "alone_count": alone_att,
                "total_searched": search_att,
                "searched_count": search_att,
                "unspecified_count": max(0, tot_att - (alone_att + search_att)),
                "autonomy_percentage": autonomy_pct,
                "alone_percentage": autonomy_pct,
                "searched_percentage": searched_pct,
                "success_rate_alone": success_rate_alone,
                "success_rate_searched": success_rate_searched,
                "top_stuck_points": top_stuck,
            }

            # ------------------------------------------------------------------
            # 2. Level Report (Levels 0, 1, 2, 3)
            # ------------------------------------------------------------------
            level_report = []
            levels_to_report = [int(level)] if level is not None else list(range(4))
            for lvl in levels_to_report:
                lvl_conds = []
                lvl_params = []
                for cond, prm in zip(conditions, params):
                    if cond != "e.level = ?":
                        lvl_conds.append(cond)
                        lvl_params.append(prm)
                lvl_conds.append("e.level = ?")
                lvl_params.append(lvl)
                lvl_where = f"WHERE {' AND '.join(lvl_conds)}"

                query_lvl = f"""
                    SELECT
                        COUNT(a.id) AS total_attempts,
                        SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END) AS success_attempts,
                        SUM(CASE WHEN a.independence_status = 'alone' THEN 1 ELSE 0 END) AS alone_attempts,
                        COUNT(DISTINCT CASE WHEN a.success = 1 AND a.independence_status = 'alone' THEN a.exercise_id ELSE NULL END) AS mastered_alone_unique,
                        COUNT(DISTINCT CASE WHEN a.success = 1 THEN a.exercise_id ELSE NULL END) AS passed_unique,
                        AVG(a.duration_seconds) AS avg_duration_seconds
                    FROM attempts a
                    LEFT JOIN exercises e ON a.exercise_id = e.id
                    {lvl_where}
                """
                cursor.execute(query_lvl, tuple(lvl_params))
                r_lvl = cursor.fetchone()

                # Total exercises in level
                cursor.execute("SELECT COUNT(*) AS total FROM exercises WHERE level = ?", (lvl,))
                total_in_level = cursor.fetchone()["total"] or 0

                l_tot = r_lvl["total_attempts"] or 0
                l_succ = r_lvl["success_attempts"] or 0
                l_alone = r_lvl["alone_attempts"] or 0
                l_rate = round((l_succ / l_tot * 100.0), 1) if l_tot > 0 else 0.0
                l_dur = float(r_lvl["avg_duration_seconds"]) if r_lvl["avg_duration_seconds"] is not None else 0.0
                l_alone_rate = round((l_alone / l_tot * 100.0), 1) if l_tot > 0 else 0.0

                # Top error reasons in this level
                query_lvl_errors = f"""
                    SELECT a.error_reason, COUNT(*) as count
                    FROM attempts a
                    LEFT JOIN exercises e ON a.exercise_id = e.id
                    {lvl_where} AND a.success = 0 AND (a.error_reason != '' AND a.error_reason != 'Success')
                    GROUP BY a.error_reason
                    ORDER BY count DESC
                    LIMIT 3
                """
                cursor.execute(query_lvl_errors, tuple(lvl_params))
                top_errors_lvl = [f"{r['error_reason']} ({r['count']})" for r in cursor.fetchall()]

                # Top stuck points in this level
                query_lvl_stuck = f"""
                    SELECT a.stuck_point, COUNT(*) as count
                    FROM attempts a
                    LEFT JOIN exercises e ON a.exercise_id = e.id
                    {lvl_where} AND (a.stuck_point != '')
                    GROUP BY a.stuck_point
                    ORDER BY count DESC
                    LIMIT 3
                """
                cursor.execute(query_lvl_stuck, tuple(lvl_params))
                top_stuck_lvl = [f"{r['stuck_point']} ({r['count']})" for r in cursor.fetchall()]

                level_report.append(
                    {
                        "level": lvl,
                        "total_exercises": total_in_level,
                        "mastered_alone_unique": r_lvl["mastered_alone_unique"] or 0,
                        "passed_unique": r_lvl["passed_unique"] or 0,
                        "total_attempts": l_tot,
                        "success_rate": l_rate,
                        "autonomy_rate": l_alone_rate,
                        "avg_duration_seconds": round(l_dur, 1),
                        "avg_duration_formatted": format_duration(l_dur),
                        "top_error_reasons": top_errors_lvl,
                        "top_stuck_points": top_stuck_lvl,
                    }
                )

            # ------------------------------------------------------------------
            # 3. Exercise Report (Granular for each exercise)
            # ------------------------------------------------------------------
            query_exercises = f"""
                SELECT
                    e.id AS exercise_id,
                    e.level,
                    e.patterns,
                    COUNT(a.id) AS total_attempts,
                    SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END) AS success_attempts,
                    SUM(CASE WHEN a.success = 0 THEN 1 ELSE 0 END) AS failed_attempts,
                    SUM(CASE WHEN a.independence_status = 'alone' THEN 1 ELSE 0 END) AS alone_attempts,
                    SUM(CASE WHEN a.independence_status = 'searched' THEN 1 ELSE 0 END) AS searched_attempts,
                    AVG(a.duration_seconds) AS avg_duration_seconds,
                    MIN(CASE WHEN a.success = 1 THEN a.duration_seconds ELSE NULL END) AS best_time_seconds,
                    MAX(a.duration_seconds) AS worst_time_seconds
                FROM exercises e
                LEFT JOIN attempts a ON e.id = a.exercise_id
                GROUP BY e.id, e.level, e.patterns
                ORDER BY e.level ASC, e.id ASC
            """
            cursor.execute(query_exercises)
            raw_ex_rows = cursor.fetchall()
            exercise_report = []

            for r in raw_ex_rows:
                e_id = r["exercise_id"]
                e_tot = r["total_attempts"] or 0
                e_succ = r["success_attempts"] or 0
                e_fail = r["failed_attempts"] or 0
                e_rate = round((e_succ / e_tot * 100.0), 1) if e_tot > 0 else 0.0
                e_dur = float(r["avg_duration_seconds"]) if r["avg_duration_seconds"] is not None else 0.0
                e_best = r["best_time_seconds"]
                e_worst = r["worst_time_seconds"]

                # Fetch last note, reason and stuck point
                cursor.execute(
                    """
                    SELECT success, error_reason, stuck_point, user_notes, timestamp
                    FROM attempts
                    WHERE exercise_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (e_id,),
                )
                last_r = cursor.fetchone()
                last_success = bool(last_r["success"]) if last_r else False
                last_reason = last_r["error_reason"] if last_r else ""
                last_stuck = last_r["stuck_point"] if last_r else ""
                last_note = last_r["user_notes"] if last_r else ""

                alone_cnt = r["alone_attempts"] or 0
                search_cnt = r["searched_attempts"] or 0
                eval_indep = alone_cnt + search_cnt
                autonomy_rate = round((alone_cnt / eval_indep * 100.0), 1) if eval_indep > 0 else 0.0

                is_mastered = (e_succ >= 1) and (alone_cnt > search_cnt) and last_success
                if e_tot == 0:
                    mastery_status = "unattempted"
                    mastery_label = "Não Iniciado"
                elif is_mastered:
                    mastery_status = "mastered"
                    mastery_label = "Dominado"
                else:
                    mastery_status = "training"
                    mastery_label = "Em Treinamento"

                exercise_report.append(
                    {
                        "id": e_id,
                        "level": r["level"],
                        "patterns": [p.strip() for p in (r["patterns"] or "").split(",") if p.strip()],
                        "total_attempts": e_tot,
                        "success_attempts": e_succ,
                        "failed_attempts": e_fail,
                        "success_rate": e_rate,
                        "alone_attempts": alone_cnt,
                        "searched_attempts": search_cnt,
                        "autonomy_rate": autonomy_rate,
                        "is_mastered": is_mastered,
                        "mastery_status": mastery_status,
                        "mastery_label": mastery_label,
                        "avg_duration_seconds": round(e_dur, 1),
                        "avg_duration_formatted": format_duration(e_dur),
                        "best_time_seconds": e_best,
                        "best_time_formatted": format_duration(e_best) if e_best is not None else "--:--",
                        "worst_time_seconds": e_worst,
                        "worst_time_formatted": format_duration(e_worst) if e_worst is not None else "--:--",
                        "last_error_reason": last_reason,
                        "last_stuck_point": last_stuck,
                        "last_user_notes": last_note,
                    }
                )

            # ------------------------------------------------------------------
            # 4. Daily Report (Aggregated by Date)
            # ------------------------------------------------------------------
            query_daily = f"""
                SELECT
                    strftime('%Y-%m-%d', a.timestamp) AS date,
                    COUNT(a.id) AS total_attempts,
                    SUM(CASE WHEN a.success = 1 THEN 1 ELSE 0 END) AS success_attempts,
                    SUM(CASE WHEN a.success = 0 THEN 1 ELSE 0 END) AS fail_attempts,
                    SUM(CASE WHEN a.independence_status = 'alone' THEN 1 ELSE 0 END) AS alone_attempts,
                    SUM(a.duration_seconds) AS total_duration_seconds,
                    AVG(a.duration_seconds) AS avg_duration_seconds,
                    GROUP_CONCAT(DISTINCT a.exercise_id) AS distinct_exercises
                FROM attempts a
                LEFT JOIN exercises e ON a.exercise_id = e.id
                {where_clause}
                GROUP BY date
                ORDER BY date DESC
            """
            cursor.execute(query_daily, tuple(params))
            daily_rows = cursor.fetchall()
            daily_report = []

            for r in daily_rows:
                d_tot = r["total_attempts"] or 0
                d_succ = r["success_attempts"] or 0
                d_fail = r["fail_attempts"] or 0
                d_alone = r["alone_attempts"] or 0
                d_rate = round((d_succ / d_tot * 100.0), 1) if d_tot > 0 else 0.0
                d_alone_rate = round((d_alone / d_tot * 100.0), 1) if d_tot > 0 else 0.0
                d_time_tot = r["total_duration_seconds"] or 0
                d_time_avg = float(r["avg_duration_seconds"]) if r["avg_duration_seconds"] is not None else 0.0

                daily_report.append(
                    {
                        "date": r["date"],
                        "total_attempts": d_tot,
                        "success_attempts": d_succ,
                        "failed_attempts": d_fail,
                        "success_rate": d_rate,
                        "autonomy_rate": d_alone_rate,
                        "total_duration_seconds": d_time_tot,
                        "total_duration_formatted": format_duration(d_time_tot),
                        "avg_duration_seconds": round(d_time_avg, 1),
                        "avg_duration_formatted": format_duration(d_time_avg),
                        "distinct_exercises": sorted([ex.strip() for ex in (r["distinct_exercises"] or "").split(",") if ex.strip()]),
                    }
                )

            return {
                "autonomy_report": autonomy_report,
                "level_report": level_report,
                "exercise_report": exercise_report,
                "daily_report": daily_report,
            }

    # ==========================================================================
    # Custom Drill Queue Methods
    # ==========================================================================

    def save_custom_queue(
        self,
        name: str,
        items: Optional[List[str]] = None,
        description: str = "",
        exercises: Optional[List[str]] = None,
    ) -> int:
        """Save a custom sequence of exercises in the database."""
        if not name.strip():
            name = f"Treino Customizado {time.strftime('%Y-%m-%d %H:%M')}"
        raw_list = items if items is not None else (exercises or [])
        valid_items = [str(x).strip() for x in raw_list if str(x).strip()]
        items_json = json.dumps(valid_items)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO custom_drill_queues (name, description, items)
                VALUES (?, ?, ?)
                """,
                (name.strip(), description.strip(), items_json),
            )
            conn.commit()
            return cursor.lastrowid

    def get_custom_queues(self) -> List[Dict[str, Any]]:
        """List all saved custom drill queues."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, created_at, description, items
                FROM custom_drill_queues
                ORDER BY id DESC
                """
            )
            rows = cursor.fetchall()
            result = []
            for r in rows:
                try:
                    items = json.loads(r["items"])
                except Exception:
                    items = []
                result.append(
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "created_at": r["created_at"],
                        "description": r["description"] or "",
                        "items": items,
                        "exercises": items,
                        "count": len(items),
                    }
                )
            return result

    def get_custom_queue(self, queue_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific custom queue by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, created_at, description, items
                FROM custom_drill_queues
                WHERE id = ?
                """,
                (queue_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            try:
                items = json.loads(row["items"])
            except Exception:
                items = []
            return {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "description": row["description"] or "",
                "items": items,
                "exercises": items,
                "count": len(items),
            }

    def get_latest_custom_queue(self) -> Optional[Dict[str, Any]]:
        """Retrieve the most recently created custom drill queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, created_at, description, items
                FROM custom_drill_queues
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                return None
            try:
                items = json.loads(row["items"])
            except Exception:
                items = []
            return {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "description": row["description"] or "",
                "items": items,
                "exercises": items,
                "count": len(items),
            }

    def delete_custom_queue(self, queue_id: int) -> bool:
        """Delete a custom drill queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_drill_queues WHERE id = ?", (queue_id,))
            conn.commit()
            return cursor.rowcount > 0

    def export_custom_queue_to_json(self, queue_id: int, file_path: Path | str) -> str:
        """Export custom queue to a standalone JSON file ready for CLI execution."""
        q = self.get_custom_queue(queue_id)
        if not q:
            raise ValueError(f"Fila ID {queue_id} não encontrada.")
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(q, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(target)

    def load_custom_queue_from_json(self, file_path: Path | str) -> List[str]:
        """Load exercise sequence from a JSON file."""
        target = Path(file_path)
        if not target.is_file():
            raise FileNotFoundError(f"Arquivo de fila '{file_path}' não encontrado.")
        data = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            return [str(x).strip() for x in data["items"] if str(x).strip()]
        raise ValueError("Estrutura JSON inválida para fila customizada. Esperado lista ou objeto com campo 'items'.")

    # ==========================================================================
    # AI Strategy Coach Methods
    # ==========================================================================

    def record_ai_strategy_interaction(
        self,
        role: str,
        message: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> int:
        """Record interaction in strategy coach chat history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ai_strategy_interactions (role, message, tokens_used, cost_usd)
                VALUES (?, ?, ?, ?)
                """,
                (role, message, tokens_used, cost_usd),
            )
            conn.commit()
            return cursor.lastrowid

    def get_ai_strategy_interactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent strategy coach conversations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, role, message, tokens_used, cost_usd, timestamp
                FROM ai_strategy_interactions
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "role": r["role"],
                    "message": r["message"],
                    "tokens_used": r["tokens_used"],
                    "cost_usd": r["cost_usd"],
                    "timestamp": r["timestamp"],
                }
                for r in rows
            ]

    def clear_ai_strategy_interactions(self) -> None:
        """Clear strategy coach conversational history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ai_strategy_interactions;")
            conn.commit()

    def get_ai_strategy_context(self) -> Dict[str, Any]:
        """Aggregate multidimensional performance context to feed the AI Strategy Coach."""
        stats = self.get_overall_statistics()
        deep = self.get_deep_analytics_report()

        # Extract top stuck points
        stuck_points: Dict[str, int] = {}
        for ex in deep["exercise_report"]:
            sp = ex.get("last_stuck_point", "").strip()
            if sp and sp != "Nenhum" and sp != "-":
                stuck_points[sp] = stuck_points.get(sp, 0) + 1

        top_stuck = sorted(stuck_points.items(), key=lambda x: x[1], reverse=True)[:5]

        # Critical patterns
        critical_patterns = [
            p for p in stats["pattern_summary"]
            if p["attempts"] > 0 and (p["autonomy_rate"] < 70.0 or p["accuracy_rate"] < 75.0)
        ]

        # Training vs Mastered lists
        mastered_names = [e["id"] for e in deep["exercise_report"] if e.get("mastery_status") == "mastered"]
        training_names = [e["id"] for e in deep["exercise_report"] if e.get("mastery_status") == "training"]
        unattempted_names = [e["id"] for e in deep["exercise_report"] if e.get("mastery_status") == "unattempted"]

        return {
            "total_exercises": stats["total_exercises"],
            "mastered_count": stats["mastered_count"],
            "training_count": stats["training_count"],
            "unattempted_count": stats["unattempted_count"],
            "completion_percentage": stats["completion_percentage"],
            "global_accuracy_rate": stats["global_accuracy_rate"],
            "global_avg_duration_formatted": stats["global_avg_duration_formatted"],
            "pattern_summary": stats["pattern_summary"],
            "critical_patterns": critical_patterns,
            "top_stuck_points": top_stuck,
            "error_reasons": stats["error_reasons_summary"],
            "mastered_exercises": mastered_names,
            "training_exercises": training_names,
            "unattempted_exercises": unattempted_names,
            "level_report": deep["level_report"],
        }


# ==============================================================================
# CLI Helper Utilities
# ==============================================================================


def print_dashboard(db: ExamDatabase, show_traces: bool = False) -> None:
    """Print the complete stats dashboard in rich terminal format."""
    stats = db.get_overall_statistics()

    CYAN = "\033[1;36m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[1;31m"
    BLUE = "\033[1;34m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    print(f"\n{CYAN}╔══════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║             📊 42 EXAMSHELL - STATS DASHBOARD & PADRÕES TÉCNICOS                 ║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════════════════════════════════════════════════╝{RESET}\n")

    total = stats["total_exercises"]
    mastered = stats["mastered_count"]
    pending = stats["pending_count"]
    pct = stats["completion_percentage"]

    print(f"{BOLD}📈 Progresso Geral do Rank 02:{RESET}")
    print(f"  • Total de Exercícios: {BOLD}{total}{RESET}")
    print(f"  • Dominados (>=1 Sucesso): {GREEN}{mastered}{RESET} ({GREEN}{pct:.1f}%{RESET})")
    print(f"  • Pendentes: {YELLOW}{pending}{RESET}")
    print(f"  • Total de Submissões: {stats['total_attempts']} | Tempo Médio: {stats['global_avg_duration_formatted']}\n")

    print(f"{BOLD}🧠 Desempenho por Padrão Técnico (13 Padrões):{RESET}")
    print(f"{'PADRÃO TÉCNICO':<25} | {'QUESTÕES':<8} | {'DOMINADAS':<9} | {'TENTATIVAS':<10} | {'ACERTO (%)':<10} | STATUS")
    print("-" * 82)

    for p in stats["pattern_summary"]:
        rate = p["accuracy_rate"]
        if p["attempts"] == 0:
            status_str = f"{YELLOW}SEM TREINO{RESET}"
            rate_str = "    -    "
        elif rate >= 80.0:
            status_str = f"{GREEN}EXCELENTE{RESET}"
            rate_str = f"{rate:6.1f}%  "
        elif rate >= 50.0:
            status_str = f"{YELLOW}REGULAR  {RESET}"
            rate_str = f"{rate:6.1f}%  "
        else:
            status_str = f"{RED}CRÍTICO  {RESET}"
            rate_str = f"{rate:6.1f}%  "

        print(
            f"{p['pattern']:<25} | {p['total_exercises']:<8} | {p['mastered_exercises']:<9} | "
            f"{p['attempts']:<10} | {rate_str} | {status_str}"
        )
    print("-" * 82)

    print(f"\n{BOLD}📋 Estatísticas por Exercício (Rank 02):{RESET}")
    print(f"{'EXERCÍCIO':<20} | {'LVL':<3} | {'TENTATIVAS':<10} | {'SUCESSO (%)':<11} | {'TEMPO MÉD':<9} | {'MOTIVO ÚLTIMO ERRO'}")
    print("-" * 82)

    for ex in stats["all_exercises_stats"]:
        rate_str = f"{ex.success_rate:5.1f}%" if ex.total_attempts > 0 else "   -  "
        dur_str = format_duration(ex.avg_duration_seconds) if ex.total_attempts > 0 else "--:--"
        err_reason = ex.last_error_reason or "Nenhum"
        if ex.successful_attempts > 0 and ex.failed_attempts == 0:
            err_reason = f"{GREEN}Aprovado{RESET}"
        elif ex.last_error_reason:
            err_reason = f"{RED}{ex.last_error_reason}{RESET}"

        print(
            f"{ex.id:<20} | L{ex.level:<2} | {ex.total_attempts:<10} | {rate_str:<11} | {dur_str:<9} | {err_reason}"
        )
    print("-" * 82)

    print(f"\n{BOLD}🎯 Top 5 Questões Críticas / Foco de Treino:{RESET}")
    for idx, p in enumerate(stats["top_problematic"], start=1):
        reason = "Nunca tentada" if p.total_attempts == 0 else f"{p.failed_attempts} falhas ({p.success_rate:.1f}% acerto)"
        print(f"  {idx}. {BOLD}{p.id:<18}{RESET} [Level {p.level}] - {YELLOW}{reason}{RESET} - Padrões: {BLUE}{', '.join(p.patterns)}{RESET}")

    if show_traces:
        print(f"\n{BOLD}🔍 Últimos Traces de Erro Registrados:{RESET}")
        has_traces = False
        for ex in stats["all_exercises_stats"]:
            if ex.last_error_trace:
                has_traces = True
                print(f"\n{RED}=== Trace de Erro: {ex.id} (Level {ex.level}) ==={RESET}")
                print(ex.last_error_trace.strip())
                print(f"{RED}{'=' * 50}{RESET}")
        if not has_traces:
            print("  Nenhum erro com trace registrado até o momento.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="42 Examshell Rank 02 Database & Active Trainer")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB_PATH), help="Path to stats.db")

    subparsers = parser.add_subparsers(dest="command")

    # Command: init
    subparsers.add_parser("init", help="Initialize database and seed 55 Rank 02 exercises")

    # Command: record
    rec_parser = subparsers.add_parser("record", help="Record an attempt")
    rec_parser.add_argument("exercise_id", type=str, help="Exercise identifier (e.g. first_word)")
    rec_parser.add_argument("success", type=int, choices=[0, 1], help="1 for success, 0 for failure")
    rec_parser.add_argument("duration_seconds", type=int, help="Duration in seconds")
    rec_parser.add_argument("--trace-file", type=str, default="", help="Path to error trace file")
    rec_parser.add_argument("--trace-text", type=str, default="", help="Inline error trace text")
    rec_parser.add_argument("--code-file", type=str, default="", help="Path to submitted C source file")
    rec_parser.add_argument("--code-text", type=str, default="", help="Inline C source code")
    rec_parser.add_argument("--error-reason", type=str, default="", help="Categorized error reason")
    rec_parser.add_argument("--user-notes", "--notes", dest="user_notes", type=str, default="", help="User reflective notes")
    rec_parser.add_argument("--independence-status", "--independence", dest="independence_status", type=str, default="", help="Independence status (alone, searched, etc.)")
    rec_parser.add_argument("--stuck-point", "--stuck", dest="stuck_point", type=str, default="", help="Point where user got stuck")

    # Command: feedback
    fb_parser = subparsers.add_parser("feedback", help="Update attempt self-assessment feedback")
    fb_parser.add_argument("attempt_id", type=int, help="Attempt ID")
    fb_parser.add_argument("--user-notes", "--notes", dest="user_notes", type=str, default=None, help="User reflective notes")
    fb_parser.add_argument("--independence-status", "--independence", dest="independence_status", type=str, default=None, help="Independence status (alone, searched, etc.)")
    fb_parser.add_argument("--stuck-point", "--stuck", dest="stuck_point", type=str, default=None, help="Point where user got stuck")

    # Command: stats
    stats_parser = subparsers.add_parser("stats", help="Display stats dashboard")
    stats_parser.add_argument("--traces", action="store_true", help="Display full error traces")

    # Command: list-patterns
    subparsers.add_parser("list-patterns", help="List all available technical patterns")

    # Command: pick
    pick_parser = subparsers.add_parser("pick", help="Pick next exercise according to strategy")
    pick_parser.add_argument("--mode", choices=["sim", "pattern", "weakness"], default="weakness")
    pick_parser.add_argument("--level", type=int, default=None, help="Filter by level (0-3)")
    pick_parser.add_argument("--pattern", type=str, default=None, help="Pattern name for pattern drill")

    # Command: show-trace
    trace_parser = subparsers.add_parser("show-trace", help="Show last error trace for exercise")
    trace_parser.add_argument("exercise_id", type=str, help="Exercise identifier")

    # Command: get-by-pattern
    get_pat_parser = subparsers.add_parser("get-by-pattern", help="Fetch exercises for a pattern")
    get_pat_parser.add_argument("pattern_name", type=str, help="Pattern name")

    # Command: list-queues
    subparsers.add_parser("list-queues", help="List all saved custom drill queues")

    # Command: get-queue
    get_q_parser = subparsers.add_parser("get-queue", help="Get exercises from a custom queue")
    get_q_parser.add_argument("target", nargs="?", default="latest", help="Queue ID, 'latest', or path to .json file")

    # Command: list-exercises
    list_ex_parser = subparsers.add_parser("list-exercises", help="List all 55 exercises")
    list_ex_parser.add_argument("--level", type=int, default=None, help="Filter by level (0-3)")

    # Command: get-exercise-info
    info_ex_parser = subparsers.add_parser("get-exercise-info", help="Get metadata for an exercise")
    info_ex_parser.add_argument("exercise_id", type=str, help="Exercise identifier")

    args = parser.parse_args()

    db = ExamDatabase(args.db)

    if args.command == "init" or args.command is None:
        if args.command is None:
            print_dashboard(db)
        else:
            print(f"✅ Banco de dados inicializado com sucesso em: {db.db_path}")

    elif args.command == "record":
        trace_content = None
        if args.trace_file and os.path.isfile(args.trace_file):
            try:
                with open(args.trace_file, "r", encoding="utf-8", errors="replace") as f:
                    trace_content = f.read()
            except Exception as e:
                trace_content = f"Error reading trace file: {e}"
        elif args.trace_text:
            trace_content = args.trace_text

        code_content = None
        if args.code_file and os.path.isfile(args.code_file):
            try:
                with open(args.code_file, "r", encoding="utf-8", errors="replace") as f:
                    code_content = f.read()
            except Exception as e:
                code_content = f"/* Error reading code file: {e} */"
        elif args.code_text:
            code_content = args.code_text

        att_id = db.record_attempt(
            exercise_id=args.exercise_id,
            success=bool(args.success),
            duration_seconds=args.duration_seconds,
            error_trace=trace_content,
            submitted_code=code_content,
            error_reason=args.error_reason or None,
            user_notes=args.user_notes or None,
            independence_status=args.independence_status or None,
            stuck_point=args.stuck_point or None,
        )
        print(f"RECORDED:{att_id}")

    elif args.command == "feedback":
        ok = db.update_attempt_feedback(
            attempt_id=args.attempt_id,
            user_notes=args.user_notes,
            independence_status=args.independence_status,
            stuck_point=args.stuck_point,
        )
        if ok:
            print(f"FEEDBACK_UPDATED:{args.attempt_id}")
        else:
            print(f"ERROR: Tentativa {args.attempt_id} não encontrada.", file=sys.stderr)
            sys.exit(1)

    elif args.command == "stats":
        print_dashboard(db, show_traces=args.traces)

    elif args.command == "list-patterns":
        for p in db.get_all_patterns():
            print(p)

    elif args.command == "pick":
        if args.mode == "pattern":
            if not args.pattern:
                print("ERROR: --pattern is required when mode is pattern", file=sys.stderr)
                sys.exit(1)
            candidates = db.get_exercises_by_pattern(args.pattern)
            if not candidates:
                print(f"ERROR: No exercises found for pattern '{args.pattern}'", file=sys.stderr)
                sys.exit(1)
            stats_map = {s.id: s for s in db.get_exercise_stats()}
            candidates.sort(key=lambda ex: (ex.level, stats_map[ex.id].success_rate if ex.id in stats_map else 0))
            chosen = candidates[0]
            print(f"{chosen.id}:{chosen.level}:{chosen.patterns_str}")

        elif args.mode == "sim":
            lvl = 0 if args.level is None else args.level
            candidates = db.get_exercises_by_level(lvl)
            if not candidates:
                print(f"ERROR: No exercises found for level {lvl}", file=sys.stderr)
                sys.exit(1)
            import random
            chosen = random.choice(candidates)
            print(f"{chosen.id}:{chosen.level}:{chosen.patterns_str}")

        elif args.mode == "weakness":
            queue = db.get_review_queue()
            if args.level is not None:
                queue = [q for q in queue if q.level == args.level]
            if not queue:
                print("ERROR: Queue empty", file=sys.stderr)
                sys.exit(1)
            chosen_stat = queue[0]
            print(f"{chosen_stat.id}:{chosen_stat.level}:{', '.join(chosen_stat.patterns)}")

    elif args.command == "show-trace":
        history = db.get_attempts_for_exercise(args.exercise_id)
        failed_attempts = [a for a in history if not a.success and a.error_trace]
        if not failed_attempts:
            print(f"Nenhum trace de erro encontrado para {args.exercise_id}.")
        else:
            latest = failed_attempts[0]
            print(f"--- Trace da tentativa {latest.id} em {latest.timestamp} ({format_duration(latest.duration_seconds)}) ---")
            print(latest.error_trace)

    elif args.command == "get-by-pattern":
        exs = db.get_exercises_by_pattern(args.pattern_name)
        if not exs:
            print(f"Nenhum exercício encontrado para o padrão '{args.pattern_name}'.", file=sys.stderr)
            sys.exit(1)
        for ex in exs:
            print(f"{ex.id}:{ex.level}:{ex.patterns_str}")

    elif args.command == "list-queues":
        queues = db.get_custom_queues()
        if not queues:
            print("Nenhuma fila customizada salva no banco.")
        else:
            print(f"{'ID':<4} | {'NOME DA FILA':<30} | {'ITENS':<6} | {'CRIADA EM'}")
            print("-" * 65)
            for q in queues:
                print(f"#{q['id']:<3} | {q['name']:<30} | {q['count']:<6} | {q['created_at']}")

    elif args.command == "get-queue":
        target = args.target.strip()
        exercise_names: List[str] = []
        if target.endswith(".json") or os.path.isfile(target):
            try:
                exercise_names = db.load_custom_queue_from_json(target)
            except Exception as e:
                print(f"ERROR: Falha ao carregar fila do arquivo '{target}': {e}", file=sys.stderr)
                sys.exit(1)
        elif target == "latest":
            latest = db.get_latest_custom_queue()
            if not latest:
                print("ERROR: Nenhuma fila customizada salva.", file=sys.stderr)
                sys.exit(1)
            exercise_names = latest.get("exercises") or latest.get("items") or []
        elif target.isdigit():
            q = db.get_custom_queue(int(target))
            if not q:
                print(f"ERROR: Fila #{target} não encontrada.", file=sys.stderr)
                sys.exit(1)
            exercise_names = q.get("exercises") or q.get("items") or []
        else:
            print(f"ERROR: Alvo de fila inválido: '{target}'", file=sys.stderr)
            sys.exit(1)

        for ex_id in exercise_names:
            ex = db.get_exercise(ex_id)
            if ex:
                print(f"{ex.id}:{ex.level}:{ex.patterns_str}")
            else:
                print(f"{ex_id}:0:C Standard")

    elif args.command == "list-exercises":
        all_exs = db.get_all_exercises()
        if args.level is not None:
            all_exs = [e for e in all_exs if e.level == args.level]
        for ex in all_exs:
            print(f"{ex.id}:{ex.level}:{ex.patterns_str}")

    elif args.command == "get-exercise-info":
        ex = db.get_exercise(args.exercise_id)
        if not ex:
            print(f"ERROR: Exercício '{args.exercise_id}' não encontrado.", file=sys.stderr)
            sys.exit(1)
        print(f"{ex.id}:{ex.level}:{ex.patterns_str}")


if __name__ == "__main__":
    main()
