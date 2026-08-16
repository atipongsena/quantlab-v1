from collections.abc import Sequence
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from quantlab.common.hashing import canonical_hash


@dataclass(frozen=True, slots=True)
class DeterministicIdFactory:
    root_namespace: UUID = NAMESPACE_URL

    def from_parts(self, namespace: str, parts: Sequence[str]) -> str:
        if not namespace:
            raise ValueError("namespace must be nonempty")
        if not parts:
            raise ValueError("parts must be nonempty")
        payload_hash = canonical_hash({"namespace": namespace, "parts": tuple(parts)})
        return str(uuid5(self.root_namespace, payload_hash))
