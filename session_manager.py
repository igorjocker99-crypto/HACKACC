import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, sessions_dir: str = "sessions/valid", data_dir: str = "data"):
        self.sessions_dir = sessions_dir
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "db.json")
        os.makedirs(sessions_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        self.db = self._load_db()

    def _load_db(self) -> Dict:
        if os.path.exists(self.db_path):
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"sessions": {}, "stats": {"total": 0, "valid": 0, "invalid": 0}}

    def _save_db(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.db, f, indent=2, ensure_ascii=False)

    def save_session(self, phone: str, session_string: str) -> bool:
        try:
            filename = f"session_{phone.replace('+', '')}.session"
            filepath = os.path.join(self.sessions_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(session_string)
            self.db["sessions"][phone] = {
                "phone": phone,
                "file": filename,
                "created_at": "2026-08-05",
                "valid": True
            }
            self.db["stats"]["total"] = len(self.db["sessions"])
            self.db["stats"]["valid"] = sum(1 for s in self.db["sessions"].values() if s.get("valid", False))
            self._save_db()
            logger.info(f"Session saved: {phone}")
            return True
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False

    def get_valid_sessions(self) -> List[Dict]:
        return [{"phone": p, "file": d.get("file", ""), "created_at": d.get("created_at", "")}
                for p, d in self.db["sessions"].items() if d.get("valid", False)]

    def get_stats(self) -> Dict:
        return self.db.get("stats", {"total": 0, "valid": 0, "invalid": 0})

    def get_session_file(self, phone: str) -> Optional[str]:
        data = self.db["sessions"].get(phone)
        if not data or not data.get("valid", False):
            return None
        filepath = os.path.join(self.sessions_dir, data.get("file", ""))
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()