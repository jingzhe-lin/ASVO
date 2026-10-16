"""Record ASVO model requests using the context snapshot format."""

from collections.abc import Collection, Mapping, Sequence
from typing import Any

from concordia.language_model import context_snapshot_logger
from concordia.language_model import language_model


class ContextSnapshotModel(language_model.LanguageModel):
  """Wrap any Concordia model without changing its request behavior."""

  def __init__(self, model: language_model.LanguageModel, model_name: str):
    self._model = model
    self._model_name = model_name

  def _record(self, prompt: str, output: str | None, error: Exception | None = None):
    context_snapshot_logger.log_context_snapshot(
        provider=type(self._model).__name__,
        model_name=self._model_name,
        system_prompt='',
        user_input=prompt,
        prompt_tokens=None,
        llm_output=output,
        request_status='error' if error else 'success',
        error_type=type(error).__name__ if error else None,
        error_message=str(error) if error else None,
    )

  def sample_text(
      self,
      prompt: str,
      *,
      max_tokens: int = language_model.DEFAULT_MAX_TOKENS,
      terminators: Collection[str] = language_model.DEFAULT_TERMINATORS,
      temperature: float = language_model.DEFAULT_TEMPERATURE,
      timeout: float = language_model.DEFAULT_TIMEOUT_SECONDS,
      seed: int | None = None,
  ) -> str:
    try:
      output = self._model.sample_text(
          prompt, max_tokens=max_tokens, terminators=terminators,
          temperature=temperature, timeout=timeout, seed=seed,
      )
    except Exception as error:
      self._record(prompt, None, error)
      raise
    self._record(prompt, output)
    return output

  def sample_choice(
      self,
      prompt: str,
      responses: Sequence[str],
      *,
      seed: int | None = None,
  ) -> tuple[int, str, Mapping[str, Any]]:
    try:
      result = self._model.sample_choice(prompt, responses, seed=seed)
    except Exception as error:
      self._record(prompt, None, error)
      raise
    self._record(prompt, result[1])
    return result
