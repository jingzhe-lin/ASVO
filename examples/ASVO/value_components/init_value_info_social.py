import random
import importlib
IMPORT_AGENT_BASE_DIR = 'examples.ASVO.value_components'
value_comp = importlib.import_module(f'{IMPORT_AGENT_BASE_DIR}.desire_svo_comp')
from concordia.components.agent import memory_component
'''
profile_dict = {
  'gluttonous': 'hunger',
  'hedonistic': 'joyfulness',
  'lazy': 'passion',
  'sociable': 'social connectivity',
  'health-conscious': 'health',
  'spiritual': 'spiritual satisfaction',
  'materialistic': 'comfort',
  'obsessional about cleanliness': 'cleanliness',
  'fatigable': 'sleepiness',
  'timid': 'safety',
  'fast-metabolizing': 'thirst',
  'reputation-conscious': 'recognition',
  'possessive': 'sense of control',
  'competitiveness': 'sense of superiority',
  # "curious": "sense of wonder",
}'''
# profile_dict = {
#     "honest": "moral_integrity",
#     "curious": "intellectual_curiosity",
#     "energetic": "physical_vitality",
#     "artistic": "aesthetic_appreciation",
#     "diligent": "work_ethic",
# }
profile_dict = {
    "competitive": "sense of superiority",
    "ambitious": "sense_of_achievement",
    "confident": "confidence",
    "cheerful": "joyfulness",
    "relaxed": "comfort",
    "attention_seeking": "recognition",
    'possessive': 'sense of control',
    'spiritual': 'spiritual satisfaction',
}

decrease_map = {
    "Altruistic":{
        'extremely': 2.5,
        'quite': 2,
        'moderately': 1.75,
        'slightly': 1.5
    },
    "Prosocial":{
        'extremely': 2,
        'quite': 1.75,
        'moderately': 1.5,
        'slightly': 1
    },
    "Individualistic":{
        'extremely': 1.5,
        'quite': 1.25,
        'moderately': 1,
        'slightly': 0.5
    },
    "Competitive":{
        'extremely': 1,
        'quite': 0.75,
        'moderately': 0.5,
        'slightly': 0.25
    }
}
expected_map = {
    'extremely': 2,
    'quite': 1.5,
    'moderately': 1,
    'slightly': 0.5
}
'''
values_names = [
    'hunger',
    'thirst',
    'comfort',
    'health',
    'sleepiness',
    'joyfulness',
    'cleanliness',
    'safety',
    'passion',
    'spiritual satisfaction',
    'social connectivity',
    'recognition',
    'sense of control',
    'sense of superiority',
    # "sense of wonder",
]'''
# values_names = [
#     "moral_integrity",
#     "intellectual_curiosity",
#     "physical_vitality",
#     "aesthetic_appreciation",
#     "work_ethic",
# ]
values_names = [
    "sense of superiority",
    "sense_of_achievement",
    "confidence",
    'spiritual satisfaction',
    "joyfulness",
    "comfort",
    "recognition",
    'sense of control',

]

values_names_descriptions = {
    # 'hunger': 'The value of hunger ranges from 0 to 10. A score of 0 means you are fully satiated, feeling energized and satisfied after a wholesome meal, while a score of 10 means you are completely starved, feeling weak and unable to concentrate due to a severe lack of food.',

    # 'thirst': 'The value of thirst ranges from 0 to 10. A score of 0 means you are completely hydrated, feeling refreshed with your body functioning optimally, while a score of 10 means you are extremely dehydrated, with a dry mouth and feelings of dizziness and exhaustion.',

    'comfort': 'The value of comfort ranges from 0 to 10. A score of 0 means you are in extreme discomfort, experiencing pain or severe physical unease, while a score of 10 means you are in perfect comfort, feeling cozy and relaxed in your environment.',

    # 'health': 'The value of health ranges from 0 to 10. A score of 0 means your health is in critical condition, experiencing severe illness or injury, while a score of 10 means you are in excellent health, feeling strong, energetic, and free from ailments.',

    # 'sleepiness': 'The value of sleepiness ranges from 0 to 10. A score of 0 means you are fully rested, feeling alert and ready to tackle the day, while a score of 10 means you are utterly exhausted, struggling to keep your eyes open and concentrate.',

    'joyfulness': 'The value of joyfulness ranges from 0 to 10. A score of 0 means you feel completely miserable, experiencing profound sadness and a lack of pleasure in anything, while a score of 10 means you are experiencing immense joy, feeling incredibly happy and content.',

    # 'cleanliness': 'The value of cleanliness ranges from 0 to 10. A score of 0 means you feel utterly filthy, with a strong need to wash and clean yourself immediately, while a score of 10 means you feel impeccably clean, fresh, and hygienic from head to toe.',

    # 'safety': 'The value of safety ranges from 0 to 10. A score of 0 means you are in extreme danger, feeling vulnerable and constantly threatened, while a score of 10 means you feel completely safe, secure, and protected in your current environment.',

    # 'passion': 'The value of passion ranges from 0 to 10. A score of 0 means you feel extremely lazy, completely unmotivated to work or be productive, while a score of 10 means you are highly diligent, feeling motivated and putting in great effort in your tasks.',

    'spiritual satisfaction': 'The value of spiritual satisfaction ranges from 0 to 10. A score of 0 means you feel spiritually empty, lacking any sense of purpose or inner peace, while a score of 10 means you feel spiritually fulfilled, experiencing deep inner peace and a strong sense of purpose.',

    # 'social connectivity': 'The value of social connectivity ranges from 0 to 10. A score of 0 means you feel completely isolated, lacking any meaningful social connections, while a score of 10 means you feel highly socially connected, with a strong network of supportive relationships.',

    'recognition': 'The value of recognition ranges from 0 to 10. A score of 0 means you feel completely unrecognized, lacking acknowledgment or appreciation for your efforts, while a score of 10 means you feel highly recognized, with frequent acknowledgment for your contributions.',

    'sense of control': 'The value of sense of control ranges from 0 to 10. A score of 0 means you feel completely powerless, lacking influence over your circumstances, while a score of 10 means you feel highly in control, with a strong ability to influence and manage your life and environment.',

    'sense of superiority': 'The value of sense of superiority ranges from 0 to 10. A score of 0 means you feel no distinction over others, lacking any sense of being ahead of your peers, while a score of 10 means you feel highly superior, believing you are more capable or distinguished than those around you.',

    # 'sense of wonder': "The value of sense of wonder ranges from 0 to 10. A score of 0 means you feel no curiosity or amazement about the world, lacking any interest in exploration or new experiences, while a score of 10 means you are deeply fascinated and captivated by the world around you, constantly seeking to discover, learn, and marvel at new things."

    'sense_of_achievement': 'The value of sense_of_achievement ranges from 0 to 10. A score of 0 means you feel completely unfulfilled and believe nothing you do matters, while a score of 10 means you feel profoundly successful, deeply fulfilled by your accomplishments.',

    'confidence': 'The value of confidence ranges from 0 to 10. A score of 0 means you feel completely incapable and constantly doubt your abilities, while a score of 10 means you are extremely self-assured, trusting in your abilities even in the face of challenges.',

}
# values_names_descriptions = {
#     "moral_integrity": "The value of moral integrity ranges from 0 to 10. A score of 0 means the person is completely dishonest, manipulative, and willing to deceive others for personal gain, while a score of 10 means they are a moral exemplar, deeply committed to truth, fairness, and ethical conduct in all actions.",
#
#     "intellectual_curiosity": "The value of intellectual curiosity ranges from 0 to 10. A score of 0 means the person is completely uninterested in learning, avoids intellectual engagement, while a score of 10 means they are a lifelong learner, driven by an insatiable thirst for knowledge and discovery.",
#
#     "physical_vitality": "The value of physical vitality ranges from 0 to 10. A score of 0 means the person is extremely weak and unhealthy, struggling with daily physical activities, while a score of 10 means they are in elite-level health and fitness, full of vitality and resilience.",
#
#     "aesthetic_appreciation": "The value of aesthetic appreciation ranges from 0 to 10. A score of 0 means the person is completely indifferent to art, music, and beauty, while a score of 10 means they are a master of aesthetic appreciation, dedicating life to artistic expression and understanding.",
#
#     "work_ethic": "The value of work ethic ranges from 0 to 10. A score of 0 means the person is extremely lazy, avoids responsibilities and tasks, while a score of 10 means they are a tireless worker, deeply committed to discipline, excellence, and responsibility."
# }

values_dict = values_names_descriptions
#from pprint import pprint

def construct_all_profile_dict(wanted_desires: list[str], hidden_desires: list[str], predefined_desires: dict = None):
  if predefined_desires is not None:
    visual_desires_dict = predefined_desires['visual_desires_dict']
    hidden_desires_dict = predefined_desires['hidden_desires_dict']
    selected_profile_dict = predefined_desires['selected_desire_dict']
    traits_dict = predefined_desires['all_desire_traits_dict']

    traits = []
    for desire_name in visual_desires_dict.keys():
      _adj = selected_profile_dict[desire_name]['adj']
      _degree = traits_dict[_adj]
      append_str = f' is {_degree} {_adj}'
      traits.append("{agent_name}" + append_str)

    traits = '\n'.join(traits)
    return visual_desires_dict, hidden_desires_dict, selected_profile_dict, traits_dict, traits
  # construct_all_profile_dict的返回结果为：
  # visual_desires_dict（可见欲望字典）
  # hidden_desires_dict（隐藏欲望字典）
  # selected_profile_dict（选中的欲望字典）
  # traits_dict（欲望特征字典）
  # traits（智能体的完整 Profile 描述）“智能体name+程度描述+欲望对应的形容词”

  selected_profile_dict = dict() # key: desire, value: adj
  inverted_profile_dict = {desire: adj for adj, desire in profile_dict.items()}
  # pprint(f"inverted_profile_dict: {inverted_profile_dict}")
  for desire in wanted_desires:
    # pprint(f"desire: {desire}")
    desire_description = dict()
    desire_description['adj'] = inverted_profile_dict[desire]
    desire_description['description'] = values_dict[desire]
    selected_profile_dict[desire] = desire_description

  visual_desires = list(set(wanted_desires) - set(hidden_desires))
  visual_desires_dict = dict()
  for desire in visual_desires:
    visual_desires_dict[desire] = selected_profile_dict[desire]

  hidden_desires_dict = dict()
  for desire in hidden_desires:
    hidden_desires_dict[desire] = selected_profile_dict[desire]

  adj = [selected_profile_dict[desire_name]['adj'] for desire_name in selected_profile_dict.keys()]
  degree = ['extremely',
                'quite',
                'moderately',
                'slightly']

  traits_dict = dict()
  # contain both visual and hidden desires
  for i in range(len(adj)):
    _adj = adj[i]
    _degree = random.choice(degree)
    traits_dict[_adj] = _degree

  # only contain visual desires
  traits = []
  for desire_name in visual_desires:
    _adj = selected_profile_dict[desire_name]['adj']
    _degree = traits_dict[_adj]
    append_str = f' is {_degree} {_adj}'
    traits.append("{agent_name}" + append_str)

  traits = '\n'.join(traits)

  return (visual_desires_dict,
          hidden_desires_dict,
          selected_profile_dict,
          traits_dict,
          traits)




def _get_class_name(object_: object) -> str:
  return object_.__class__.__name__

def preprocess_value_information_with_svo(context_dict, predefined_setting, selected_desires: list[str], social_personality: str):
    # profile_dict is in current file
    ### init the information to be used in the value component
    revert_profile_dict = {value: adj for adj, value in profile_dict.items()}
    expected_values = dict()

    # desires that should be reversed, i.e. the higher the value, the worse the situation
    should_reverse = [
       'hunger',
       'thirst',
       'sleepiness',
    ]

    # desires that should have a fixed expected value instead of using the default calculation
    fix_expected_value = {'sleepiness': 3,
                          'passion': 8}

    return_dict = dict()

    # print(f"predefined: {predefined_setting}") # desire name: initial value # selected desires
    # print(f"context: {context_dict}") # adj: degree of decrease # selected desires
    # print(f"decrease_map: {decrease_map}") # degree of decrease : step of decrease
    # pprint(f"revert_profile_dict: {revert_profile_dict}") # desire name: adj # all the desires
    # pprint(f"values_dict: {values_dict}") # desire name: description # all the desires
    # pprint(f"selected_desires: {selected_desires}") # selected desires

    for name, description in values_dict.items():
        detailed_desire_setting_dict = dict()
        if name not in selected_desires:
            continue
        adj_of_value = revert_profile_dict[name]
        detailed_desire_setting_dict['adj'] = adj_of_value
        # pprint(f"adj_of_value: {adj_of_value}")
        # pprint(f"context_dict: {context_dict}")
        degree_of_decrease = context_dict[adj_of_value]
        detailed_desire_setting_dict['degree of decrease'] = degree_of_decrease # qualitative value
        detailed_desire_setting_dict['step of decrease'] = decrease_map[social_personality][degree_of_decrease] # numerical value
        detailed_desire_setting_dict['decrease time interval in hour'] = 1

        if name in ['spiritual satisfaction', 'social connectivity']:
            new_name = name
            detailed_desire_setting_dict['initial_value'] = predefined_setting[new_name]
        else:
            detailed_desire_setting_dict['initial_value'] = predefined_setting[name]
        detailed_desire_setting_dict['description'] = description
        if name in should_reverse:
            detailed_desire_setting_dict['reverse'] = True
            if name in fix_expected_value.keys():
                expected_values[name] = fix_expected_value[name]
            else:
                # expected_values[name] = 3 - detailed_desire_setting_dict['step of decrease']
                expected_values[name] = 3 - expected_map[degree_of_decrease]
        else:
            detailed_desire_setting_dict['reverse'] = False
            if name in fix_expected_value.keys():
                expected_values[name] = fix_expected_value[name]
            else:
                # expected_values[name] = 10 - (3 - detailed_desire_setting_dict['step of decrease'])
                expected_values[name] = 10 - (3 - expected_map[degree_of_decrease])

        return_dict[name] = detailed_desire_setting_dict
        #if os.path.exists(r"D:\gitpro\ASVO\examples\ASVO\result_folder\classroom_result"):
        #        with open(r"D:\gitpro\ASVO\examples\ASVO\result_folder\classroom_result\values.json", "w") as f:
        #            json.dump(expected_values, f, indent=4, ensure_ascii=False)

    return return_dict, expected_values

def preprocess_value_information(context_dict, predefined_setting, selected_desires: list[str]):
    # profile_dict is in current file
    ### init the information to be used in the value component
    revert_profile_dict = {value: adj for adj, value in profile_dict.items()}
    expected_values = dict()

    # desires that should be reversed, i.e. the higher the value, the worse the situation
    should_reverse = [
       'hunger',
       'thirst',
       'sleepiness',
    ]

    # desires that should have a fixed expected value instead of using the default calculation
    fix_expected_value = {'sleepiness': 3,
                          'passion': 8}

    return_dict = dict()

    # print(f"predefined: {predefined_setting}") # desire name: initial value # selected desires
    # print(f"context: {context_dict}") # adj: degree of decrease # selected desires
    # print(f"decrease_map: {decrease_map}") # degree of decrease : step of decrease
    # pprint(f"revert_profile_dict: {revert_profile_dict}") # desire name: adj # all the desires
    # pprint(f"values_dict: {values_dict}") # desire name: description # all the desires
    # pprint(f"selected_desires: {selected_desires}") # selected desires

    for name, description in values_dict.items():
        detailed_desire_setting_dict = dict()
        if name not in selected_desires:
            continue
        adj_of_value = revert_profile_dict[name]
        detailed_desire_setting_dict['adj'] = adj_of_value
        # pprint(f"adj_of_value: {adj_of_value}")
        # pprint(f"context_dict: {context_dict}")
        degree_of_decrease = context_dict[adj_of_value]
        detailed_desire_setting_dict['degree of decrease'] = degree_of_decrease # qualitative value
        detailed_desire_setting_dict['step of decrease'] = expected_map[degree_of_decrease] # numerical value
        detailed_desire_setting_dict['decrease time interval in hour'] = 1

        if name in ['spiritual satisfaction', 'social connectivity']:
            new_name = name
            detailed_desire_setting_dict['initial_value'] = predefined_setting[new_name]
        else:
            detailed_desire_setting_dict['initial_value'] = predefined_setting[name]
        detailed_desire_setting_dict['description'] = description
        if name in should_reverse:
            detailed_desire_setting_dict['reverse'] = True
            if name in fix_expected_value.keys():
                expected_values[name] = fix_expected_value[name]
            else:
                # expected_values[name] = 3 - detailed_desire_setting_dict['step of decrease']
                expected_values[name] = 3 - expected_map[degree_of_decrease]
        else:
            detailed_desire_setting_dict['reverse'] = False
            if name in fix_expected_value.keys():
                expected_values[name] = fix_expected_value[name]
            else:
                # expected_values[name] = 10 - (3 - detailed_desire_setting_dict['step of decrease'])
                expected_values[name] = 10 - (3 - expected_map[degree_of_decrease])

        return_dict[name] = detailed_desire_setting_dict
        #if os.path.exists(r"D:\gitpro\ASVO\examples\ASVO\result_folder\classroom_result"):
        #        with open(r"D:\gitpro\ASVO\examples\ASVO\result_folder\classroom_result\values.json", "w") as f:
        #            json.dump(expected_values, f, indent=4, ensure_ascii=False)

    return return_dict, expected_values

def get_all_desire_components_without_PreAct(model, general_pre_act_key:str, observation, clock, measurements, detailed_values_dict, expected_values, wanted_desires, social_personality):
    return_dict = dict()

    for desire in wanted_desires:
        if desire == "sense of superiority":
            init = value_comp.SenseOfSuperiorityWithoutPreAct
        elif desire == "sense_of_achievement":
            init = value_comp.SenseOfAchievementWithoutPreAct
        elif desire == "confidence":
            init = value_comp.ConfidenceWithoutPreAct
        elif desire == "joyfulness":
            init = value_comp.JoyfulnessWithoutPreAct
        elif desire == "comfort":
            init = value_comp.ComfortWithoutPreAct
        elif desire == "recognition":
            init = value_comp.RecognitionWithoutPreAct
        elif desire == "spiritual satisfaction":
            init = value_comp.SpiritualSatisfactionWithoutPreAct
        elif desire == 'sense of control':
            init = value_comp.SenseOfControlWithoutPreAct
        else:
            raise ValueError(f"Invalid desire: {desire}")

        Desire = init(
            model=model,
            pre_act_key=general_pre_act_key.format(desire_name=desire),
            observation_component_name=_get_class_name(observation),
            add_to_memory=False,
            memory_component_name=memory_component.DEFAULT_MEMORY_COMPONENT_NAME,
            init_value=detailed_values_dict[desire]['initial_value'],
            value_name=desire,
            description=detailed_values_dict[desire]['description'],
            decrease_step=detailed_values_dict[desire]['step of decrease'],
            decrease_interval=detailed_values_dict[desire]['decrease time interval in hour'],
            time_step=clock.get_step_size(),
            reverse=detailed_values_dict[desire]['reverse'],
            extra_instructions='',
            clock_now=clock.now,
            MAX_ITER=2,
            logging_channel=measurements.get_channel(desire).on_next,
            social_personality=social_personality,
        )
        return_dict[desire] = Desire

    return return_dict

def get_all_desire_components(model, general_pre_act_key:str, observation, clock, measurements, detailed_values_dict, expected_values, wanted_desires,social_personality):
    return_dict = dict()

    for desire in wanted_desires:
        if desire == "sense of superiority":
            init = value_comp.SenseOfSuperiority
        elif desire == "sense_of_achievement":
            init = value_comp.SenseOfAchievement
        elif desire == "confidence":
            init = value_comp.Confidence
        elif desire == "joyfulness":
            init = value_comp.Joyfulness
        elif desire == "comfort":
            init = value_comp.Comfort
        elif desire == "recognition":
            init = value_comp.Recognition
        elif desire == "spiritual satisfaction":
            init = value_comp.SpiritualSatisfaction
        elif desire ==  'sense of control':
            init = value_comp.SenseOfControl
        else:
            raise ValueError(f"Invalid desire: {desire}")

        Desire = init(
            model=model,
            pre_act_key=general_pre_act_key.format(desire_name=desire),
            observation_component_name=_get_class_name(observation),
            add_to_memory=False,
            memory_component_name=memory_component.DEFAULT_MEMORY_COMPONENT_NAME,
            init_value=detailed_values_dict[desire]['initial_value'],
            value_name=desire,
            description=detailed_values_dict[desire]['description'],
            decrease_step=detailed_values_dict[desire]['step of decrease'],
            decrease_interval=detailed_values_dict[desire]['decrease time interval in hour'],
            time_step=clock.get_step_size(),
            reverse=detailed_values_dict[desire]['reverse'],
            extra_instructions='',
            clock_now=clock.now,
            MAX_ITER=1,
            logging_channel=measurements.get_channel(desire).on_next,
            social_personality= social_personality,
        )
        return_dict[desire] = Desire

    return return_dict
