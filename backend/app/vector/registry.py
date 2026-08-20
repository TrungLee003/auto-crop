from typing import Dict, List, Optional
from .base import Vectorizer
from .potrace import PotraceVectorizer
from .vtracer import VTracerVectorizer


class VectorizerRegistry:
    def __init__(self):
        self._vectorizers: Dict[str, Vectorizer] = {}
        # Pre-register built-in vectorizer providers
        self.register("vtracer", VTracerVectorizer())
        self.register("potrace", PotraceVectorizer())

    def register(self, name: str, vectorizer: Vectorizer):
        self._vectorizers[name] = vectorizer

    def get(self, name: str = "vtracer") -> Optional[Vectorizer]:
        return self._vectorizers.get(name)

    def list_providers(self) -> List[str]:
        return list(self._vectorizers.keys())


# Global singleton instance
vectorizer_registry = VectorizerRegistry()

