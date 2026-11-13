#!/usr/bin/env python
"""
Migrate legacy root-level artifacts to workspace structure.
Creates run directories with proper structure and hash verification.
"""

import shutil
import hashlib
from pathlib import Path
from datetime import datetime
import json

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE = PROJECT_ROOT / "workspace"
LEGACY_DIR = WORKSPACE / "legacy"

# File manifest for migration
MIGRATION_MANIFEST = {
    "m1_verification": {
        "task_id": "m1_regression",
        "run_id": "legacy_validation_001",
        "files": [
            ("validation_result_m1.json", "inputs"),
            ("validation_result_m1_historical.json", "inputs"),
        ]
    },
    "m2_checkpoints": {
        "task_id": "m2_cross_process",
        "run_id": "legacy_checkpoint_001",
        "files": [
            ("cross_process_checkpoints.db", "state"),
            ("process1_metadata.json", "logs"),
            ("interrupt_process1_metadata.json", "logs"),
        ]
    },
    "vector_add_tests": {
        "task_id": "cuda_basic_test",
        "run_id": "legacy_vector_add",
        "files": [
            ("vector_add.cu", "source"),
            ("vector_add.exe", "build"),
            ("vector_add_verify.cu", "source"),
            ("vector_add_verify.exe", "build"),
            ("vector_add_sweep.cu", "source"),
            ("vector_add_sweep.exe", "build"),
        ]
    },
    "controlled_interrupt": {
        "task_id": "m2_controlled_interrupt",
        "run_id": "legacy_interrupt_001",
        "files": [
            ("interrupt_controlled.db", "state"),
            ("interrupt_controlled_metadata.json", "logs"),
            ("interrupt_resume_checkpoints.db", "state"),
            ("m2_controlled_interrupt.log", "logs"),
        ]
    },
}

def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def migrate_files():
    """Migrate legacy files to workspace structure."""

    print("=" * 70)
    print("LEGACY FILE MIGRATION")
    print("=" * 70)

    migration_log = {
        "timestamp": datetime.now().isoformat(),
        "migrations": []
    }

    for category, info in MIGRATION_MANIFEST.items():
        task_id = info["task_id"]
        run_id = info["run_id"]
        run_dir = WORKSPACE / "runs" / task_id / run_id

        print(f"\n[{category}]")
        print(f"  Task: {task_id}")
        print(f"  Run: {run_id}")

        for old_file, sub_dir in info["files"]:
            old_path = PROJECT_ROOT / old_file

            if not old_path.exists():
                print(f"  SKIP: {old_file} (not found)")
                continue

            # Create destination
            new_sub_dir = run_dir / sub_dir
            new_sub_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_sub_dir / old_file

            # Compute hash before migration
            old_hash = compute_sha256(old_path)

            # Copy file
            shutil.copy2(old_path, new_path)

            # Verify hash
            new_hash = compute_sha256(new_path)

            if old_hash == new_hash:
                print(f"  OK: {old_file} -> {sub_dir}/")
                print(f"      SHA256: {old_hash[:16]}...")

                migration_log["migrations"].append({
                    "file": old_file,
                    "old_path": str(old_path),
                    "new_path": str(new_path),
                    "sha256": old_hash,
                    "status": "migrated"
                })
            else:
                print(f"  FAIL: {old_file} - hash mismatch!")
                migration_log["migrations"].append({
                    "file": old_file,
                    "status": "failed",
                    "error": "hash_mismatch"
                })

    # Save migration log
    log_path = WORKSPACE / "state" / "migration.log"
    log_path.write_text(json.dumps(migration_log, indent=2))

    print("\n" + "=" * 70)
    print(f"Migration log saved: {log_path}")
    print("=" * 70)

    return migration_log

if __name__ == "__main__":
    migrate_files()
