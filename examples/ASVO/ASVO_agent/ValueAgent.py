import os

from collections.abc import Mapping
import datetime
import types

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import associative_memory
from concordia.associative_memory import formative_memories
from concordia.clocks import game_clock
from concordia.components import agent as agent_components
from concordia.language_model import language_model
from concordia.memory_bank import legacy_associative_memory
from concordia.typing import entity_component
from concordia.utils import measurements as measurements_lib

import importlib

IMPORT_AGENT_BASE_DIR = 'examples.ASVO.value_components'
init_value_info_social = importlib.import_module(
    f'{IMPORT_AGENT_BASE_DIR}.init_value_info_social')
desire_svo_comp = importlib.import_module(f"{IMPORT_AGENT_BASE_DIR}.desire_svo_comp")

import NullObservation
from .Value_Act_SVO import MCTSActComponent
def _get_class_name(object_: object) -> str:
  return object_.__class__.__name__

class BackgroundKnowledge(agent_components.constant.Constant):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ConstantProfile(agent_components.constant.Constant):
  def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def build_ASVO_agent(
    *,
    config: formative_memories.AgentConfig,
    context_dict: Mapping[str, str], # contain value related context
    selected_desire: Mapping[str, str], # contain value related desire
    predefined_setting: Mapping[str, Mapping[str, str]], # contain value related setting
    model: language_model.LanguageModel,
    profile: str,
    memory: associative_memory.AssociativeMemory,
    background_knowledge:str,
    clock: game_clock.MultiIntervalClock,
    update_time_interval: datetime.timedelta,
    additional_components: Mapping[
        entity_component.ComponentName,
        entity_component.ContextComponent,
    ] = types.MappingProxyType({}),
    stored_target_folder:str,
    social_personality: str,
    agent_names: list,
    current_time: str,
) -> entity_agent_with_logging.EntityAgentWithLogging:
    del update_time_interval
    if not config.extras.get('main_character', False):
        raise ValueError('This function is meant for a main character '
                        'but it was called on a supported character.')

    #确保stored_target_folder路径存在
    os.makedirs(stored_target_folder, exist_ok=True)
    storage_folder = stored_target_folder

    # same as the original
    agent_name = config.name
    raw_memory = legacy_associative_memory.AssociativeMemoryBank(memory)
    measurements = measurements_lib.Measurements()

    instructions = agent_components.instructions.Instructions(
      agent_name=agent_name,
      logging_channel=measurements.get_channel('Instructions').on_next,
    )

    SVO_instructions = desire_svo_comp.SVO_Instructions(
        agent_name=agent_name,
        logging_channel=measurements.get_channel('SVO_Instructions').on_next,
    )

    time_display = agent_components.report_function.ReportFunction(
      function=clock.current_time_interval_str,
      pre_act_key='\nCurrent time',
      logging_channel=measurements.get_channel('TimeDisplay').on_next,
    )

    background_knowledge_comp = BackgroundKnowledge(
        state=background_knowledge,
        pre_act_key='\nbackground knowledge',
        logging_channel=measurements.get_channel('Background Knowledge').on_next,
    )

    identity_label = '\nIdentity characteristics'
    identity = agent_components.question_of_query_associated_memories.Identity(
       model = model,
       logging_channel=measurements.get_channel(
              'Identity'
          ).on_next,
          pre_act_key=identity_label,
    )
    social_personality_label = '\nSocial personality'
    personality = agent_components.constant.Constant(
        state=social_personality,
        pre_act_key=social_personality_label,
        logging_channel=measurements.get_channel(social_personality_label).on_next
    )

    if config.goal:
        goal_label = '\nGoal'
        overarching_goal = agent_components.constant.Constant(
            state=config.goal,
            pre_act_key=goal_label,
            logging_channel=measurements.get_channel(goal_label).on_next)
    else:
        goal_label = None
        overarching_goal = None

    observation_label = '\nCurrent observation'
    observation = agent_components.observation.Observation(
        clock_now=clock.now,
        timeframe=clock.get_step_size(),
        pre_act_key=observation_label,
        logging_channel=measurements.get_channel('Observation').on_next,
    )

    observation_summary_label = '\nSummary of recent observations'
    observation_summary = agent_components.observation.ObservationSummary(
        model=model,
        clock_now=clock.now,
        timeframe_delta_from=datetime.timedelta(hours=4),
        timeframe_delta_until=datetime.timedelta(hours=1),
        components = {_get_class_name(identity): identity},
        pre_act_key=observation_summary_label,
        logging_channel=measurements.get_channel('ObservationSummary').on_next,
    )

    profile_label = '\nProfile'
    profile_comp = ConstantProfile(
        state=profile.format(agent_name=agent_name),
        pre_act_key=profile_label,
        logging_channel=measurements.get_channel(profile_label).on_next,
    )
    tracked_components = {
        _get_class_name(identity): "Identity",
        _get_class_name(profile_comp): "Profile",
        _get_class_name(background_knowledge_comp): "BackgroundKnowledge",
        _get_class_name(personality): 'SocialPersonality',
        _get_class_name(observation_summary): "ObservationSummary",
    }
    info_storage = agent_components.new_agent_info_storage.AgentInfoStorage(
        storage_folder=storage_folder,
        logging_channel=measurements.get_channel('AgentInfoStorage').on_next,
        components=tracked_components,
        current_time=current_time,
    )

    ## Value Components
    general_pre_act_label = f"\n{agent_name}" + "'s current feeling of {desire_name} is"

    ### init the information to be used in the value component
    # 在这里，获得expected_values
    detailed_values_dict, expected_values = init_value_info_social.preprocess_value_information_with_svo(context_dict, predefined_setting, selected_desire,social_personality)
    all_desire_components = init_value_info_social.get_all_desire_components(model, general_pre_act_label, observation, clock, measurements, detailed_values_dict, expected_values, wanted_desires=selected_desire, social_personality=social_personality)
    target_tracking_desire_component = dict()
    for desire_name, desire_component in all_desire_components.items():
        target_tracking_desire_component[_get_class_name(desire_component)] = desire_component

    value_tracker = desire_svo_comp.ValueTracker(
        clock_now=clock.now,
        pre_act_key='',
        desire_components=target_tracking_desire_component,
        logging_channel=measurements.get_channel('ValueTracker').on_next,
        init_value = predefined_setting,
        expected_value_dict=expected_values,
        observation_component_name=_get_class_name(observation_summary),
        agent_names=agent_names,
        current_agent_name=agent_name,
        model=model,
        social_personality=social_personality,
    )

    null_observation = NullObservation.NULLObservation(
        clock_now=clock.now,
        timeframe=None,
        memory_component_name=agent_components.memory_component.DEFAULT_MEMORY_COMPONENT_NAME,
        logging_channel=measurements.get_channel('NullObservation').on_next,
        pre_act_key='',
    )

    entity_components = (
        # Components that provide pre_act context.
        instructions,
        SVO_instructions,
        profile_comp,
        background_knowledge_comp,
        observation,
        personality,
        observation_summary,
        time_display,
        identity,
        info_storage,

        value_tracker,
        null_observation,
    )

    entity_components += tuple(all_desire_components.values())
    components_of_agent = {_get_class_name(component): component
                         for component in entity_components}

    components_of_agent[
        agent_components.memory_component.DEFAULT_MEMORY_COMPONENT_NAME] = (
            agent_components.memory_component.MemoryComponent(raw_memory))
    #print(f"DEBUG: context_components keys = {list(components_of_agent.keys())}")

    component_order = list(components_of_agent.keys())
    if overarching_goal is not None:
        components_of_agent[goal_label] = overarching_goal
        # Place goal after the instructions.
        component_order.insert(1, goal_label)

    act_component = MCTSActComponent(
        model=model,
        clock=clock,
        num_proposed_actions = 3,
        desire_component_dict = all_desire_components,
        component_order=component_order,
        logging_channel=measurements.get_channel('ActComponent').on_next,
        social_personality=social_personality,
    )

    agent = entity_agent_with_logging.EntityAgentWithLogging(
        agent_name=agent_name,
        act_component=act_component,
        context_components=components_of_agent,
        component_logging=measurements,
    )

    return agent