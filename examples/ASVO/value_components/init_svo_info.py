import importlib
IMPORT_AGENT_BASE_DIR = 'examples.ASVO.value_components'
svo_comp = importlib.import_module(f'{IMPORT_AGENT_BASE_DIR}.svo_comp')

def _get_class_name(object_: object) -> str:
    return object_.__class__.__name__

def get_svo_component_without_PreAct(
        model,
        pre_act_key:str,
        observation,
        selected_desire,
        expected_values,
        agent_name,
        storage_path,
        clock,
        measurements,
):
    init = svo_comp.SVO_Component_Without_PreAct
    SVO = init(
        model=model,
        pre_act_key=pre_act_key,
        observation_component_name=_get_class_name(observation),
        desire_components=selected_desire,
        expected_values=expected_values,
        agent_name=agent_name,
        storage_folder=storage_path,
        clock_now=clock.now,
        logging_channel=measurements.get_channel("SVO").on_next
    )
    return SVO

def get_svo_component(
        model,
        pre_act_key:str,
        observation,
        selected_desire,
        expected_values,
        agent_name,
        clock,
        measurements,
        agent_names,
):
    init = svo_comp.SVO_Component
    SVO = init(
        model=model,
        pre_act_key=pre_act_key,
        observation_component_name=_get_class_name(observation),
        desire_components=selected_desire,
        expected_values=expected_values,
        agent_name=agent_name,
        clock=clock,
        logging_channel=measurements.get_channel("SVO").on_next,
        agent_names=agent_names,
)
    return SVO