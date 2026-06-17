"""AgentBase Memory integration for Contract Guardian."""

import json
import os
from typing import Optional


class MemoryClient:
    """Lightweight memory client for semantic fact extraction."""

    def __init__(self, memory_id: Optional[str] = None, actor_id: str = "contract-analyst"):
        self.memory_id = memory_id or os.getenv("AGENTBASE_MEMORY_ID", "default")
        self.actor_id = actor_id
        self.session_id = None
        self.events = []

    def start_session(self, session_id: str):
        """Start a new conversation session."""
        self.session_id = session_id
        self.events = []

    def add_event(self, role: str, content: str):
        """Add conversation turn to session."""
        if not self.session_id:
            return
        self.events.append({"role": role, "content": content})

    def get_session_events(self) -> list:
        """Return current session events."""
        return self.events

    def extract_contract_patterns(self) -> dict:
        """Extract semantic patterns from contract analysis."""
        if not self.events:
            return {}
        
        patterns = {
            "total_conversations": len([e for e in self.events if e["role"] == "user"]),
            "common_risks": [],
            "compliance_status": "unknown",
            "negotiation_topics": [],
        }
        
        for event in self.events:
            if "risk" in event["content"].lower():
                patterns["common_risks"].append(event["content"][:100])
            if "compliance" in event["content"].lower():
                patterns["compliance_status"] = "reviewed"
            if "negotiate" in event["content"].lower() or "đàm phán" in event["content"].lower():
                patterns["negotiation_topics"].append(event["content"][:100])
        
        return patterns

    def store_memory_record(self, fact: dict):
        """Store extracted fact as memory record (for future AgentBase integration)."""
        return {
            "namespace": f"/strategies/contract/actors/{self.actor_id}",
            "fact": fact,
            "timestamp": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
        }


_memory = MemoryClient()


def get_memory_client() -> MemoryClient:
    """Get global memory client instance."""
    return _memory


def init_session(session_id: str):
    """Initialize memory for new contract session."""
    _memory.start_session(session_id)
