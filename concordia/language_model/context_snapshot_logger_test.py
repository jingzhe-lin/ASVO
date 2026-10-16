# Copyright 2023 DeepMind Technologies Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for context snapshot logging."""

import json
import os
from pathlib import Path
from absl.testing import absltest
from concordia.language_model import context_snapshot_logger
from concordia.language_model import context_snapshot_model
from concordia.utils import concurrency


def _read_jsonl_entries(path: Path) -> list[dict]:
  lines = [
      line.strip() for line in path.read_text(encoding='utf-8').splitlines()
      if line.strip()
  ]
  return [json.loads(line) for line in lines]


def _read_json(path: Path) -> dict:
  return json.loads(path.read_text(encoding='utf-8'))


class ContextSnapshotLoggerTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.enter_context(absltest.mock.patch.dict(os.environ, {}, clear=False))
    self.enter_context(
        absltest.mock.patch.object(context_snapshot_logger, '_RUN_ID', None)
    )
    self.create_tempdir().full_path

  def _configure_snapshot_run(
      self,
      *,
      run_id: str,
  ) -> Path:
    run_dir = Path(self.create_tempdir().full_path)
    snapshots_root = run_dir / 'context_snapshots'
    self.enter_context(
        absltest.mock.patch.object(
            context_snapshot_logger,
            '_context_snapshots_root',
            return_value=snapshots_root,
        )
    )
    self.enter_context(
        absltest.mock.patch.dict(
            os.environ,
            {'CONCORDIA_CONTEXT_SNAPSHOT_RUN_ID': run_id},
            clear=False,
        )
    )
    return snapshots_root

  def test_log_context_snapshot_isolated_by_run_id(self):
    snapshots_root = self._configure_snapshot_run(run_id='sim_run_001')

    token = context_snapshot_logger.set_current_agent_name('alice')
    try:
      context_snapshot_logger.log_context_snapshot(
          provider='openai',
          model_name='test-model',
          system_prompt='sys',
          user_input='user',
          prompt_tokens=10,
          llm_output='model answer',
      )
    finally:
      context_snapshot_logger.reset_current_agent_name(token)

    snapshot_file = snapshots_root / 'sim_run_001' / 'alice.jsonl'
    self.assertTrue(snapshot_file.exists())
    payload = _read_jsonl_entries(snapshot_file)
    self.assertLen(payload, 1)
    self.assertEqual(payload[0]['agent_name'], 'alice')
    self.assertEqual(payload[0]['llm_output'], 'model answer')

  def test_wrapped_model_saves_text_choice_and_error(self):
    snapshots_root = self._configure_snapshot_run(run_id='sim_run_model')
    class FakeModel:
      def sample_text(self, prompt, **kwargs):
        if prompt == 'fail':
          raise ValueError('model failed')
        return 'text answer'
      def sample_choice(self, prompt, responses, *, seed=None):
        return 1, responses[1], {'ok': True}

    model = context_snapshot_model.ContextSnapshotModel(FakeModel(), 'fake')
    token = context_snapshot_logger.set_current_agent_name('alice')
    try:
      self.assertEqual(model.sample_text('text prompt'), 'text answer')
      self.assertEqual(model.sample_choice('choice prompt', ['A', 'B'])[1], 'B')
      with self.assertRaisesRegex(ValueError, 'model failed'):
        model.sample_text('fail')
    finally:
      context_snapshot_logger.reset_current_agent_name(token)

    records = _read_jsonl_entries(
        snapshots_root / 'sim_run_model' / 'alice.jsonl'
    )
    self.assertEqual([record['user_input'] for record in records],
                     ['text prompt', 'choice prompt', 'fail'])
    self.assertEqual([record['llm_output'] for record in records],
                     ['text answer', 'B', None])
    self.assertEqual(records[-1]['request_status'], 'error')

  def test_agent_name_reaches_parallel_components(self):
    snapshots_root = self._configure_snapshot_run(run_id='parallel_run')
    token = context_snapshot_logger.set_current_agent_name('alice')
    try:
      concurrency.run_tasks({
          'component': lambda: context_snapshot_logger.log_context_snapshot(
              provider='fake', model_name='fake', system_prompt='',
              user_input='parallel prompt', prompt_tokens=None,
              llm_output='answer',
          )
      })
    finally:
      context_snapshot_logger.reset_current_agent_name(token)
    records = _read_jsonl_entries(snapshots_root / 'parallel_run' / 'alice.jsonl')
    self.assertEqual(records[0]['user_input'], 'parallel prompt')

  def test_log_context_snapshot_routes_unknown_game_master_to_json(self):
    snapshots_root = self._configure_snapshot_run(run_id='sim_run_002')

    context_snapshot_logger.log_context_snapshot(
        provider='openai',
        model_name='test-model',
        system_prompt='You are the game master in this simulation.',
        user_input='Describe the next scene.',
        prompt_tokens=12,
    )

    snapshot_file = (
        snapshots_root
        / 'sim_run_002'
        / 'game_master.jsonl'
    )
    self.assertTrue(snapshot_file.exists())
    payload = _read_jsonl_entries(snapshot_file)
    self.assertLen(payload, 1)
    self.assertEqual(payload[0]['agent_name'], 'unknown_agent')

  def test_log_context_snapshot_routes_non_game_master_unknown_to_json(self):
    snapshots_root = self._configure_snapshot_run(run_id='sim_run_003')

    context_snapshot_logger.log_context_snapshot(
        provider='openai',
        model_name='test-model',
        system_prompt='You are an assistant helping with narration.',
        user_input='Continue the story.',
        prompt_tokens=9,
    )

    snapshot_file = (
            snapshots_root
            / 'sim_run_003'
            / 'unknown_agent.jsonl'
    )
    self.assertTrue(snapshot_file.exists())
    payload = _read_jsonl_entries(snapshot_file)
    self.assertLen(payload, 1)
    self.assertEqual(payload[0]['agent_name'], 'unknown_agent')

  def test_log_context_snapshot_routes_importance_judgments_to_dedicated_json(
      self,
  ):
    snapshots_root = self._configure_snapshot_run(run_id='sim_run_004')

    context_snapshot_logger.log_context_snapshot(
        provider='openai',
        model_name='test-model',
        system_prompt='You are an assistant.',
        user_input=(
            "A memory text -- how memorable: 1.0\n"
            "Relative to the life memories above, on a scale from 0 to 3..."
        ),
        prompt_tokens=20,
    )

    dedicated_file = (
        snapshots_root
        / 'sim_run_004'
        / 'importance_judgments.jsonl'
    )
    unknown_file = (
        snapshots_root
        / 'sim_run_004'
        / 'unknown_agent.jsonl'
    )
    self.assertTrue(dedicated_file.exists())
    payload = _read_jsonl_entries(dedicated_file)
    self.assertLen(payload, 1)
    self.assertEqual(payload[0]['agent_name'], 'unknown_agent')
    self.assertFalse(unknown_file.exists())

  def test_log_context_snapshot_routes_sleep_state_judgments_to_dedicated_json(
      self,
  ):
    snapshots_root = self._configure_snapshot_run(run_id='sim_run_005')

    context_snapshot_logger.log_context_snapshot(
        provider='openai',
        model_name='test-model',
        system_prompt='You are an assistant.',
        user_input=(
            "Alice is currently in a sleep-related schedule block.\n"
            "Please judge Alice's CURRENT sleep phase from the observation and context below.\n"
            "Sleep phase labels:\n"
        ),
        prompt_tokens=11,
    )

    dedicated_file = (
        snapshots_root
        / 'sim_run_005'
        / 'sleep_state_judgments.jsonl'
    )
    unknown_file = (
        snapshots_root
        / 'sim_run_005'
        / 'unknown_agent.jsonl'
    )
    self.assertTrue(dedicated_file.exists())
    payload = _read_jsonl_entries(dedicated_file)
    self.assertLen(payload, 1)
    self.assertEqual(payload[0]['agent_name'], 'unknown_agent')
    self.assertFalse(unknown_file.exists())

  def test_log_context_snapshot_routes_content_blocks_to_dedicated_json(self):
    snapshots_root = self._configure_snapshot_run(run_id='sim_run_006')

    token = context_snapshot_logger.set_current_agent_name('bob')
    try:
      context_snapshot_logger.log_context_snapshot(
          provider='openai',
          model_name='test-model',
          system_prompt='sys',
          user_input='user prompt with blocked content',
          prompt_tokens=None,
          request_status='content_blocked',
          error_type='BadRequestError',
          error_message='data_inspection_failed',
          error_code='data_inspection_failed',
          request_summary={'model': 'test-model'},
          response_debug=[],
          attempt=1,
          max_attempts=10,
      )
    finally:
      context_snapshot_logger.reset_current_agent_name(token)

    blocked_dir = snapshots_root / 'sim_run_006' / 'logs' / 'content_blocks'
    self.assertTrue(blocked_dir.exists())
    json_files = sorted(blocked_dir.glob('*.json'))
    markdown_files = sorted(blocked_dir.glob('*.md'))
    self.assertLen(json_files, 1)
    self.assertLen(markdown_files, 1)

    payload = _read_json(json_files[0])
    self.assertEqual(payload['agent_name'], 'bob')
    self.assertEqual(payload['request_status'], 'content_blocked')
    self.assertEqual(payload['error']['code'], 'data_inspection_failed')
    self.assertEqual(payload['attempt']['current'], 1)
    self.assertEqual(payload['attempt']['max'], 10)

    markdown_text = markdown_files[0].read_text(encoding='utf-8')
    self.assertIn('# Content Blocked Request', markdown_text)
    self.assertIn('## User Input', markdown_text)
    self.assertIn('user prompt with blocked content', markdown_text)

  def test_get_snapshot_run_id_stable_per_process(self):
    first = context_snapshot_logger.get_snapshot_run_id()
    second = context_snapshot_logger.get_snapshot_run_id()
    self.assertEqual(first, second)
    self.assertRegex(first, r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$')


if __name__ == '__main__':
  absltest.main()
