"""
通用输入生成与变异引擎

支持字节级变异、长度变异、边界变异
记录父样本、变异操作、种子信息
"""

import hashlib
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MutationRecord:
    """变异记录"""
    input_sha256: str
    parent_sha256: str
    mutation_type: str  # "bit_flip", "byte_flip", "insert", "delete", "truncate", "extend"
    operation_details: str
    seed: int
    timestamp: str


class InputMutationEngine:
    """
    通用输入变异引擎

    允许生成畸形、无效、边界输入
    不强制格式检查
    """

    def __init__(self, seed_file: Path, workspace: Path):
        """
        初始化引擎

        Args:
            seed_file: 初始种子文件
            workspace: 输出工作目录
        """
        self.seed_file = seed_file
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.candidates_dir = self.workspace / "candidates"
        self.candidates_dir.mkdir(exist_ok=True)

        # 读取种子
        self.seed_data = seed_file.read_bytes()
        self.seed_sha256 = hashlib.sha256(self.seed_data).hexdigest()
        self.mutations = []

    def _generate_candidate(
        self,
        data: bytes,
        mutation_type: str,
        details: str,
        seed: int
    ) -> Tuple[Path, MutationRecord]:
        """生成一个候选输入"""
        candidate_sha256 = hashlib.sha256(data).hexdigest()
        candidate_file = self.candidates_dir / f"{candidate_sha256[:8]}.bin"

        if not candidate_file.exists():
            candidate_file.write_bytes(data)

        record = MutationRecord(
            input_sha256=candidate_sha256,
            parent_sha256=self.seed_sha256,
            mutation_type=mutation_type,
            operation_details=details,
            seed=seed,
            timestamp=datetime.now().isoformat()
        )

        self.mutations.append(record)
        return candidate_file, record

    def bit_flip(self, count: int = 5, random_seed: int = 42) -> List[Tuple[Path, MutationRecord]]:
        """随机位翻转"""
        random.seed(random_seed)
        candidates = []

        for i in range(count):
            data = bytearray(self.seed_data)
            byte_idx = random.randint(0, len(data) - 1)
            bit_idx = random.randint(0, 7)
            data[byte_idx] ^= (1 << bit_idx)

            candidate, record = self._generate_candidate(
                bytes(data),
                "bit_flip",
                f"byte[{byte_idx}] bit[{bit_idx}] flipped",
                random_seed + i
            )
            candidates.append((candidate, record))

        return candidates

    def byte_flip(self, count: int = 5, random_seed: int = 42) -> List[Tuple[Path, MutationRecord]]:
        """随机字节翻转"""
        random.seed(random_seed)
        candidates = []

        for i in range(count):
            data = bytearray(self.seed_data)
            idx = random.randint(0, len(data) - 1)
            data[idx] ^= 0xFF

            candidate, record = self._generate_candidate(
                bytes(data),
                "byte_flip",
                f"byte[{idx}] flipped",
                random_seed + i
            )
            candidates.append((candidate, record))

        return candidates

    def truncate(self, count: int = 5, random_seed: int = 42) -> List[Tuple[Path, MutationRecord]]:
        """截断变异"""
        random.seed(random_seed)
        candidates = []

        for i in range(count):
            length = random.randint(1, len(self.seed_data) - 1)
            data = self.seed_data[:length]

            candidate, record = self._generate_candidate(
                data,
                "truncate",
                f"truncated to {length} bytes",
                random_seed + i
            )
            candidates.append((candidate, record))

        return candidates

    def extend(self, count: int = 5, max_size: int = None, random_seed: int = 42) -> List[Tuple[Path, MutationRecord]]:
        """扩展变异"""
        random.seed(random_seed)
        candidates = []

        if max_size is None:
            max_size = len(self.seed_data) * 2

        for i in range(count):
            added = random.randint(1, max_size - len(self.seed_data))
            extra = bytes([random.randint(0, 255) for _ in range(added)])
            data = self.seed_data + extra

            candidate, record = self._generate_candidate(
                data,
                "extend",
                f"extended by {added} random bytes",
                random_seed + i
            )
            candidates.append((candidate, record))

        return candidates

    def boundary(self, count: int = 5) -> List[Tuple[Path, MutationRecord]]:
        """边界值变异（常见出错位置）"""
        candidates = []

        # 长度为 0
        candidate, record = self._generate_candidate(
            b"",
            "boundary",
            "empty file (length 0)",
            0
        )
        candidates.append((candidate, record))

        # 长度为 1
        if len(self.seed_data) > 0:
            candidate, record = self._generate_candidate(
                self.seed_data[:1],
                "boundary",
                "minimal file (length 1)",
                1
            )
            candidates.append((candidate, record))

        # 所有字节为 0x00
        candidate, record = self._generate_candidate(
            b'\x00' * len(self.seed_data),
            "boundary",
            "all zeros",
            2
        )
        candidates.append((candidate, record))

        # 所有字节为 0xFF
        candidate, record = self._generate_candidate(
            b'\xFF' * len(self.seed_data),
            "boundary",
            "all ones",
            3
        )
        candidates.append((candidate, record))

        return candidates[:count]

    def get_mutation_log(self) -> List[Dict[str, Any]]:
        """获取变异日志"""
        return [
            {
                "input_sha256": m.input_sha256,
                "parent_sha256": m.parent_sha256,
                "mutation_type": m.mutation_type,
                "operation_details": m.operation_details,
                "seed": m.seed,
                "timestamp": m.timestamp
            }
            for m in self.mutations
        ]
