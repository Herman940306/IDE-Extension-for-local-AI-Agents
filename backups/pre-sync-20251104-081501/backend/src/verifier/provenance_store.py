"""
Provenance Store for immutable audit logs
Project Creator: Herman Swanepoel
"""

import base64
import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class ProvenanceStore:
    """
    Immutable audit logs for all AI inferences.

    Provides complete transparency and traceability for all AI decisions
    with optional encryption for sensitive data.
    """

    def __init__(
        self,
        db_path: str = "./data/provenance.db",
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize provenance store.

        Args:
            db_path: Path to SQLite database
            encryption_key: Optional encryption key for sensitive data
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize encryption if key provided
        self.cipher = None
        if encryption_key:
            key = base64.urlsafe_b64encode(encryption_key.encode().ljust(32)[:32])
            self.cipher = Fernet(key)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

        logger.info(f"ProvenanceStore initialized at {self.db_path}")

    def _create_tables(self) -> None:
        """Create database tables"""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS provenance (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                task_type TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                output_hash TEXT NOT NULL,
                confidence REAL NOT NULL,
                metadata TEXT,
                trace_id TEXT,
                encrypted INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_agent ON provenance(agent)
        """
        )

        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp ON provenance(timestamp)
        """
        )

        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trace_id ON provenance(trace_id)
        """
        )

        self.conn.commit()

    def log(
        self,
        agent: str,
        task_type: str,
        input_data: str,
        output_data: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        encrypt: bool = False,
    ) -> str:
        """
        Log inference with provenance.

        Args:
            agent: Agent name
            task_type: Type of task
            input_data: Input data (will be hashed)
            output_data: Output data (will be hashed)
            confidence: Confidence score
            metadata: Additional metadata
            trace_id: Optional trace ID for linking
            encrypt: Whether to encrypt metadata

        Returns:
            Log entry ID
        """
        # Generate unique ID
        log_id = hashlib.sha256(
            f"{agent}{task_type}{input_data}{datetime.utcnow()}".encode()
        ).hexdigest()

        # Hash input and output
        input_hash = hashlib.sha256(input_data.encode()).hexdigest()
        output_hash = hashlib.sha256(output_data.encode()).hexdigest()

        # Prepare metadata
        metadata_str = json.dumps(metadata or {})
        if encrypt and self.cipher:
            metadata_str = self.cipher.encrypt(metadata_str.encode()).decode()

        # Insert into database
        try:
            self.conn.execute(
                """
                INSERT INTO provenance
                (id, timestamp, agent, task_type, input_hash, output_hash,
                 confidence, metadata, trace_id, encrypted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    log_id,
                    datetime.utcnow().isoformat(),
                    agent,
                    task_type,
                    input_hash,
                    output_hash,
                    confidence,
                    metadata_str,
                    trace_id,
                    1 if encrypt else 0,
                ),
            )
            self.conn.commit()

            logger.debug(f"Logged provenance: {log_id}")
            return log_id
        except Exception as e:
            logger.error(f"Failed to log provenance: {e}")
            raise

    def get_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Get provenance entry by ID.

        Args:
            log_id: Log entry ID

        Returns:
            Provenance entry dict or None
        """
        try:
            cursor = self.conn.execute(
                "SELECT * FROM provenance WHERE id = ?", (log_id,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get provenance {log_id}: {e}")
            return None

    def get_by_agent(
        self, agent: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get provenance entries by agent.

        Args:
            agent: Agent name
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            List of provenance entries
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT * FROM provenance
                WHERE agent = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """,
                (agent, limit, offset),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get provenance for {agent}: {e}")
            return []

    def get_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Get all provenance entries for a trace.

        Args:
            trace_id: Trace ID

        Returns:
            List of provenance entries
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT * FROM provenance
                WHERE trace_id = ?
                ORDER BY timestamp ASC
            """,
                (trace_id,),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get provenance for trace {trace_id}: {e}")
            return []

    def search(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        agent: Optional[str] = None,
        task_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search provenance entries with filters.

        Args:
            start_time: Start timestamp (ISO format)
            end_time: End timestamp (ISO format)
            agent: Filter by agent
            task_type: Filter by task type
            min_confidence: Minimum confidence score
            limit: Maximum results

        Returns:
            List of matching provenance entries
        """
        query = "SELECT * FROM provenance WHERE 1=1"
        params: List[Any] = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        if agent:
            query += " AND agent = ?"
            params.append(agent)

        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)

        if min_confidence is not None:
            query += " AND confidence >= ?"
            params.append(min_confidence)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor = self.conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get provenance statistics.

        Returns:
            Dict containing statistics
        """
        try:
            # Total entries
            total = self.conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]

            # By agent
            agent_stats = {}
            cursor = self.conn.execute(
                """
                SELECT agent, COUNT(*) as count, AVG(confidence) as avg_conf
                FROM provenance
                GROUP BY agent
            """
            )
            for row in cursor:
                agent_stats[row[0]] = {"count": row[1], "avg_confidence": row[2]}

            # By task type
            task_stats = {}
            cursor = self.conn.execute(
                """
                SELECT task_type, COUNT(*) as count
                FROM provenance
                GROUP BY task_type
            """
            )
            for row in cursor:
                task_stats[row[0]] = row[1]

            return {
                "total_entries": total,
                "by_agent": agent_stats,
                "by_task_type": task_stats,
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to dict"""
        result = dict(row)

        # Decrypt metadata if encrypted
        if result.get("encrypted") and self.cipher:
            try:
                encrypted_metadata = result["metadata"]
                decrypted = self.cipher.decrypt(encrypted_metadata.encode())
                result["metadata"] = json.loads(decrypted.decode())
            except Exception as e:
                logger.error(f"Failed to decrypt metadata: {e}")
                result["metadata"] = {}
        else:
            try:
                result["metadata"] = json.loads(result["metadata"])
            except (json.JSONDecodeError, TypeError):
                result["metadata"] = {}

        return result

    def export_audit_report(
        self,
        output_path: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> bool:
        """
        Export audit report to JSON file.

        Args:
            output_path: Output file path
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            True if successful
        """
        try:
            entries = self.search(start_time=start_time, end_time=end_time, limit=10000)

            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "period": {"start": start_time, "end": end_time},
                "total_entries": len(entries),
                "entries": entries,
            }

            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)

            logger.info(f"Exported audit report to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            return False

    def close(self) -> None:
        """Close database connection"""
        try:
            self.conn.close()
            logger.info("Closed provenance store connection")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
