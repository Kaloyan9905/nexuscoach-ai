"""LLM Coaching Synthesizer: calls LLM API or uses deterministic fallback generator."""

import json
import os
from typing import Any, Dict, Optional
import requests

from nexuscoach.llm.normalizer import normalize_coaching_context
from nexuscoach.llm.prompt import SYSTEM_PROMPT, build_user_prompt

class CoachingSynthesizer:
    """Generates the final 3-point coaching takeaway using LLM or offline fallback."""

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = (gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()

    def generate_review(self, analysis_data: Dict[str, Any]) -> str:
        """Synthesize coaching feedback from analysis data."""
        manifest_json = normalize_coaching_context(analysis_data)

        if self.api_key:
            try:
                return self._call_gemini_api(manifest_json)
            except Exception as e:
                # Graceful fallback to offline rule synthesis if API call fails
                offline_output = self._offline_fallback_synthesizer(analysis_data)
                return f"{offline_output}\n\n*(Забележка: LLM API грешка: {str(e)} - генериран детерминистичен анализ)*"
        else:
            return self._offline_fallback_synthesizer(analysis_data)

    def _call_gemini_api(self, manifest_json: str) -> str:
        """Call Gemini Flash API directly with zero extra SDK dependencies."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        prompt = build_user_prompt(manifest_json)

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("No candidate response received from Gemini.")

        return candidates[0]["content"]["parts"][0]["text"].strip()

    def _offline_fallback_synthesizer(self, analysis_data: Dict[str, Any]) -> str:
        """Deterministic rule-based Challenger synthesis for offline/zero-API execution."""
        meta = analysis_data.get("metadata", {})
        anomalies = analysis_data.get("top_anomalies", [])[:3]

        lines = [
            f"### 🛡️ NexusCoach Review: {meta.get('userChampion')} vs {meta.get('opponentChampion')} ({meta.get('result')} - {meta.get('duration')})",
            f"**КДА:** {meta.get('kda')} | **CS/min:** {meta.get('cs_per_min')} | **Линия:** {meta.get('role')}",
            "",
            "---",
            "#### ❌ Топ 3 грешки, които определиха изхода на играта:",
            ""
        ]

        if not anomalies:
            lines.append("Няма засечени критични макро грешки. Отлична дисциплина в линията и контрола на обективите!")
            return "\n".join(lines)

        for i, a in enumerate(anomalies, 1):
            ts = a.get("timestamp", "00:00")
            a_type = a.get("type")

            if a_type == "DEATH_ANALYSIS":
                killer = a.get("killer", "Enemy")
                eng = a.get("engagement_type", "Kill")
                vision_str = "без активен съюзен вард" if not a.get("had_vision") else "въпреки наличието на вард"
                flash_str = "с наличен Flash" if a.get("flash_available") else "без наличен Flash"
                plates = a.get("plates_lost_after", 0)

                lines.append(f"{i}. **[{ts}] Смърт от {eng} ({vision_str} & {flash_str})**")
                lines.append(f"   * *Какво се случи:* Умираш в зона {a.get('zone')} от {killer}. Липсва визия за предпазване от ганк.")
                lines.append(f"   * *Цената:* Загуба на контрол над линията и {plates} turret plates за противниковия отбор.")
                lines.append(f"   * *Подобрение:* Позиционирай се към варднатата страна на реката. Ако си изненадан в гръб, използвай Flash незабавно преди влизане на CC веригата.")
            elif a_type == "GOLD_HOARDING":
                gold = a.get("held_gold", 0)
                dur = a.get("duration_seconds", 0)
                lines.append(f"{i}. **[{ts}] Задържане на злато (Gold Hoarding: {gold}g за {dur}s)**")
                lines.append(f"   * *Какво се случи:* Задържаш над {gold} непохарчено злато за над {dur // 60} минути без Recall за предмети.")
                lines.append(f"   * *Цената:* Играеш с огромно изоставане в бойни стакове и отстъпваш темпото на опонент с готов предмет.")
                lines.append(f"   * *Подобрение:* Планирай Recall при Cannon wave, веднага щом достигнеш злато за ключов компонент (Lost Chapter, B.F. Sword, Noonquiver).")
            elif a_type == "FAILED_ROAM":
                plates = a.get("plates_lost", 0)
                lines.append(f"{i}. **[{ts}] Роум с отрицателна стойност (Failed Roam)**")
                lines.append(f"   * *Какво се случи:* Напускаш линията за продължителен период, без да осъществиш убийство или асистенция.")
                lines.append(f"   * *Цената:* Противникът взима свободен CS приоритет и {plates} turret plates на твоята кула.")
                lines.append(f"   * *Подобрение:* Роумвай само след като избуташ напълно вълната под противниковата кула (Wave Crash) или при 100% сигурен kill setup.")
            elif a_type == "OBJECTIVE_DESYNC":
                obj = a.get("objective", "Objective")
                dist = a.get("distance_to_pit", 0)
                lines.append(f"{i}. **[{ts}] Отсъствие от битка за {obj} (Objective Desync)**")
                lines.append(f"   * *Какво се случи:* Намираш се на {dist} единици от ямата на {obj} точно по време на появата и битката.")
                lines.append(f"   * *Цената:* Отборът ти остава в числено малцинство и губи епичния обектив.")
                lines.append(f"   * *Подобрение:* Синхронизирай придвижването си 45 секунди преди обектива. Ако нямаш Teleport, не оставай на противоположната страна на картата.")
            elif a_type == "LEVEL_DEFICIT":
                gap = a.get("level_gap", 1)
                lines.append(f"{i}. **[{ts}] Изоставане с {gap} нива спрямо противниковия лейнър**")
                lines.append(f"   * *Какво се случи:* Противникът те изпреварва с цяло ниво по време на ранната фаза на линията.")
                lines.append(f"   * *Цената:* Противникът отключва ключови умения и Ultimate по-рано, създавайки зона за агресивен all-in.")
                lines.append(f"   * *Подобрение:* Не губи XP радиуса на умиращите миньони, дори когато си притиснат под кулата.")
            lines.append("")

        return "\n".join(lines)
