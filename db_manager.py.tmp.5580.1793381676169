import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "assessment_engine.db"):
        self.db_path = db_path
        self._init_db()

    def get_connection(self):
        """Returns a connection with WAL mode enabled for better concurrency."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes the database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Concept Families Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS concept_families (
                    family_id TEXT PRIMARY KEY,
                    section TEXT NOT NULL,
                    sub_topic TEXT NOT NULL,
                    structural_schema TEXT
                )
            ''')
            
            # Items Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    family_id TEXT,
                    stem TEXT NOT NULL,
                    options TEXT NOT NULL, -- JSON array
                    correct_answer TEXT NOT NULL,
                    empirical_p_value REAL,
                    irt_difficulty_b REAL,
                    irt_discrimination_a REAL,
                    point_biserial REAL,
                    approval_status TEXT DEFAULT 'DRAFT', -- DRAFT, APPROVED, REJECTED
                    is_quarantined BOOLEAN DEFAULT 0,
                    vector_embedding BLOB, -- Serialized numpy array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(family_id) REFERENCES concept_families(family_id)
                )
            ''')
            
            # Response Logs Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS response_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_source TEXT NOT NULL, -- e.g., IMAP_BASELINE, PILOT, SLOT_1
                    candidate_id TEXT NOT NULL,
                    slot_id INTEGER,
                    item_id TEXT NOT NULL,
                    is_correct BOOLEAN NOT NULL,
                    response_time_sec REAL,
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(item_id) REFERENCES items(item_id)
                )
            ''')
            
            # Slot Forms Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS slot_forms (
                    form_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(item_id) REFERENCES items(item_id),
                    UNIQUE(slot_id, item_id)
                )
            ''')
            
            # Leak Alerts Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leak_alerts (
                    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL, -- CUSUM, OSINT
                    item_id TEXT NOT NULL,
                    evidence_payload TEXT, -- JSON details
                    hot_swap_item_id TEXT, -- Replacement item
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(item_id) REFERENCES items(item_id)
                )
            ''')
            
            # Red Team Runs Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS red_team_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    round INTEGER NOT NULL DEFAULT 0,
                    accuracy_blind REAL,
                    accuracy_armed REAL,
                    leak_advantage REAL,
                    copy_rate REAL,
                    status TEXT NOT NULL, -- PASSED, REGENERATED, STILL_VULNERABLE
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Candidate Responses Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    selected TEXT NOT NULL,
                    slot_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(candidate_id, item_id)
                )
            ''')

            # Migration: regenerated items keep a link to their parent item.
            item_columns = [row[1] for row in cursor.execute("PRAGMA table_info(items)").fetchall()]
            if "parent_item_id" not in item_columns:
                cursor.execute("ALTER TABLE items ADD COLUMN parent_item_id TEXT")
            
            conn.commit()
            logger.info("Database schema initialized successfully.")

    # Utility functions for basic operations
    def insert_concept_family(self, family_id: str, section: str, sub_topic: str, structural_schema: str = ""):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO concept_families (family_id, section, sub_topic, structural_schema)
                VALUES (?, ?, ?, ?)
            ''', (family_id, section, sub_topic, structural_schema))
            conn.commit()

    def insert_item(self, item_data: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO items (
                    item_id, family_id, stem, options, correct_answer, 
                    empirical_p_value, irt_difficulty_b, irt_discrimination_a, 
                    point_biserial, approval_status, is_quarantined, parent_item_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_data.get('item_id'), item_data.get('family_id'), item_data.get('stem'),
                json.dumps(item_data.get('options', [])), item_data.get('correct_answer'),
                item_data.get('empirical_p_value'), item_data.get('irt_difficulty_b'),
                item_data.get('irt_discrimination_a'), item_data.get('point_biserial'),
                item_data.get('approval_status', 'DRAFT'), item_data.get('is_quarantined', False),
                item_data.get('parent_item_id')
            ))
            conn.commit()

    # --- Red Team Loop ---------------------------------------------------

    RED_TEAM_STATUSES = ("PASSED", "REGENERATED", "STILL_VULNERABLE")

    def save_red_team_run(self, slot_id: int, item_id: str, round: int,
                          accuracy_blind: float, accuracy_armed: float,
                          leak_advantage: float, copy_rate: float, status: str):
        if status not in self.RED_TEAM_STATUSES:
            raise ValueError(f"Unknown red-team status: {status}")
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO red_team_runs (
                    slot_id, item_id, round, accuracy_blind, accuracy_armed,
                    leak_advantage, copy_rate, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (slot_id, item_id, round, accuracy_blind, accuracy_armed,
                  leak_advantage, copy_rate, status))
            conn.commit()

    def get_red_team_runs(self, slot_id: Optional[int] = None,
                          item_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM red_team_runs"
        clauses, params = [], []
        if slot_id is not None:
            clauses.append("slot_id = ?")
            params.append(slot_id)
        if item_id is not None:
            clauses.append("item_id = ?")
            params.append(item_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id ASC"
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def update_item_approval(self, item_id: str, status: str):
        if status not in ("DRAFT", "APPROVED", "REJECTED"):
            raise ValueError(f"Unknown approval status: {status}")
        with self.get_connection() as conn:
            conn.execute("UPDATE items SET approval_status = ? WHERE item_id = ?", (status, item_id))
            conn.commit()

    def get_item_approval(self, item_id: str) -> Optional[str]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT approval_status FROM items WHERE item_id = ?", (item_id,)).fetchone()
        return row["approval_status"] if row else None

    def item_exists(self, item_id: str) -> bool:
        with self.get_connection() as conn:
            row = conn.execute("SELECT 1 FROM items WHERE item_id = ? LIMIT 1", (item_id,)).fetchone()
        return row is not None

    def bulk_set_answers(self, pairs: List[tuple]) -> int:
        """Backfill correct answers. pairs is [(item_id, option_letter), ...]."""
        if not pairs:
            return 0
        with self.get_connection() as conn:
            cursor = conn.executemany(
                "UPDATE items SET correct_answer = ? WHERE item_id = ?",
                [(answer, item_id) for item_id, answer in pairs],
            )
            conn.commit()
        return cursor.rowcount or 0

    def answer_key_coverage(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            row = conn.execute('''
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN correct_answer IS NULL
                                  OR correct_answer IN ('', 'N/A') THEN 0 ELSE 1 END) AS keyed
                FROM items
            ''').fetchone()
        return {"keyed": row["keyed"] or 0, "total": row["total"] or 0}

    def save_responses(self, rows: List[tuple]) -> int:
        """rows is [(candidate_id, item_id, selected, slot_id), ...]; re-uploads replace."""
        if not rows:
            return 0
        with self.get_connection() as conn:
            cursor = conn.executemany('''
                INSERT OR REPLACE INTO responses (candidate_id, item_id, selected, slot_id)
                VALUES (?, ?, ?, ?)
            ''', rows)
            conn.commit()
        return cursor.rowcount or 0

    def get_responses(self, slot_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT candidate_id, item_id, selected, slot_id FROM responses"
        params: List[Any] = []
        if slot_id is not None:
            query += " WHERE slot_id = ?"
            params.append(slot_id)
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_items_by_ids(self, item_ids) -> List[Dict[str, Any]]:
        if not item_ids:
            return []
        ids = list(dict.fromkeys(item_ids))
        results: List[Dict[str, Any]] = []
        with self.get_connection() as conn:
            for start in range(0, len(ids), 900):
                chunk = ids[start:start + 900]
                placeholders = ",".join("?" * len(chunk))
                rows = conn.execute(
                    f"SELECT item_id, stem, options, correct_answer FROM items WHERE item_id IN ({placeholders})",
                    chunk,
                ).fetchall()
                results.extend(dict(row) for row in rows)
        return results



