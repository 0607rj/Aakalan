"""LLMClient interface and implementations (architecture rule 9: the provider is a config
change). LLMs only read and suggest — nothing here ever computes a cost (rule 1)."""

import base64
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from pydantic import BaseModel

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from anthropic.types.beta import BetaOutputConfigParam

PROMPTS_DIR = Path(__file__).parent / "prompts"
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMNotConfiguredError(RuntimeError):
    """No API key / provider configured."""


class LLMRefusedError(RuntimeError):
    """The model declined the request (after any server-side fallback)."""


@dataclass(frozen=True)
class LLMResult[T: BaseModel]:
    output: T
    model: str
    input_tokens: int
    output_tokens: int


class LLMClient(Protocol):
    def extract[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        """One structured-output call; the reply is validated against `schema`."""
        ...

    def extract_pdf[T: BaseModel](
        self, *, system: str, pdf: bytes, instruction: str, schema: type[T]
    ) -> LLMResult[T]:
        """Same, reading a PDF directly (scanned documents)."""
        ...


def load_prompt(name: str) -> str:
    """Prompts are versioned files under app/llm/prompts/ (brief Section 9)."""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


class AnthropicClient:
    def __init__(self, settings: Settings) -> None:
        import anthropic

        if not settings.anthropic_api_key:
            raise LLMNotConfiguredError(
                "No AI key configured. Add ANTHROPIC_API_KEY to the .env file and restart."
            )
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._settings = settings

    def extract[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        return self._call(system, [{"type": "text", "text": user}], schema)

    def extract_pdf[T: BaseModel](
        self, *, system: str, pdf: bytes, instruction: str, schema: type[T]
    ) -> LLMResult[T]:
        document = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.b64encode(pdf).decode("ascii"),
            },
        }
        return self._call(system, [document, {"type": "text", "text": instruction}], schema)

    def _call[T: BaseModel](
        self, system: str, content: list[dict[str, Any]], schema: type[T]
    ) -> LLMResult[T]:
        response = self._client.beta.messages.parse(
            model=self._settings.llm_model,
            max_tokens=self._settings.llm_max_output_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],  # type: ignore[typeddict-item]
            output_format=schema,
            output_config=cast("BetaOutputConfigParam", {"effort": self._settings.llm_effort}),
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise LLMRefusedError("The AI declined to read this document.")
        parsed = response.parsed_output
        if parsed is None:
            raise LLMRefusedError(f"The AI returned no usable result ({response.stop_reason}).")
        return LLMResult(
            output=parsed,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


class FakeClient:
    """Deterministic stand-in for tests and offline demos: returns whatever `responder`
    builds from the prompt, validated against the schema like a real reply."""

    def __init__(self, responder: Callable[[str, str], object]) -> None:
        self._responder = responder

    def extract[T: BaseModel](self, *, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        output = schema.model_validate(self._responder(system, user))
        return LLMResult(output=output, model="fake", input_tokens=len(user) // 4, output_tokens=0)

    def extract_pdf[T: BaseModel](
        self, *, system: str, pdf: bytes, instruction: str, schema: type[T]
    ) -> LLMResult[T]:
        user = f"[PDF {len(pdf)} bytes] {instruction}"
        return self.extract(system=system, user=user, schema=schema)


_override: LLMClient | None = None


def set_llm_client(client: LLMClient | None) -> None:
    """Install a client (tests); None restores provider selection from settings."""
    global _override
    _override = client


def get_llm_client() -> LLMClient:
    if _override is not None:
        return _override
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        return AnthropicClient(settings)
    raise LLMNotConfiguredError(f"Unknown LLM_PROVIDER {settings.llm_provider!r}")
