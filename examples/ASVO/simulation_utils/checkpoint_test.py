"""Offline regression checks for checkpoint and notebook resume boundaries."""

import datetime as dt
import json
from pathlib import Path
import random
import tempfile
import types
import unittest

import numpy as np

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import associative_memory, formative_memories
from concordia.clocks import game_clock
from concordia.components import constant
from concordia.components.agent import concat_act_component, memory_component
from concordia.components.game_master import direct_effect, player_status, relevant_events, time_display
from concordia.environment import game_master
from concordia.language_model import no_language_model
from concordia.memory_bank import legacy_associative_memory
from examples.ASVO.simulation_utils import checkpoint


class CheckpointTest(unittest.TestCase):
  def make_runtime(self):
    clock = game_clock.MultiIntervalClock(
        start=dt.datetime(2025, 10, 1),
        step_sizes=[dt.timedelta(minutes=20), dt.timedelta(seconds=10)])
    model = no_language_model.NoLanguageModel()
    def memory():
      return associative_memory.AssociativeMemory(
          lambda _: np.array([0.123456789123456, 0.8]),
          lambda *_: 0.5, clock=clock.now)
    mem, gm_mem = memory(), memory()
    player = entity_agent_with_logging.EntityAgentWithLogging(
        agent_name='Alice',
        act_component=concat_act_component.ConcatActComponent(model, clock),
        context_components={'memory': memory_component.MemoryComponent(
            legacy_associative_memory.AssociativeMemoryBank(mem))})
    status = player_status.PlayerStatus(clock.now, model, gm_mem, ['Alice'])
    env = game_master.GameMaster(
        model=model, memory=gm_mem, clock=clock, players=[player], components=[
            constant.ConstantComponent('facts'), status,
            relevant_events.RelevantEvents(clock.now, model, gm_mem),
            direct_effect.DirectEffect([player], model=model, memory=gm_mem,
                                       clock_now=clock.now),
            time_display.TimeDisplay(clock)], seed=42)
    return clock, mem, gm_mem, player, status, env

  def test_real_components_round_trip_and_next_step(self):
    clock, mem, gm_mem, player, status, env = self.make_runtime()
    mem.add('Alice arrived', tags=['event'])
    gm_mem.add('Alice arrived')
    status._state = 'Alice at home'
    status._partial_states = {'Alice': 'home'}
    status._last_memory_len = 1
    status._history = [{'date': clock.now(), 'state': status._state}]
    env._log = [{'date': clock.now(), 'Event statement': 'arrival'}]
    clock._gear_up()
    clock.advance()
    with tempfile.TemporaryDirectory() as folder:
      path = checkpoint.save_checkpoint(
          checkpoint_dir=folder, step=2, agent_type='ASVO',
          players=[player], memories={'Alice': mem}, clock=clock, env=env,
          game_master_memory=gm_mem,
          player_configs=[formative_memories.AgentConfig(name='Alice')],
          metadata={'tracker': {2: np.array([1., 2.])}})
      expected = (random.random(), np.random.random(), env._rng.random())
      payload = checkpoint.load_checkpoint(path)
      new_clock, new_mem, new_gm, new_player, new_status, new_env = self.make_runtime()
      new_clock._start = dt.datetime(2020, 1, 1)
      new_env._seed = 99
      checkpoint.restore_runtime_state(
          payload, players=[new_player], memories={'Alice': new_mem},
          clock=new_clock, env=new_env, game_master_memory=new_gm)
      self.assertEqual(clock.now(), new_clock.now())
      self.assertEqual(clock.get_step_size(), new_clock.get_step_size())
      self.assertEqual((random.random(), np.random.random(), new_env._rng.random()), expected)
      self.assertEqual(new_env._seed, 42)
      self.assertEqual(new_status.get_history(), status.get_history())
      self.assertEqual(new_status.partial_state('Alice'), 'home')
      self.assertEqual(new_env.get_history(), env.get_history())
      self.assertEqual(mem.retrieve_recent(10, add_time=True), new_mem.retrieve_recent(10, add_time=True))
      self.assertEqual(mem.retrieve_associative('Alice'), new_mem.retrieve_associative('Alice'))
      np.testing.assert_array_equal(mem._memory_bank.iloc[0]['embedding'], new_mem._memory_bank.iloc[0]['embedding'])
      new_mem.add('Alice arrived', timestamp=dt.datetime(2025, 10, 1), tags=['event'])
      self.assertEqual(len(new_mem), 1)
      self.assertIn(2, payload['metadata']['tracker'])
      # Run an actual next GM step with offline components after restoring.
      new_env.step()
      self.assertGreater(new_clock.now(), clock.now())
      checkpoint.save_checkpoint(
          checkpoint_dir=folder, step=3, agent_type='ASVO', players=[new_player],
          memories={'Alice': new_mem}, clock=new_clock, env=new_env,
          game_master_memory=new_gm, player_configs=[formative_memories.AgentConfig(name='Alice')])

  def test_memory_empty_and_legacy_formats(self):
    clock, mem, _, _, _, _ = self.make_runtime()
    mem.set_state(json.loads(json.dumps(mem.get_state())))
    self.assertEqual(mem.retrieve_recent(10), [])
    mem.add('event', tags=['test'])
    legacy = {'seed': 1, 'stored_hashes': [-1], 'memory_bank': mem._memory_bank.to_json()}
    restored = self.make_runtime()[1]
    restored.set_state(legacy)
    self.assertEqual(restored.retrieve_recent(10, add_time=True), mem.retrieve_recent(10, add_time=True))
    restored.add('event', tags=['test'])
    self.assertEqual(len(restored), 1)

  def test_checkpoint_selection_ignores_directories(self):
    with tempfile.TemporaryDirectory() as folder:
      first = Path(folder) / 'checkpoint_step_000002.json'
      first.write_text('{}')
      (Path(folder) / 'checkpoint_step_999999.json').mkdir()
      self.assertEqual(checkpoint.resolve_checkpoint(None, folder), first.resolve())

  def test_notebook_gm_resume_skips_initial_observations(self):
    notebook = json.loads((Path(__file__).parents[1] / 'Simulation.ipynb').read_text(encoding='utf8'))
    clock, _, _, player, _, _ = self.make_runtime()
    class NeverObserve:
      name = 'Alice'
      def observe(self, _):
        raise AssertionError('Resume must not inject an initial observation')
    from concordia import components as generic_components
    from concordia.components import game_master as gm_components
    namespace = dict(associative_memory=associative_memory, embedder=lambda _: np.ones(2),
        importance_model_gm=types.SimpleNamespace(importance=lambda *_: 1.),
        generic_components=generic_components, gm_components=gm_components,
        game_master=game_master, model=no_language_model.NoLanguageModel(),
        START_TIME=clock.now(), scenario={'gm_facts_desc': 'facts'})
    exec(''.join(notebook['cells'][13]['source']), namespace)
    runtime = namespace['build_game_master']([], [NeverObserve()], ['Alice'], {}, clock, [], None, ['facts'], resume_payload={})
    self.assertEqual(len(runtime[1]), 0)

  def test_export_support_agent_preserves_resumed_context(self):
    from concordia.utils import html as html_lib
    notebook = json.loads((Path(__file__).parents[1] / 'Simulation.ipynb').read_text(encoding='utf8'))
    clock, mem, gm_mem, player, status, env = self.make_runtime()
    config = formative_memories.AgentConfig(name='Alice')
    with tempfile.TemporaryDirectory() as folder:
      namespace = dict(EntityWithComponents=object, desire_svo_comp=types.SimpleNamespace(ValueTracker=object),
          model=no_language_model.NoLanguageModel(), model_name='offline',
          html_lib=html_lib, datetime=dt, os=__import__('os'), json=json,
          stored_target_folder=folder)
      exec(''.join(notebook['cells'][17]['source']), namespace)
      result = dict(env=env, players=[player], memories={'Alice': mem},
          player_configs=[config], game_master_memory=gm_mem, current_time='original',
          convo_externality=None,
          direct_effect_externality=next(c for c in env._components.values() if isinstance(c, direct_effect.DirectEffect)),
          relevant_events=next(c for c in env._components.values() if isinstance(c, relevant_events.RelevantEvents)),
          player_status=status, agent_personality={}, shared_context='restored background')
      files = namespace['save_simulation_results'](result, 'LLMob', '')
      data = json.loads(Path(files[0]).read_text(encoding='utf8'))
      self.assertEqual(data['sampled_background'], 'restored background')
      self.assertEqual(data['agent_name'], 'Alice')

  def test_desire_and_tracker_state_for_all_variants(self):
    import importlib
    for module in ('desire_svo_comp', 'desire_no_svo_comp', 'baseline_version.value_comp'):
      comp = importlib.import_module('examples.ASVO.value_components.' + module)
      desire = comp.desire.__new__(comp.desire)
      desire._value = 7
      desire._value_change_cache = [{2: 'changed'}]
      desire._action_cache = ['action']
      restored = comp.desire.__new__(comp.desire)
      restored.set_state(checkpoint._decode(checkpoint._encode(desire.get_state())))
      self.assertEqual(restored.get_state(), desire.get_state())
      tracker = comp.ValueTracker.__new__(comp.ValueTracker)
      # Populate each serialized field without querying a language model.
      for field in ('_step_counter', '_whole_delta_tracker', '_individual_desire_tracker',
                    '_individual_delta_tracker', '_individual_qualitative_desire_tracker',
                    '_action_cache', '_expected_value_dict'):
        setattr(tracker, field, 3 if field == '_step_counter' else {2: 5})
      restored_tracker = comp.ValueTracker.__new__(comp.ValueTracker)
      restored_tracker.__dict__.update(tracker.__dict__)
      restored_tracker.set_state(checkpoint._decode(checkpoint._encode(tracker.get_state())))
      self.assertEqual(restored_tracker.get_state(), tracker.get_state())

  def test_all_agent_entrypoints_import(self):
    import importlib
    import sys
    notebook_dir = str(Path(__file__).parents[1])
    sys.path.insert(0, notebook_dir)
    try:
      for module in ('ASVO_agent.ValueAgent', 'ASVO_agent.ValueAgent_without_SVO',
                     'Baseline_agent.Baseline_ReAct', 'Baseline_agent.Baseline_LLMob',
                     'Baseline_agent.Baseline_BabyAGI', 'Baseline_agent.D2A_comp',
                     'NPC_agent.generic_support_agent'):
        importlib.import_module(module)
    finally:
      sys.path.remove(notebook_dir)


if __name__ == '__main__':
  unittest.main()
