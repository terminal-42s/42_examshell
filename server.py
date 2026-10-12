#!/usr/bin/env python3
"""
42 Examshell Active Learning & Analytics Dashboard Server.

Provides a lightweight, zero-dependency HTTP server with REST APIs,
database queries, auto-polling support, and Azure AI Foundry / OpenAI integration.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from db import ExamDatabase, format_duration, detect_error_reason

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ENV_PATH = BASE_DIR / ".env"
STATS_DB_PATH = BASE_DIR / ".resources" / "rank02" / "stats.db"


def load_env(env_path: Path = ENV_PATH) -> None:
    """Load environment variables from a .env file without external dependencies."""
    if not env_path.is_file():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        print(f"Warning: Could not read {env_path}: {e}", file=sys.stderr)


load_env()

# Initialize shared database instance
db = ExamDatabase(STATS_DB_PATH)


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP Request Handler serving Dashboard SPA and REST API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path in ("/", "/index.html"):
            self.serve_dashboard()
        elif path == "/api/stats":
            self.handle_api_stats()
        elif path == "/api/stats/timeline":
            self.handle_api_stats_timeline(parsed_url.query)
        elif path == "/api/stats/day-details":
            self.handle_api_stats_day_details(parsed_url.query)
        elif path == "/api/reports/analytics":
            self.handle_api_reports_analytics(parsed_url.query)
        elif path == "/api/history":
            self.handle_api_history(parsed_url.query)
        elif path == "/api/latest":
            self.handle_api_latest()
        elif path.startswith("/api/attempt/") or path.startswith("/api/attempts/"):
            attempt_id_str = path.rstrip("/").split("/")[-1]
            self.handle_api_attempt(attempt_id_str)
        elif path.startswith("/api/exercise/") or path.startswith("/api/exercises/"):
            exercise_id = path.rstrip("/").split("/")[-1]
            self.handle_api_exercise_details(exercise_id)
        elif path == "/api/ai-chat/history":
            self.handle_api_ai_chat_history(parsed_url.query)
        elif path in ("/api/custom-queue", "/api/custom-queues"):
            self.handle_api_custom_queues_list()
        elif path.startswith("/api/custom-queue/"):
            queue_id_str = path.rstrip("/").split("/")[-1]
            self.handle_api_custom_queue_get(queue_id_str)
        elif path == "/api/ai-strategy/history":
            self.handle_api_ai_strategy_history()
        elif path == "/api/ai-strategy/context":
            self.handle_api_ai_strategy_context()
        else:
            # Serve static assets (CSS, JS, images) if requested
            super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/ai-tutor":
            self.handle_api_ai_tutor()
        elif path == "/api/ai-chat/clear":
            self.handle_api_ai_chat_clear()
        elif path == "/api/ai-strategy":
            self.handle_api_ai_strategy()
        elif path == "/api/ai-strategy/clear":
            self.handle_api_ai_strategy_clear()
        elif path in ("/api/custom-queue", "/api/custom-queues"):
            self.handle_api_custom_queue_create()
        elif "/api/attempts/" in path or "/api/attempt/" in path:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 3:
                attempt_id_str = parts[2]
                self.handle_api_attempt_feedback(attempt_id_str)
            else:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid attempt feedback path")
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "API route not found")

    def do_PATCH(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if "/api/attempts/" in path or "/api/attempt/" in path:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 3:
                attempt_id_str = parts[2]
                self.handle_api_attempt_feedback(attempt_id_str)
            else:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid attempt feedback path")
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "API route not found")

    def do_DELETE(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/custom-queue/"):
            queue_id_str = path.rstrip("/").split("/")[-1]
            self.handle_api_custom_queue_delete(queue_id_str)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "API route not found")

    # ==========================================================================
    # API Handlers
    # ==========================================================================

    def serve_dashboard(self) -> None:
        """Serve index.html with no-cache headers."""
        index_file = STATIC_DIR / "index.html"
        if not index_file.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "index.html not found")
            return

        with open(index_file, "rb") as f:
            content = f.read()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(content)

    def handle_api_stats(self) -> None:
        """Return consolidated analytical stats."""
        stats = db.get_overall_statistics()

        # Serialize exercise stats
        serialized_exercises = []
        for ex in stats["all_exercises_stats"]:
            serialized_exercises.append(
                {
                    "id": ex.id,
                    "level": ex.level,
                    "patterns": ex.patterns,
                    "total_attempts": ex.total_attempts,
                    "successful_attempts": ex.successful_attempts,
                    "failed_attempts": ex.failed_attempts,
                    "success_rate": round(ex.success_rate, 1),
                    "avg_duration_seconds": round(ex.avg_duration_seconds, 1),
                    "avg_duration_formatted": format_duration(ex.avg_duration_seconds),
                    "last_attempt_at": ex.last_attempt_at or "",
                    "last_error_reason": ex.last_error_reason or "",
                    "best_time_seconds": ex.best_time_seconds,
                    "best_time_formatted": format_duration(ex.best_time_seconds),
                }
            )

        response_data = {
            "total_exercises": stats["total_exercises"],
            "mastered_count": stats["mastered_count"],
            "pending_count": stats["pending_count"],
            "completion_percentage": round(stats["completion_percentage"], 1),
            "total_attempts": stats["total_attempts"],
            "total_successes": stats["total_successes"],
            "global_accuracy_rate": round(stats["global_accuracy_rate"], 1),
            "global_avg_duration_seconds": round(stats["global_avg_duration_seconds"], 1),
            "global_avg_duration_formatted": stats["global_avg_duration_formatted"],
            "most_vulnerable_pattern": stats["most_vulnerable_pattern"],
            "error_reasons_summary": stats["error_reasons_summary"],
            "pattern_summary": stats["pattern_summary"],
            "top_problematic": [
                {
                    "id": p.id,
                    "level": p.level,
                    "patterns": p.patterns,
                    "total_attempts": p.total_attempts,
                    "failed_attempts": p.failed_attempts,
                    "success_rate": round(p.success_rate, 1),
                }
                for p in stats["top_problematic"]
            ],
            "exercises": serialized_exercises,
            "latest_attempt_id": db.get_latest_attempt_id(),
        }

        self.send_json_response(response_data)

    def handle_api_stats_timeline(self, query_string: str) -> None:
        """Return daily aggregated metrics and activity history."""
        query_params = parse_qs(query_string)
        start_date = query_params.get("start_date", [None])[0]
        end_date = query_params.get("end_date", [None])[0]

        timeline = db.get_timeline_stats(start_date=start_date, end_date=end_date)
        self.send_json_response({"timeline": timeline})

    def handle_api_stats_day_details(self, query_string: str) -> None:
        """Return detailed submissions and pattern breakdown for a specific date."""
        query_params = parse_qs(query_string)
        date_str = query_params.get("date", [None])[0]

        if not date_str:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Parameter 'date' (YYYY-MM-DD) is required.")
            return

        details = db.get_day_details(date_str)
        self.send_json_response(details)

    def handle_api_reports_analytics(self, query_string: str) -> None:
        """Return deep analytical multidimensional report."""
        query_params = parse_qs(query_string)
        start_date = query_params.get("start_date", [None])[0]
        end_date = query_params.get("end_date", [None])[0]
        level_str = query_params.get("level", [None])[0]
        level = int(level_str) if level_str and level_str.isdigit() else None
        pattern = query_params.get("pattern", [None])[0]
        exercise_id = query_params.get("exercise", [None])[0] or query_params.get("exercise_id", [None])[0]

        report = db.get_deep_analytics_report(
            start_date=start_date,
            end_date=end_date,
            level=level,
            pattern=pattern,
            exercise_id=exercise_id,
        )
        self.send_json_response(report)

    def handle_api_attempt_feedback(self, attempt_id_str: str) -> None:
        """Update reflexive self-assessment feedback for an attempt."""
        try:
            attempt_id = int(attempt_id_str)
        except ValueError:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Invalid attempt id")
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body) if body else {}
        except Exception as e:
            self.send_json_error(HTTPStatus.BAD_REQUEST, f"Malformed JSON: {e}")
            return

        user_notes = payload.get("user_notes")
        independence_status = payload.get("independence_status")
        stuck_point = payload.get("stuck_point")

        success = db.update_attempt_feedback(
            attempt_id=attempt_id,
            user_notes=user_notes,
            independence_status=independence_status,
            stuck_point=stuck_point,
        )

        if not success:
            self.send_json_error(HTTPStatus.NOT_FOUND, f"Attempt {attempt_id} not found")
            return

        updated_attempt = db.get_attempt_by_id(attempt_id)
        self.send_json_response({
            "status": "success",
            "message": "Feedback atualizado com sucesso.",
            "attempt": {
                "id": attempt_id,
                "user_notes": updated_attempt.user_notes if updated_attempt else (user_notes or ""),
                "independence_status": updated_attempt.independence_status if updated_attempt else (independence_status or ""),
                "stuck_point": updated_attempt.stuck_point if updated_attempt else (stuck_point or ""),
            }
        })

    def handle_api_history(self, query_string: str) -> None:
        """Return attempts history with flexible filtering (date range, status, pattern, exercise)."""
        query_params = parse_qs(query_string)
        limit = 100
        if "limit" in query_params:
            try:
                limit = int(query_params["limit"][0])
            except ValueError:
                pass

        start_date = query_params.get("start_date", [None])[0]
        end_date = query_params.get("end_date", [None])[0]
        status = query_params.get("status", [None])[0]
        exercise_id = query_params.get("exercise_id", [None])[0] or query_params.get("exercise", [None])[0]
        pattern = query_params.get("pattern", [None])[0]

        # Use multi-criteria filter if any advanced filter is requested
        if start_date or end_date or status or pattern or (exercise_id and ("status" in query_params or "start_date" in query_params)):
            data = db.get_filtered_attempts(
                start_date=start_date,
                end_date=end_date,
                status=status,
                exercise_id=exercise_id,
                pattern=pattern,
                limit=limit,
            )
        elif exercise_id:
            attempts = db.get_attempts_for_exercise(exercise_id)
            data = [
                {
                    "id": a.id,
                    "exercise_id": a.exercise_id,
                    "timestamp": a.timestamp,
                    "duration_seconds": a.duration_seconds,
                    "duration_formatted": format_duration(a.duration_seconds),
                    "success": a.success,
                    "error_reason": a.error_reason,
                    "has_trace": bool(a.error_trace),
                    "has_code": bool(a.submitted_code),
                    "user_notes": getattr(a, "user_notes", ""),
                    "independence_status": getattr(a, "independence_status", ""),
                    "stuck_point": getattr(a, "stuck_point", ""),
                }
                for a in attempts[:limit]
            ]
        else:
            attempts = db.get_all_attempts(limit=limit)
            data = [
                {
                    "id": a.id,
                    "exercise_id": a.exercise_id,
                    "timestamp": a.timestamp,
                    "duration_seconds": a.duration_seconds,
                    "duration_formatted": format_duration(a.duration_seconds),
                    "success": a.success,
                    "error_reason": a.error_reason,
                    "has_trace": bool(a.error_trace),
                    "has_code": bool(a.submitted_code),
                    "user_notes": getattr(a, "user_notes", ""),
                    "independence_status": getattr(a, "independence_status", ""),
                    "stuck_point": getattr(a, "stuck_point", ""),
                }
                for a in attempts
            ]

        self.send_json_response({"attempts": data})

    def handle_api_latest(self) -> None:
        """Return the latest attempt ID for polling."""
        latest_id = db.get_latest_attempt_id()
        self.send_json_response({"latest_attempt_id": latest_id})

    def handle_api_attempt(self, attempt_id_str: str) -> None:
        """Return full details of an attempt including code, trace and reflexive self-assessment."""
        try:
            attempt_id = int(attempt_id_str)
        except ValueError:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Invalid attempt id")
            return

        attempt = db.get_attempt_by_id(attempt_id)
        if not attempt:
            self.send_json_error(HTTPStatus.NOT_FOUND, "Attempt not found")
            return

        ex = db.get_exercise(attempt.exercise_id)

        data = {
            "id": attempt.id,
            "exercise_id": attempt.exercise_id,
            "level": ex.level if ex else None,
            "patterns": ex.patterns if ex else [],
            "timestamp": attempt.timestamp,
            "duration_seconds": attempt.duration_seconds,
            "duration_formatted": format_duration(attempt.duration_seconds),
            "success": attempt.success,
            "error_trace": attempt.error_trace or "Sem trace de erro disponível.",
            "submitted_code": attempt.submitted_code or "/* Código fonte não capturado nesta tentativa */",
            "error_reason": attempt.error_reason or ("Sucesso" if attempt.success else "Falha Desconhecida"),
            "user_notes": attempt.user_notes or "",
            "independence_status": attempt.independence_status or "",
            "stuck_point": attempt.stuck_point or "",
        }

        self.send_json_response(data)

    def handle_api_exercise_details(self, exercise_id: str) -> None:
        """Return full profile for an exercise including stats, attempts, and AI chat."""
        if not exercise_id:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Exercise ID is required.")
            return

        profile = db.get_exercise_full_profile(exercise_id)
        if not profile:
            self.send_json_error(HTTPStatus.NOT_FOUND, f"Exercise '{exercise_id}' not found.")
            return

        self.send_json_response(profile)

    def handle_api_ai_chat_history(self, query_string: str) -> None:
        """Return conversational history for an exercise and attempt."""
        query_params = parse_qs(query_string)
        exercise_id = query_params.get("exercise_id", [None])[0] or query_params.get("exercise", [None])[0]
        attempt_id_str = query_params.get("attempt_id", [None])[0]
        attempt_id = int(attempt_id_str) if attempt_id_str and attempt_id_str.isdigit() else None

        if not exercise_id:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Parameter 'exercise_id' is required.")
            return

        history = db.get_ai_interactions(exercise_id, attempt_id=attempt_id)
        self.send_json_response({"exercise_id": exercise_id, "messages": history})

    def handle_api_ai_chat_clear(self) -> None:
        """Clear conversation history for an exercise."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body)
        except Exception as e:
            self.send_json_error(HTTPStatus.BAD_REQUEST, f"Malformed JSON: {e}")
            return

        exercise_id = payload.get("exercise_id")
        if not exercise_id:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Parameter 'exercise_id' is required.")
            return

        db.clear_ai_interactions(exercise_id)
        self.send_json_response({"status": "success", "message": f"Histórico limpo para '{exercise_id}'."})

    def handle_api_ai_tutor(self) -> None:
        """Call Azure AI Foundry / Azure OpenAI to get pedagogical feedback and handle interactive chat."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body)
        except Exception as e:
            self.send_json_error(HTTPStatus.BAD_REQUEST, f"Malformed JSON: {e}")
            return

        attempt_id = payload.get("attempt_id")
        code = payload.get("code")
        trace = payload.get("trace")
        exercise_id = payload.get("exercise_id")
        user_message = payload.get("user_message")  # Follow-up question from the user

        if attempt_id:
            attempt = db.get_attempt_by_id(int(attempt_id))
            if attempt:
                if not code:
                    code = attempt.submitted_code
                if not trace:
                    trace = attempt.error_trace
                if not exercise_id:
                    exercise_id = attempt.exercise_id

        if not exercise_id:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "exercise_id or attempt_id is required")
            return

        ex = db.get_exercise(exercise_id)
        patterns_str = ", ".join(ex.patterns) if ex else "C Standard"
        level_str = str(ex.level) if ex else "Rank 02"

        # Check Azure AI credentials
        endpoint = os.environ.get("AZURE_AI_ENDPOINT", "").strip()
        api_key = os.environ.get("AZURE_AI_API_KEY", "").strip()

        if not endpoint or not api_key:
            # Fallback when credentials are not configured
            fallback_hint = self.generate_offline_hint(exercise_id, level_str, patterns_str, code, trace)
            self.send_json_response(
                {
                    "status": "warning",
                    "tutor_response": fallback_hint,
                    "azure_configured": False,
                    "note": "Configure AZURE_AI_ENDPOINT e AZURE_AI_API_KEY no arquivo .env para respostas da Azure AI Foundry.",
                }
            )
            return

        # Prepare system prompt
        system_prompt = (
            "Você é um tutor sênior da Escola 42 focado no Rank 02. "
            "Você analisa o código C enviado pelo aluno, os traces de erro do tester/gcc e responde dúvidas do aluno. "
            "Explique a causa raiz do erro de forma pedagógica, indique o padrão técnico envolvido e aponte "
            "armadilhas de ponteiro/memória/ASCII sem dar a função pronta completa, guiando o aluno a corrigir "
            "com o próprio raciocínio. Responda em português brasileiro claro com Markdown formatado."
        )

        # Retrieve prior chat interactions for this exercise / attempt to keep conversational context
        prev_interactions = db.get_ai_interactions(exercise_id, attempt_id=int(attempt_id) if attempt_id else None, limit=12)

        messages = [{"role": "system", "content": system_prompt}]

        # Context initial prompt
        initial_context = (
            f"Contexto do Exercício:\n"
            f"- Exercício: {exercise_id} (Level {level_str})\n"
            f"- Padrões Técnicos Associados: {patterns_str}\n\n"
            f"--- Código C Submetido ---\n"
            f"{code or '/* Nenhum código submetido ainda */'}\n\n"
            f"--- Trace do Compilador / Tester ---\n"
            f"{trace or 'Sem trace de erro registrado'}"
        )

        # Add history
        if prev_interactions:
            messages.append({"role": "user", "content": initial_context})
            for inter in prev_interactions:
                messages.append({"role": inter["role"], "content": inter["message"]})

            # Append new user question
            current_user_text = user_message.strip() if user_message else "Por favor, continue a análise e me oriente na resolução."
            messages.append({"role": "user", "content": current_user_text})
        else:
            # First turn: initial diagnosis or initial question
            current_user_text = (
                f"{initial_context}\n\n"
                f"Pergunta do aluno: {user_message.strip() if user_message else 'Por favor, ajude-me a entender onde está a falha lógica ou de implementação, sem entregar o código pronto.'}"
            )
            messages.append({"role": "user", "content": current_user_text})

        # Save user message to database
        db_user_msg = user_message.strip() if user_message else "Diagnóstico inicial do código e trace de erro."
        db.record_ai_interaction(
            exercise_id=exercise_id,
            role="user",
            message=db_user_msg,
            attempt_id=int(attempt_id) if attempt_id else None,
        )

        request_body = {
            "messages": messages,
            "max_tokens": 1200,
            "temperature": 0.3,
        }

        # Automatically adapt for GPT-5 or reasoning models
        if any(m in endpoint.lower() for m in ["gpt-5", "o1", "o3"]):
            request_body.pop("max_tokens", None)
            request_body.pop("temperature", None)
            request_body["max_completion_tokens"] = 1500

        def send_azure_request(body: dict) -> dict:
            req_data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(endpoint, data=req_data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("api-key", api_key)
            req.add_header("Authorization", f"Bearer {api_key}")
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode("utf-8"))

        try:
            try:
                resp_json = send_azure_request(request_body)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if "max_tokens" in err_body and "max_completion_tokens" in err_body:
                    request_body.pop("max_tokens", None)
                    request_body.pop("temperature", None)
                    request_body["max_completion_tokens"] = 1500
                    resp_json = send_azure_request(request_body)
                else:
                    raise

            choices = resp_json.get("choices", [])
            if choices and "message" in choices[0]:
                reply = choices[0]["message"].get("content", "")
            else:
                reply = "Não foi possível extrair a resposta do modelo da Azure."

            usage = resp_json.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            cost_usd = (prompt_tokens * 0.0000025) + (completion_tokens * 0.000010)

            # Persist assistant reply in database
            db.record_ai_interaction(
                exercise_id=exercise_id,
                role="assistant",
                message=reply,
                attempt_id=int(attempt_id) if attempt_id else None,
                tokens_used=total_tokens,
                cost_usd=cost_usd,
            )

            # Fetch updated conversation history for full UI sync
            updated_history = db.get_ai_interactions(exercise_id, attempt_id=int(attempt_id) if attempt_id else None)

            self.send_json_response(
                {
                    "status": "success",
                    "tutor_response": reply,
                    "azure_configured": True,
                    "messages": updated_history,
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost_usd": round(cost_usd, 5),
                    },
                }
            )

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            print(f"Azure HTTP Error {e.code}: {err_body}", file=sys.stderr)
            self.send_json_response(
                {
                    "error": "Azure AI não configurada ou inacessível. Verifique o arquivo .env.",
                    "detail": f"HTTP {e.code}: {err_body[:200]}",
                    "status_code": 503,
                },
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except urllib.error.URLError as e:
            print(f"Azure URL Error: {e.reason}", file=sys.stderr)
            self.send_json_response(
                {
                    "error": "Azure AI não configurada ou inacessível. Verifique o arquivo .env.",
                    "detail": f"Connection error: {e.reason}",
                    "status_code": 503,
                },
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            print(f"Azure Unexpected Error: {e}", file=sys.stderr)
            self.send_json_response(
                {
                    "error": "Azure AI não configurada ou inacessível. Verifique o arquivo .env.",
                    "detail": str(e),
                    "status_code": 503,
                },
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )

    def generate_offline_hint(
        self,
        exercise_id: str,
        level_str: str,
        patterns: str,
        code: Optional[str],
        trace: Optional[str],
    ) -> str:
        """Smart fallback tutor guidance when Azure credentials are not set."""
        reason = detect_error_reason(False, trace)
        
        guidance = [
            f"### 💡 Diagnóstico do Tutor 42 (Modo Offline / Sem Credenciais Azure)",
            f"",
            f"**Exercício:** `{exercise_id}` (Level {level_str})",
            f"**Padrões Técnicos:** `{patterns}`",
            f"**Causa Raiz Diagnosticada:** `{reason}`",
            f"",
            f"---",
            f"",
        ]

        if reason == "Segmentation Fault":
            guidance.extend([
                "**Atenção a Acessos de Memória:**",
                "- Você tentou dereferenciar um ponteiro nulo (`NULL`) ou ultrapassou os limites da string/array.",
                "- Se o programa recebe argumentos (`argc`, `argv`), verifique se você checou se `argc == 2` (ou o número esperado) antes de acessar `argv[1]`. Se nenhum argumento for passado, acessar `argv[1][0]` causará **Segfault** imediato!",
                "- Verifique se seu loop de terminação de string para estritamente em `str[i] != '\\0'`. Se você incrementou além do terminador, o acesso resultará em violação de memória.",
            ])
        elif reason == "Wrong Output / Mismatch":
            guidance.extend([
                "**Diferença entre Saída Esperada e Obtida:**",
                "- O tester encontrou discrepância entre o seu output e o esperado pelo Moulinette.",
                "- Preste atenção em quebras de linha (`'\\n'`) finais!",
                "- Na 42, se a quantidade de parâmetros for inválida, a maioria dos exercícios exige apenas imprimir `\\n`.",
                "- Cuidado com espaços em branco extras no início, no meio ou no fim da saída (especialmente em padrões como *Skip Whitespace*).",
            ])
        elif reason == "Memory Leak / Timeout":
            guidance.extend([
                "**Loop Infinito ou Esgotamento de Tempo:**",
                "- O tester encerrou o processo após 10 segundos para evitar travamento.",
                "- Verifique as condições de parada dos seus loops `while` ou recursões.",
                "- Certifique-se de que a variável de incremento (`i++` ou avanço de ponteiro) está sendo executada em todos os ramos (`if/else`) dentro do loop.",
            ])
        elif reason == "Compilation Error":
            guidance.extend([
                "**Erro de Compilação (`gcc -Wall -Wextra -Werror`):**",
                "- Verifique declarações de tipos, protótipos de funções e inclusão de headers obrigatórios (como `<unistd.h>` para `write`, ou `<stdlib.h>` para `malloc`/`free`).",
                "- Lembre-se que flags de erro tratam avisos (warnings) como erros fatais.",
            ])
        else:
            guidance.extend([
                "**Dica Geral de Resolução:**",
                "- Analise a linha exata em que o tester reportou falha.",
                "- Teste casos de borda: string vazia `\"\"`, múltiplos espaços seguidos `\"  hello   world  \"`, sem argumentos, e caracteres especiais.",
            ])

    # ==========================================================================
    # Custom Drill Queue Handlers
    # ==========================================================================

    def handle_api_custom_queues_list(self) -> None:
        """Return list of saved custom drill queues."""
        queues = db.get_custom_queues()
        self.send_json_response({"queues": queues, "count": len(queues)})

    def handle_api_custom_queue_get(self, queue_id_str: str) -> None:
        """Return a specific custom drill queue."""
        if not queue_id_str.isdigit():
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Queue ID must be an integer.")
            return
        q = db.get_custom_queue(int(queue_id_str))
        if not q:
            self.send_json_error(HTTPStatus.NOT_FOUND, f"Custom queue #{queue_id_str} not found.")
            return
        self.send_json_response(q)

    def handle_api_custom_queue_create(self) -> None:
        """Save a new custom drill queue from JSON payload."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body)
        except Exception as e:
            self.send_json_error(HTTPStatus.BAD_REQUEST, f"Malformed JSON: {e}")
            return

        name = str(payload.get("name", "")).strip()
        exercises = payload.get("exercises", [])
        description = str(payload.get("description", "")).strip()

        if not name:
            name = f"Treino Customizado {time.strftime('%d/%m %H:%M')}"

        if not isinstance(exercises, list) or not exercises:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Parameter 'exercises' must be a non-empty list of exercise names.")
            return

        clean_exercises = [str(ex).strip() for ex in exercises if str(ex).strip()]
        if not clean_exercises:
            self.send_json_error(HTTPStatus.BAD_REQUEST, "No valid exercise names provided.")
            return

        queue_id = db.save_custom_queue(name=name, items=clean_exercises, exercises=clean_exercises, description=description)
        created_queue = db.get_custom_queue(queue_id)
        self.send_json_response(
            {
                "status": "success",
                "message": f"Fila customizada '{name}' salva com sucesso!",
                "queue": created_queue,
            },
            status=HTTPStatus.CREATED,
        )

    def handle_api_custom_queue_delete(self, queue_id_str: str) -> None:
        """Delete a custom drill queue."""
        if not queue_id_str.isdigit():
            self.send_json_error(HTTPStatus.BAD_REQUEST, "Queue ID must be an integer.")
            return
        deleted = db.delete_custom_queue(int(queue_id_str))
        if not deleted:
            self.send_json_error(HTTPStatus.NOT_FOUND, f"Queue #{queue_id_str} not found.")
            return
        self.send_json_response({"status": "success", "message": f"Fila #{queue_id_str} removida."})

    # ==========================================================================
    # AI Strategy Coach Handlers
    # ==========================================================================

    def handle_api_ai_strategy_history(self) -> None:
        """Return conversational history with AI Strategy Coach."""
        history = db.get_ai_strategy_interactions()
        self.send_json_response({"messages": history})

    def handle_api_ai_strategy_context(self) -> None:
        """Return aggregated analytical metrics and context for AI Strategy Coach."""
        ctx = db.get_ai_strategy_context()
        self.send_json_response(ctx)

    def handle_api_ai_strategy_clear(self) -> None:
        """Clear AI Strategy Coach conversation history."""
        db.clear_ai_strategy_interactions()
        self.send_json_response({"status": "success", "message": "Histórico do Coach Estratégico limpo com sucesso."})

    def handle_api_ai_strategy(self) -> None:
        """Generate high-level tactical coaching recommendations using Azure AI Foundry with offline fallback."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body) if content_length > 0 and body else {}
        except Exception as e:
            self.send_json_error(HTTPStatus.BAD_REQUEST, f"Malformed JSON: {e}")
            return

        user_message = payload.get("user_message", "").strip() if isinstance(payload, dict) else ""
        context = db.get_ai_strategy_context()

        # Check Azure AI credentials
        endpoint = os.environ.get("AZURE_AI_ENDPOINT", "").strip()
        api_key = os.environ.get("AZURE_AI_API_KEY", "").strip()

        # Record user query if provided
        db_user_query = user_message if user_message else "Gere um diagnóstico estratégico completo e plano tático para meu exame."
        db.record_ai_strategy_interaction(role="user", message=db_user_query)

        if not endpoint or not api_key:
            reply = self.generate_offline_strategy_report(context, user_message)
            db.record_ai_strategy_interaction(role="assistant", message=reply)
            updated_history = db.get_ai_strategy_interactions()
            self.send_json_response(
                {
                    "status": "warning",
                    "coach_response": reply,
                    "azure_configured": False,
                    "messages": updated_history,
                    "note": "Modo Estratégico Offline ativo. Configure AZURE_AI_ENDPOINT e AZURE_AI_API_KEY no .env para consultoria em tempo real.",
                }
            )
            return

        # Prepare System Prompt & Context for Azure
        system_prompt = (
            "Você é o Coach Estratégico Sênior da Escola 42 focado na aprovação do Rank 02. "
            "Seu papel é orientar o aluno taticamente para vencer o exame de 3 horas com calma, velocidade e 100% de autonomia. "
            "Você analisa métricas profundas: questões Dominadas (aprovadas sem consulta recente), Em Treinamento (onde houve consulta ou falha) "
            "e Não Iniciadas, além de padrões técnicos críticos e pontos de travamento recorrentes. "
            "Forneça diagnósticos objetivos, aponte gargalos que causam reprovação imediata na 42, recomende a ordem exata de estudo "
            "e responda às perguntas do aluno com tom encorajador, pragmático e rigoroso. Responda em português brasileiro com Markdown estruturado."
        )

        prev_interactions = db.get_ai_strategy_interactions(limit=10)
        messages = [{"role": "system", "content": system_prompt}]

        crit_pat_strs = [
            f"{p['pattern']} ({p['autonomy_rate']}% aut, {p['accuracy_rate']}% acerto)"
            for p in context.get("critical_patterns", [])
        ]
        crit_pat_joined = ", ".join(crit_pat_strs) if crit_pat_strs else "Nenhum crítico no momento"

        stuck_strs = [f"{sp[0]} ({sp[1]}x)" for sp in context.get("top_stuck_points", [])]
        stuck_joined = ", ".join(stuck_strs) if stuck_strs else "Nenhum registrado"

        training_joined = ", ".join(context.get("training_exercises", [])[:10]) or "Nenhuma"
        unattempted_joined = ", ".join(context.get("unattempted_exercises", [])[:10]) or "Todas já tentadas"

        context_summary_text = (
            f"=== Métricas do Aluno (Rank 02) ===\n"
            f"• Progresso Geral: {context['completion_percentage']}% ({context['mastered_count']}/{context['total_exercises']} dominados)\n"
            f"• Em Treinamento: {context['training_count']} | Não Iniciados: {context['unattempted_count']}\n"
            f"• Taxa de Acerto Global: {context['global_accuracy_rate']}%\n"
            f"• Tempo Médio: {context['global_avg_duration_formatted']}\n\n"
            f"• Padrões Críticos (<70% autonomia ou <75% acerto): {crit_pat_joined}\n\n"
            f"• Top Pontos de Bloqueio Recorrentes: {stuck_joined}\n\n"
            f"• Questões em Treinamento Recente: {training_joined}\n\n"
            f"• Próximas Não Iniciadas: {unattempted_joined}\n"
        )

        if len(prev_interactions) > 1:
            messages.append({"role": "user", "content": context_summary_text})
            for inter in prev_interactions[:-1]:
                messages.append({"role": inter["role"], "content": inter["message"]})
            messages.append({"role": "user", "content": db_user_query})
        else:
            messages.append({"role": "user", "content": f"{context_summary_text}\n\nPergunta do aluno: {db_user_query}"})

        request_body = {
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.4,
        }

        if any(m in endpoint.lower() for m in ["gpt-5", "o1", "o3"]):
            request_body.pop("max_tokens", None)
            request_body.pop("temperature", None)
            request_body["max_completion_tokens"] = 1800

        def send_azure_request(body: dict) -> dict:
            req_data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(endpoint, data=req_data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("api-key", api_key)
            req.add_header("Authorization", f"Bearer {api_key}")
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode("utf-8"))

        try:
            try:
                resp_json = send_azure_request(request_body)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if "max_tokens" in err_body and "max_completion_tokens" in err_body:
                    request_body.pop("max_tokens", None)
                    request_body.pop("temperature", None)
                    request_body["max_completion_tokens"] = 1800
                    resp_json = send_azure_request(request_body)
                else:
                    raise

            choices = resp_json.get("choices", [])
            reply = choices[0]["message"].get("content", "") if choices and "message" in choices[0] else "Sem resposta do modelo."

            usage = resp_json.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            cost_usd = (prompt_tokens * 0.0000025) + (completion_tokens * 0.000010)

            db.record_ai_strategy_interaction(
                role="assistant",
                message=reply,
                tokens_used=total_tokens,
                cost_usd=cost_usd,
            )

            updated_history = db.get_ai_strategy_interactions()
            self.send_json_response(
                {
                    "status": "success",
                    "coach_response": reply,
                    "azure_configured": True,
                    "messages": updated_history,
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost_usd": round(cost_usd, 5),
                    },
                }
            )

        except Exception as e:
            print(f"Azure AI Strategy Error: {e}", file=sys.stderr)
            reply = self.generate_offline_strategy_report(context, user_message)
            db.record_ai_strategy_interaction(role="assistant", message=reply)
            updated_history = db.get_ai_strategy_interactions()
            self.send_json_response(
                {
                    "status": "warning",
                    "coach_response": reply,
                    "azure_configured": False,
                    "messages": updated_history,
                    "note": f"Fallback offline ativado devido a erro na Azure: {e}",
                }
            )

    def generate_offline_strategy_report(self, context: Dict[str, Any], user_query: str = "") -> str:
        """Generate high-density tactical study guidance without requiring cloud API."""
        total = context.get("total_exercises", 55)
        mastered = context.get("mastered_count", 0)
        training = context.get("training_count", 0)
        unattempted = context.get("unattempted_count", 0)
        pct = context.get("completion_percentage", 0.0)
        acc = context.get("global_accuracy_rate", 0.0)
        avg_dur = context.get("global_avg_duration_formatted", "--:--")

        crit_pats = context.get("critical_patterns", [])
        stuck = context.get("top_stuck_points", [])
        training_exs = context.get("training_exercises", [])
        unattempted_exs = context.get("unattempted_exercises", [])

        # Readiness assessment
        if pct >= 80.0 and acc >= 85.0:
            status_badge = "🟢 **PRONTO PARA O EXAME (Alta Confiabilidade)**"
            readiness_desc = "Você atingiu a faixa de maestria sólida. Suas chances de aprovação no Rank 02 são excelentes."
        elif pct >= 50.0:
            status_badge = "🟡 **FASE DE CONSOLIDAÇÃO (Risco Moderado)**"
            readiness_desc = "Você já possui uma base sólida, mas ainda existem pontos de consulta e padrões que exigem drill para garantir velocidade sob a pressão do cronômetro da 42."
        else:
            status_badge = "🔴 **EM CONSTRUÇÃO DE BASE (Treino Intensivo Necessário)**"
            readiness_desc = "Você precisa expandir o volume de questões testadas com 100% de autonomia para evitar surpresas no sorteio de exercícios do exame."

        report = [
            f"# 🧭 Relatório Tático do Coach de Estratégia 42",
            f"",
            f"### 🎯 Nível de Prontidão: {status_badge}",
            f"{readiness_desc}",
            f"",
            f"| Métrica Global | Valor Atual | Meta para Exame Seguro |",
            f"| :--- | :--- | :--- |",
            f"| **Exercícios Dominados (100% Autônomos)** | `{mastered} / {total}` ({pct}%) | `> 40 dominados` (>75%) |",
            f"| **Em Treinamento (Precisou Ajuda / Falhou)** | `{training}` questões | `< 8 pendentes` |",
            f"| **Não Iniciados** | `{unattempted}` questões | `0 não iniciados` |",
            f"| **Taxa Global de Acerto** | `{acc}%` | `> 80%` |",
            f"| **Tempo Médio por Exercício** | `{avg_dur}` | `< 12:00` |",
            f"",
            f"---",
            f"",
            f"### ⚠️ Padrões Técnicos que Exigem Atenção Imediata",
        ]

        if crit_pats:
            for p in crit_pats[:4]:
                report.append(
                    f"- **{p['pattern']}**: Autonomia `{p['autonomy_rate']}%` | Acerto `{p['accuracy_rate']}%` "
                    f"({p['mastered_exercises']}/{p['total_exercises']} dominados). "
                    f"*Ação:* Monte uma Fila Customizada focada exclusivamente neste padrão."
                )
        else:
            report.append("- ✅ *Nenhum padrão técnico com taxa crítica no momento! Seu equilíbrio entre os 13 padrões está excelente.*")

        report.extend([
            f"",
            f"### 🧗 Principais Gargalos & Pontos de Travamento (Stuck Points)",
        ])

        if stuck:
            for sp_name, sp_count in stuck[:4]:
                report.append(f"- **{sp_name}** (esbarrou `{sp_count}x`): Pratique a sintaxe e casos de teste em folha de rascunho antes de codar no terminal.")
        else:
            report.append("- *Sem histórico de travamento registrado ainda. Registre autoavaliações pós-tentativa para refinar seu diagnóstico!*")

        report.extend([
            f"",
            f"### 📋 Plano de Fila Recomendada para a Próxima Sessão (Drill Personalizado)",
            f"Siga rigorosamente esta sequência no modo **Fila Customizada** sem abrir o Google:",
        ])

        suggested_queue = []
        if training_exs:
            suggested_queue.extend(training_exs[:3])
        if unattempted_exs:
            suggested_queue.extend(unattempted_exs[:3])

        if suggested_queue:
            for idx, ex_name in enumerate(suggested_queue, 1):
                report.append(f"{idx}. `{ex_name}` *(Foco: resolver de primeira e marcar '100% Sozinho')*")
        else:
            report.append("1. `ft_split` (Level 3 - Alocação Dinâmica)")
            report.append("2. `rostring` (Level 3 - Manipulação de Palavras)")
            report.append("3. `fprime` (Level 3 - Decomposição Numérica)")

        report.extend([
            f"",
            f"### 💡 Mindset de Prova da 42:",
            f"1. **Verificação de `argc`:** 90% dos segfaults no Level 0 e Level 1 ocorrem por acessar `argv[1]` antes de checar se `argc == 2`.",
            f"2. **Limpeza e Quebra de Linha:** Todo exercício sem parâmetros válidos pede apenas `write(1, \"\\n\", 1)`. Nunca esqueça a quebra de linha final.",
            f"3. **Regra de Ouro:** Não passe para o próximo nível no treino até conseguir escrever o exercício de ponta a ponta sem consultar nenhum código externo.",
        ])

        if user_query:
            report.extend([
                f"",
                f"> 💬 *Sobre sua pergunta ('{user_query}'):* Foque em dominar a decomposição de problemas no papel antes de abrir o editor. O cérebro precisa automatizar a lógica de avanço de ponteiro e parada em `\\0`.",
            ])

        return "\n".join(report)


    def send_json_response(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        """Send JSON response with appropriate headers."""
        encoded = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def send_json_error(self, status: HTTPStatus, message: str) -> None:
        """Send standardized error response in JSON."""
        self.send_json_response({"error": message, "status_code": int(status)}, status=status)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep console quiet unless error."""
        if len(args) > 1 and str(args[1]).startswith(("4", "5")):
            super().log_message(format, *args)


class ReusableHTTPServer(HTTPServer):
    """HTTPServer with SO_REUSEADDR enabled to prevent Address already in use on fast restarts."""
    allow_reuse_address = True


def run_server(port: int = 5000, host: str = "127.0.0.1") -> None:
    """Start the dashboard HTTP server."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    server_address = (host, port)
    try:
        httpd = ReusableHTTPServer(server_address, DashboardRequestHandler)
    except OSError as e:
        if getattr(e, "errno", None) == 98 or "already in use" in str(e).lower():
            print(f"\nℹ️  O Dashboard já está ativo e rodando na porta {port} (http://{host}:{port}/).")
            print(f"Abra seu navegador em: http://{host}:{port}/\n")
            return
        raise

    print(f"\n=======================================================")
    print(f"🚀 42 EXAMSHELL - DASHBOARD ANALÍTICO & TUTOR IA")
    print(f"📡 Servidor ativo em: http://{host}:{port}/")
    print(f"📊 Banco de dados: {STATS_DB_PATH}")
    print(f"Pressione Ctrl+C para encerrar o servidor.")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = 5000
    if len(sys.argv) > 1:
        try:
            port_arg = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port=port_arg)
