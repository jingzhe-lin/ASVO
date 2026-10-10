"""JSON checkpoints for resuming ASVO notebook simulations."""

from __future__ import annotations

import datetime
import json
import os
import random
import re
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


def _collect_gm_component(component: Any) -> dict[str, Any]:
  # The legacy GM API has state(), not the entity component get_state API.
  return {name: getattr(component, name) for name in (
      "_state", "_partial_states", "_last_memory_len", "_history"
  ) if hasattr(component, name)}


def _encode(value: Any) -> Any:
  if isinstance(value, datetime.datetime):
    return {"__datetime__": value.isoformat()}
  if isinstance(value, np.ndarray):
    return {"__ndarray__": value.tolist(), "dtype": str(value.dtype)}
  if isinstance(value, np.generic):
    return value.item()
  if isinstance(value, tuple):
    return {"__tuple__": [_encode(item) for item in value]}
  if isinstance(value, list):
    return [_encode(item) for item in value]
  if isinstance(value, dict):
    return {"__mapping__": [[_encode(key), _encode(item)] for key, item in value.items()]}
  if value is None or isinstance(value, (str, int, float, bool)):
    return value
  if hasattr(value, "value"):
    return _encode(value.value)
  raise TypeError(f"Unsupported checkpoint value: {type(value).__name__}")


def _decode(value: Any) -> Any:
  if isinstance(value, list):
    return [_decode(item) for item in value]
  if isinstance(value, dict):
    if "__datetime__" in value:
      return datetime.datetime.fromisoformat(value["__datetime__"])
    if "__ndarray__" in value:
      return np.asarray(value["__ndarray__"], dtype=value.get("dtype"))
    if "__tuple__" in value:
      return tuple(_decode(item) for item in value["__tuple__"])
    if "__mapping__" in value:
      return {_decode(key): _decode(item) for key, item in value["__mapping__"]}
    return {key: _decode(item) for key, item in value.items()}
  return value


def collect_agent_state(agent: Any) -> dict[str, Any]:
  """Collects all stateful components from a Concordia entity agent."""
  state = {"act_component": agent.get_act_component().get_state()}
  context_processor = getattr(agent, "_context_processor", None)
  if context_processor is not None:
    state["context_processor"] = context_processor.get_state()
  state.update({
      name: component.get_state()
      for name, component in agent.get_all_context_components().items()
  })
  return state


def restore_agent_state(agent: Any, state: dict[str, Any]) -> None:
  expected = {"act_component", *agent.get_all_context_components().keys()}
  context_processor = getattr(agent, "_context_processor", None)
  if context_processor is not None:
    expected.add("context_processor")
  if set(state) != expected:
    raise ValueError(
        f"Checkpoint components for {agent.name} do not match this agent: "
        f"missing={sorted(expected - set(state))}, "
        f"unexpected={sorted(set(state) - expected)}"
    )
  for name, component_state in state.items():
    if name == "act_component":
      component = agent.get_act_component()
    elif name == "context_processor":
      component = context_processor
    else:
      component = agent.get_component(name)
    component.set_state(component_state)


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  temp_path = None
  try:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix=f".{path.stem}_", suffix=".tmp", delete=False
    ) as handle:
      temp_path = Path(handle.name)
      json.dump(payload, handle, ensure_ascii=False, indent=2)
      handle.flush()
      os.fsync(handle.fileno())
    os.replace(temp_path, path)
  finally:
    if temp_path is not None and temp_path.exists():
      temp_path.unlink()


def save_checkpoint(
    *, checkpoint_dir: str | os.PathLike[str], step: int, agent_type: str,
    players: list[Any], memories: dict[str, Any], clock: Any, env: Any,
    game_master_memory: Any, player_configs: list[Any], **metadata: Any,
) -> Path:
  """Atomically saves a step boundary, including RNG and environment state."""
  path = Path(checkpoint_dir) / f"checkpoint_step_{step:06d}.json"
  components = getattr(env, "_components", {})
  rng_state = {
      "python": random.getstate(),
      "numpy": np.random.get_state(),
      "game_master": env._rng.getstate(),
  }
  if set(metadata) == {"metadata"} and isinstance(metadata["metadata"], dict):
    metadata = metadata["metadata"]
  payload = {
      "schema_version": 1,
      "step": int(step),
      "agent_type": agent_type,
      "clock_time": clock.now().isoformat(),
      "clock_start": clock._start,
      "clock_gear": clock._current_gear,
      "clock_step_sizes_seconds": [
          float(size.total_seconds()) for size in clock._step_sizes
      ],
      "random_states": rng_state,
      "player_configs": [config.to_dict() for config in player_configs],
      "agent_states": {player.name: collect_agent_state(player) for player in players},
      "memory_states": {name: memory.get_state() for name, memory in memories.items()},
      "game_master_memory_state": game_master_memory.get_state(),
      "game_master_components": {
          name: _collect_gm_component(component)
          for name, component in components.items()
      },
      "game_master_seed": env._seed,
      "game_master_log": getattr(env, "_log", []),
      "metadata": metadata,
  }
  _atomic_write(path, _encode(payload))
  print(f"[checkpoint] saved step={step}: {path}")
  return path


def load_checkpoint(path: str | os.PathLike[str]) -> dict[str, Any]:
  with Path(path).open("r", encoding="utf-8") as handle:
    payload = _decode(json.load(handle))
  if payload.get("schema_version") != 1:
    raise ValueError(f"Unsupported ASVO checkpoint schema: {payload.get('schema_version')}")
  return payload


def resolve_checkpoint(
    checkpoint_file: str | os.PathLike[str] | None,
    checkpoint_folder: str | os.PathLike[str] | None,
) -> Path | None:
  if checkpoint_file:
    path = Path(checkpoint_file).expanduser()
    if not path.is_file():
      raise FileNotFoundError(f"ASVO checkpoint file not found: {path}")
    return path.resolve()
  if not checkpoint_folder:
    return None
  folder = Path(checkpoint_folder).expanduser()
  if not folder.is_dir():
    raise FileNotFoundError(f"ASVO checkpoint folder not found: {folder}")
  pattern = re.compile(r"^checkpoint_step_(\d+)\.json$")
  candidates = []
  for path in folder.iterdir():
    match = pattern.match(path.name)
    if match and path.is_file():
      candidates.append((int(match.group(1)), path))
  if not candidates:
    raise FileNotFoundError(f"No checkpoint_step_*.json found in {folder}")
  return max(candidates, key=lambda item: item[0])[1].resolve()


def restore_runtime_state(
    payload: dict[str, Any], *, players: list[Any], memories: dict[str, Any],
    clock: Any, env: Any, game_master_memory: Any,
) -> None:
  """Restores mutable agent, memory, GM, clock, and RNG state in place."""
  saved_agents = payload["agent_states"]
  if set(saved_agents) != {player.name for player in players}:
    raise ValueError("Checkpoint player names do not match the rebuilt simulation")
  for player in players:
    restore_agent_state(player, saved_agents[player.name])
  for name, state in payload["memory_states"].items():
    memories[name].set_state(state)
  game_master_memory.set_state(payload["game_master_memory_state"])
  if set(payload.get("game_master_components", {})) != set(env._components):
    raise ValueError("Checkpoint Game Master components do not match the simulation")
  for name, state in payload.get("game_master_components", {}).items():
    if name not in env._components:
      raise ValueError(f"Game Master component missing during restore: {name}")
    component = env._components[name]
    if set(state) != set(_collect_gm_component(component)):
      raise ValueError(f"Game Master state fields do not match: {name}")
    for field, value in state.items():
      setattr(component, field, value)
  env._log = list(payload.get("game_master_log", []))
  env._rng.setstate(payload["random_states"]["game_master"])
  if "game_master_seed" in payload:
    env._seed = payload["game_master_seed"]
  if "clock_start" in payload:
    clock._start = payload["clock_start"]
  clock._current_gear = payload.get("clock_gear", 0)
  clock.set(datetime.datetime.fromisoformat(payload["clock_time"]))
  random.setstate(payload["random_states"]["python"])
  np.random.set_state(payload["random_states"]["numpy"])
