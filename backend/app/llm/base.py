from typing import Protocol
from pydantic import BaseModel

class LocalLLM(Protocol):
    model: str
    def structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...
