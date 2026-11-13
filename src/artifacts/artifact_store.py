"""
Artifact Store for GPU Research

Manages research artifacts with SHA256 hashing, provenance tracking,
and verification status.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import hashlib
import json
import sqlite3


class ArtifactStore:
    """
    Persistent storage for research artifacts.

    Tracks:
    - File identity and location
    - SHA256 hash
    - Generation source and operation
    - Associated execution results
    - Verification status
    """

    def __init__(self, db_path: str = "artifacts.db"):
        """
        Initialize artifact store.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        """Create artifact tables if they don't exist."""
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id TEXT UNIQUE NOT NULL,
            task_id TEXT NOT NULL,
            execution_id TEXT,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            source_operation TEXT NOT NULL,
            source_tool TEXT,
            verified BOOLEAN DEFAULT 0,
            verification_result TEXT,
            metadata TEXT
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_id ON artifacts(task_id)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sha256 ON artifacts(sha256)
        """)

        self.conn.commit()

    def compute_sha256(self, file_path: Path) -> str:
        """
        Compute SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hex digest
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def register_artifact(
        self,
        artifact_id: str,
        task_id: str,
        file_path: Path,
        file_type: str,
        source_operation: str,
        source_tool: Optional[str] = None,
        execution_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a new artifact.

        Args:
            artifact_id: Unique artifact identifier
            task_id: Associated task ID
            file_path: Path to artifact file
            file_type: Type of artifact (source, binary, output, etc.)
            source_operation: Operation that created this artifact
            source_tool: Tool that created this artifact
            execution_id: Associated execution ID
            metadata: Additional metadata

        Returns:
            Artifact record
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Artifact file not found: {file_path}")

        # Compute hash
        sha256 = self.compute_sha256(file_path)
        size_bytes = file_path.stat().st_size

        # Insert record
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO artifacts (
                artifact_id, task_id, execution_id, file_path, file_type,
                sha256, size_bytes, created_at, source_operation, source_tool, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                artifact_id,
                task_id,
                execution_id,
                str(file_path),
                file_type,
                sha256,
                size_bytes,
                datetime.now().isoformat(),
                source_operation,
                source_tool,
                json.dumps(metadata) if metadata else None
            ))

            self.conn.commit()

            return {
                "artifact_id": artifact_id,
                "task_id": task_id,
                "file_path": str(file_path),
                "file_type": file_type,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "source_operation": source_operation
            }

        except sqlite3.IntegrityError:
            # Artifact already exists
            cursor.execute("""
            SELECT * FROM artifacts WHERE artifact_id = ?
            """, (artifact_id,))

            row = cursor.fetchone()
            if row:
                return {
                    "artifact_id": row[1],
                    "task_id": row[2],
                    "file_path": row[4],
                    "sha256": row[6],
                    "status": "already_exists"
                }

            raise

    def verify_artifact(
        self,
        artifact_id: str,
        verification_result: str,
        verified: bool = True
    ):
        """
        Mark artifact as verified.

        Args:
            artifact_id: Artifact to verify
            verification_result: Verification outcome
            verified: Whether verification passed
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        UPDATE artifacts
        SET verified = ?, verification_result = ?
        WHERE artifact_id = ?
        """, (verified, verification_result, artifact_id))

        self.conn.commit()

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve artifact by ID.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Artifact record or None
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT * FROM artifacts WHERE artifact_id = ?
        """, (artifact_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "artifact_id": row[1],
            "task_id": row[2],
            "execution_id": row[3],
            "file_path": row[4],
            "file_type": row[5],
            "sha256": row[6],
            "size_bytes": row[7],
            "created_at": row[8],
            "source_operation": row[9],
            "source_tool": row[10],
            "verified": bool(row[11]),
            "verification_result": row[12],
            "metadata": json.loads(row[13]) if row[13] else None
        }

    def list_task_artifacts(self, task_id: str) -> List[Dict[str, Any]]:
        """
        List all artifacts for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of artifact records
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT * FROM artifacts WHERE task_id = ? ORDER BY created_at
        """, (task_id,))

        artifacts = []
        for row in cursor.fetchall():
            artifacts.append({
                "artifact_id": row[1],
                "file_path": row[4],
                "file_type": row[5],
                "sha256": row[6],
                "size_bytes": row[7],
                "source_operation": row[9],
                "verified": bool(row[11])
            })

        return artifacts

    def verify_integrity(self, artifact_id: str) -> bool:
        """
        Verify artifact integrity by recomputing hash.

        Args:
            artifact_id: Artifact to verify

        Returns:
            True if hash matches, False otherwise
        """
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return False

        file_path = Path(artifact['file_path'])
        if not file_path.exists():
            return False

        current_hash = self.compute_sha256(file_path)
        return current_hash == artifact['sha256']

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
