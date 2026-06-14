"""DLP pre/post hook for LiteLLM.

Loads /dlp/restricted_hr_comp.yaml at boot and applies rules to outbound model
responses. Blocks for non-CEO personas. All matches → audit event.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any

import yaml
from litellm.integrations.custom_logger import CustomLogger


class DLPHook(CustomLogger):
    def __init__(self) -> None:
        with open("/dlp/restricted_hr_comp.yaml") as f:
            cfg = yaml.safe_load(f)
        self.block_rules = [
            (r["id"], re.compile(r["pattern"])) for r in cfg["rules"]["block_for_non_ceo"]
        ]
        self.warn_rules = [
            (r["id"], re.compile(r["pattern"])) for r in cfg["rules"]["warn_log_only"]
        ]
        self.refusal = cfg["action_on_block"]["response_to_user"]

    async def async_post_call_success_hook(self, data: dict[str, Any], user_api_key_dict, response):
        persona = (data.get("metadata") or {}).get("persona", "UNKNOWN")
        text = self._extract_text(response)

        if persona != "CEO":
            for rule_id, pat in self.block_rules:
                if pat.search(text):
                    self._audit("dlp.block", persona, rule_id, text)
                    self._replace_response(response, self.refusal)
                    return response

        for rule_id, pat in self.warn_rules:
            if pat.search(text):
                self._audit("dlp.warn", persona, rule_id, text)

        return response

    @staticmethod
    def _extract_text(response) -> str:
        try:
            return response.choices[0].message.content or ""
        except Exception:
            return str(response)

    @staticmethod
    def _replace_response(response, replacement: str) -> None:
        try:
            response.choices[0].message.content = replacement
        except Exception:
            pass

    @staticmethod
    def _audit(event: str, persona: str, rule_id: str, sample: str) -> None:
        # Append to /var/log/bd-coach/dlp.jsonl; OpenObserve agent ships it.
        import json
        payload = {
            "ts": time.time(),
            "event": event,
            "persona": persona,
            "rule_id": rule_id,
            "sample_hash": hash(sample),
        }
        os.makedirs("/var/log/bd-coach", exist_ok=True)
        with open("/var/log/bd-coach/dlp.jsonl", "a") as f:
            f.write(json.dumps(payload) + "\n")
