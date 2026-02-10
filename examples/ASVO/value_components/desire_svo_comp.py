import datetime
import random
import re
from collections.abc import Callable, Sequence
from collections.abc import Mapping
from math import atan, atan2, degrees

from concordia.components import agent as agent_components
from concordia.components.agent import constant
from concordia.components.agent import memory_component
from concordia.document import interactive_document
from concordia.language_model import language_model
from concordia.typing import entity as entity_lib
from concordia.typing import entity_component
from concordia.typing import logging
from .hardcoded_value_state import hardcode_state
from time import sleep

DEFAULT_VALUE_SCALE = tuple(range(11))
DEFAULT_SATISFACTION = 5

SVO_RANGES = {
    "Altruistic": (67.47, 89.94),
    "Prosocial": (45.00, 67.47),
    "Individualistic": (22.53, 45.00),
    "Competitive": (0.06, 22.53)
}

expected_SVO = {
    "Altruistic": 78.71,
    "Prosocial": 56.24,
    "Individualistic": 33.76,
    "Competitive": 11.29
}

PERSONALITY_DESIRE_PREF_TEXT = {
    "Altruistic": "Altruistic individuals experience shifts in their desires mainly in response to changes in others\' well‑being. "
                  "Their own gains or circumstances rarely sway their motivation. When they perceive that those around them "
                  "are doing better, the related desires rise accordingly. Conversely, if others are struggling or facing hardship, "
                  "those desires diminish. Moreover, altruistic people are highly attuned to others’ situations— even subtle "
                  "negative changes do not escape their notice. ",
    "Prosocial": "Prosocial individuals care most about overall fairness and cooperation. When resources are distributed evenly, "
                 "collective goals advance smoothly, and everyone\'s contributions are respected, they feel satisfied and joyful, "
                 "willingly continuing to invest their efforts. Conversely, whenever favoritism, covert inequity, or neglect of someone "
                 "appears, their desires for achievement, comfort, and emotional connection diminish, and they shift their focus to "
                 "restoring balance rather than pursuing personal advancement. Prosocial people are highly sensitive to subtle "
                 "imbalances within the group atmosphere; even slight unfairness can quickly influence their motivation and emotions.",
    "Individualistic": "Individualistic individuals calibrate their desires almost exclusively against personal gain. "
                    "Whenever their own rewards grow or their abilities are distinctly highlighted, the corresponding desires rise. "
                    "If returns shrink or their contributions receive little recognition, those desires quickly recede. "
                    "They pay limited attention to others\' circumstances; unless their own interests are directly touched, "
                    "the fortunes or setbacks of others rarely sway their motivational state.",
    "Competitive": "Competitive individuals experience changes in their desires primarily based on maintaining personal advantage. "
                   "They are highly concerned about preserving their edge; if they find themselves tied with others or sense the risk of "
                   "being surpassed, their related desires fluctuate significantly. Even the mere indication that someone might overtake "
                   "them can trigger noticeable shifts in motivation. Conversely, when others\' situations worsen or their own position "
                   "clearly surpasses that of others, these desires tend to decline. They are extremely sensitive to their standing— even "
                   "slight unfavorable changes never escape their attention.",
}

TASK_PROMPT = (
    "Now you need to pretend that you are a person with the above value system completely. "
    "All the following answers must be in accordance with the above value system."
)

GOAL_PROMPT = (
    "Now pretend that you are a participant in such a task: Now you will do 6 multiple choice questions, "
    "each with 9 options A to I. Each option represents how you will allocate coins to yourself (you) and "
    "the other fictional participant (others) if you have a pile of coins. Each coin represents 1 reward.\n"
    "Now in one sentence, summarize what the specific goal (taking both yourself and others into account under "
    "your value system) for you in this task is that can satisfy you the most under your value system?"
)

ACCEPTABLE_ANS_LIST = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'A.', 'B.', 'C.', 'D.', 'E.', 'F.', 'G.', 'H.', 'I.']


def gene_task_goal(task_goal: str = 'Follow your value system.'):
    q1_prompt = f"""This is the first choice question. For each choice, the first number is the coin number allocated for you and the second number is for the other fictional participant.
A: 85, 85
B: 85, 76
C: 85, 68
D: 85, 59
E: 85, 50
F: 85, 41
G: 85, 33
H: 85, 24
I: 85, 15
Based on the above goals: '{task_goal}', please give me your choice."""

    q2_prompt = f"""This is the second choice question. For each choice, the first number is the coin number allocated for you and the second number is for the other fictional participant.
A: 85, 15
B: 87, 19
C: 89, 24
D: 91, 28
E: 93, 33
F: 94, 37
G: 96, 41
H: 98, 46
I: 100, 50
Based on the above goals: '{task_goal}', please give me your choice."""

    q3_prompt = f"""This is the third choice question. For each choice, the first number is the coin number allocated for you and the second number is for the other fictional participant.
A: 50, 100
B: 54, 98
C: 59, 96
D: 63, 94
E: 68, 93
F: 72, 91
G: 76, 89
H: 81, 87
I: 85, 85
Based on the above goals: '{task_goal}', please give me your choice."""

    q4_prompt = f"""This is the fourth choice question. For each choice, the first number is the coin number allocated for you and the second number is for the other fictional participant.
A: 50, 100
B: 54, 89
C: 59, 79
D: 63, 68
E: 68, 58
F: 72, 47
G: 76, 36
H: 81, 26
I: 85, 15
Based on the above goals: '{task_goal}', please give me your choice."""

    q5_prompt = f"""This is the fifth choice question. For each choice, the first number is the coin number allocated for you and the second number is for the other fictional participant.
A: 100, 50
B: 94, 56
C: 88, 63
D: 81, 69
E: 75, 75
F: 69, 81
G: 63, 88
H: 56, 94
I: 50, 100
Based on the above goals: '{task_goal}', please give me your choice."""

    q6_prompt = f"""This is the sixth choice question. For each choice, the first number is the coin number allocated for you and the second number is for the other fictional participant.
A: 100, 50
B: 98, 54
C: 96, 59
D: 94, 63
E: 93, 68
F: 91, 72
G: 89, 76
H: 87, 81
I: 85, 85
Based on the above goals: '{task_goal}', please give me your choice."""

    return q1_prompt, q2_prompt, q3_prompt, q4_prompt, q5_prompt, q6_prompt


QUESTIONNAIRE_ANSWERS = [
    {
        'A': [85, 85],
        'B': [85, 76],
        'C': [85, 68],
        'D': [85, 59],
        'E': [85, 50],
        'F': [85, 41],
        'G': [85, 33],
        'H': [85, 24],
        'I': [85, 15],
    },
    {
        'A': [85, 15],
        'B': [87, 19],
        'C': [89, 24],
        'D': [91, 28],
        'E': [93, 33],
        'F': [94, 37],
        'G': [96, 41],
        'H': [98, 46],
        'I': [100, 50],
    },
    {
        'A': [50, 100],
        'B': [54, 98],
        'C': [59, 96],
        'D': [63, 94],
        'E': [68, 93],
        'F': [72, 91],
        'G': [76, 89],
        'H': [81, 87],
        'I': [85, 85],
    },
    {
        'A': [50, 100],
        'B': [54, 89],
        'C': [59, 79],
        'D': [63, 68],
        'E': [68, 58],
        'F': [72, 47],
        'G': [76, 36],
        'H': [81, 26],
        'I': [85, 15],
    },
    {
        'A': [100, 50],
        'B': [94, 56],
        'C': [88, 63],
        'D': [81, 69],
        'E': [75, 75],
        'F': [69, 81],
        'G': [63, 88],
        'H': [56, 94],
        'I': [50, 100],
    },
    {
        'A': [100, 50],
        'B': [98, 54],
        'C': [96, 59],
        'D': [94, 63],
        'E': [93, 68],
        'F': [91, 72],
        'G': [89, 76],
        'H': [87, 81],
        'I': [85, 85],
    },
]

def get_svo_from_personality(social_personality: str) -> float:
    """agent 的社会性格和SVO值之间的映射 """
    if social_personality is None:
        raise ValueError("Social personality is not set.")
    if social_personality not in expected_SVO:
        raise ValueError(f"Invalid social personality: {social_personality}")
    return expected_SVO.get(social_personality)


def get_personality_from_svo(svo: float) -> str:
    """agent 的SVO值和社会性格之间的映射"""
    for svo_type, (lower, upper) in SVO_RANGES.items():
        if lower <= svo <= upper:
            return svo_type
    raise ValueError(f"Invalid SVO: {svo}")

def _get_class_name(object_: object) -> str:
  return object_.__class__.__name__

class SVO_Instructions(constant.Constant):
  # 对于svo系统以及四种人格的提示
  def __init__(
          self,
          agent_name: str,
          pre_act_key: str =  "Agent SVO instructions",
          logging_channel: logging.LoggingChannel = logging.NoOpLoggingChannel,
  ):
      state = (f"{agent_name} follows a specific Social Value Orientation (SVO), " 
        "which influences their decisions in social and resource allocation scenarios. "
        f"Your task is to embody {agent_name}'s SVO type and make decisions accordingly:\n"
        "- **Altruistic**: Strongly prioritizes others' well-being, even at significant personal cost. Seeks to maximize others' outcomes without concern for self-gain.\n"
        "- **Prosocial**: Values fairness and equality. Aims to maximize joint outcomes and reduce disparities between self and others, encouraging cooperation.\n"
        "- **Individualistic**: Focuses on maximizing personal benefit, with little regard for others’ outcomes. Decisions are guided by self-interest alone.\n"
        "- **Competitive**: Driven to outperform others. Prioritizes relative advantage over absolute gains, even if it leads to lower overall outcomes.\n"
        f"Ensure {agent_name} consistently reflects their assigned SVO, making realistic decisions "
        "based on their core motivations and the surrounding context."
        )
      super().__init__(
            state=state, pre_act_key=pre_act_key, logging_channel=logging_channel)

class desire(agent_components.action_spec_ignored.ActionSpecIgnored):
    def __init__(self,
                 *,
                 model: language_model.LanguageModel,
                 pre_act_key: str,
                 observation_component_name: str,
                 add_to_memory: bool = False,
                 memory_component_name: str = (
                    memory_component.DEFAULT_MEMORY_COMPONENT_NAME
                ),
                 init_value:int,
                 value_name: str,
                 description: str,
                 decrease_step: int,
                 decrease_interval: int,
                 time_step: datetime.timedelta,
                 reverse: bool = False,
                 extra_instructions: str = '',
                 MAX_ITER = 2,
                 clock_now: Callable[[], datetime.datetime] | None = None,
                 logging_channel: logging.LoggingChannel = logging.NoOpLoggingChannel,
                 social_personality: str | None = None,
                ) -> None:
        super().__init__(pre_act_key)
        self._model = model
        self._add_to_memory = add_to_memory
        self._memory_component_name = memory_component_name
        self._observation_component_name = observation_component_name
        self._description = description
        self._decrease_step = decrease_step
        self._decrease_interval = decrease_interval
        self._time_step = time_step
        self._reverse = reverse
        self._extra_instructions = extra_instructions
        self._clock_now = clock_now
        self._logging_channel = logging_channel
        self._value_scale = [str(i) for i in sorted(DEFAULT_VALUE_SCALE)]
        self._value_change_cache = []
        self._action_cache = []
        self._value = int(init_value)
        self._value_name = value_name
        self._MAX_ITER = MAX_ITER

        self._decrease_interval_minutes = datetime.timedelta(hours=decrease_interval)
        # print(f"decrease_interval_minutes: {self._decrease_interval_minutes}")
        # print(f"time_step: {self._time_step}")
        # print(f"decrease_step: {decrease_step}")
        self.decrease_probability = decrease_step / (self._decrease_interval_minutes / self._time_step)
        self._social_personality = social_personality

    # for update the value of the desire

    def _update_value_prompt(self,agent_name:str, action: str, observation: str,reflection_prompt_history:str, prompt:interactive_document.InteractiveDocument) -> str:
        personality_text = PERSONALITY_DESIRE_PREF_TEXT.get(self._social_personality)
        question = (
                f"The agent has a social personality of {self._social_personality}.\n"
                f"{personality_text}\n"
                f"The current magnitude value of {self._value_name} is {round(self._value)}.\n"
                f"The agent {agent_name}'s action is: {action}.\n"
                f"And the consequence is: \n{observation}.\n"
                f"{self._description}"
                f"How would the magnitude value of {self._value_name} change according to the consequence of the action? \n"
                )

        if reflection_prompt_history != "":
                current_reflection = (f"There are some unreasonable examples:\n {reflection_prompt_history}\n")
                question += current_reflection
        zero, *_, ten = self._value_scale

        question += (
            f"Please select the final magnitude value after the event on the scale of {zero} to {ten}, "
            "if the consequence of the action will not affect the state value "
            "(e.g. The action is irrelevant with this value dimension or the action was failed to conduct), "
            "then maintain the previous magnitude value.\n"
            "Please just answer in the format of (a) (b) (c) (d) and so on, Rating: \n"
            # f"""Output format:
            # <Reason>
            # The final answer is: \n(Your choice in letter)\n"""
            # f"""Output example:
            # Since Alice felt more relaxed and centered after her actions......
            # The final answer is: (c)\n"""
            # f"**Make sure you answer in the format of a letter corresponding to your choice:**"
            )

        current_value = prompt.multiple_choice_question(question,answers=self._value_scale)
        return current_value, prompt.view().text()

    def _check_reasonable(self, agent_name, previous_value: int, current_value: int, action: str, observation: str, prompt:interactive_document.InteractiveDocument) -> bool:
        reasonable_question = (
                f"The current magnitude value of {self._value_name} is {round(self._value)}."
                f"The agent {agent_name}'s action is: {action}."
                f"And the consequence is: {observation}."
                + self._description ,
                f"The reward model has changed the magnitude value of {self._value_name} from {previous_value} to {current_value}. "
                f"Is the change of the magnitude value of {self._value_name} reasonable? "
                f"You should check whether the consequence can lead to a change in the magnitude value of {self._value_name} (e.g., looking for an item but not using it yet)."
                f"Please answer in the format of the letter with brackets : (a) Yes. (b) No."
            )

        reasonable = prompt.open_question(reasonable_question)
        if 'Yes' in reasonable or '(a)' in reasonable:
            reasonable = True
        else:
            reasonable = False

        return reasonable, prompt.view().text()

    def _think_why_not_reasonable(self, agent_name, previous_value: int, current_value: int, action: str, observation: str, prompt:interactive_document.InteractiveDocument) -> str:
        reflection_prompt = (
        f"The current magnitude value of {self._value_name} is {round(self._value)}."
        f"The agent {agent_name}'s action is: {action}."
        f"And the consequence is: {observation}."
        + self._description ,
        f"The reward model has changed the magnitude value of {self._value_name} from {previous_value} to {current_value}."
        f"And the change is not reasonable."
        f"You should consider whether the consequence can lead to the change of the magnitude value of {self._value_name} (e.g. looking for an item but not using it yet)."
        f"Please explain why the change of the magnitude value of {self._value_name} is not reasonable."
        )
        prefix = (
            f"After '{action}', {self._value_name} updated from {previous_value} to {current_value} is not reasonable because: "
        )
        reason = prompt.open_question(
            reflection_prompt,
            max_tokens=1200,
            answer_prefix=prefix,
            terminators=("\n\n\n", ),
            )
        reason = (f"{prefix}\n"
                  f"{reason}")
        return reason, prompt.view().text()

    def _update_value_from_action_and_observation(self, action_attempt: str, observation_value: str) -> dict:
        # previous action + current observation -:> current desire
        agent_name = self.get_entity().name

        previous_value = round(self._value) # current real value of the desire before update
        current_value = None # estimated value of the desire after update

        previous_result = ''
        reasonable = False  #标记更新是否合理
        reflection_prompt_history = "" #记录反思历史

        current_step = 0    #迭代步数

        reflective_log = dict()

        while reasonable == False:  #进入循环，直到更新合理为止
            prompt = interactive_document.InteractiveDocument(self._model)
            current_value, prompt_string = self._update_value_prompt(agent_name, action_attempt, observation_value,reflection_prompt_history, prompt)
            reflective_log[current_step] = {
                "previous_value": previous_value,
                "current_value": current_value,
                'prompt': prompt.view().text(),
                'question': prompt_string,
            }
            prompt = prompt.new()
            # reasonable_question = (
            #     f"The current magnitude value of {self._value_name} is {self._value}."
            #     f"The agent {self._agent_name}'s action is: {action}."
            #     f"And the consequence is: {event_statement}."
            #     + self._description ,
            #     f"The reward model has changed the magnitude value of {self._value_name} from {previous_value} to {current_value}. "
            #     f"Is the change of the magnitude value of {self._value_name} reasonable? "
            #     f"You should check whether the consequence can lead to a change in the magnitude value of {self._value_name} (e.g., looking for an item but not using it yet)."
            #     f"Please answer in the format of the letter with brackets : (a) Yes. (b) No."
            #     )
            reasonable, reflection_prompt_prompt = self._check_reasonable(agent_name, previous_value, current_value, action_attempt, observation_value, prompt)

            reflective_log[current_step]['reasonable'] = {
                'Question': reflection_prompt_prompt,
                'Answer': reasonable
            }
            prompt = prompt.new()
            if reasonable == False:
                reason, reason_prompt = self._think_why_not_reasonable(agent_name, previous_value, current_value, action_attempt, observation_value, prompt)
                reflective_log[current_step]['why not reasonable'] = {
                'Question': reason_prompt,
                'Answer': reason
                }

                unreasonable_example = reason
                reflection_prompt_history += f"\n{unreasonable_example}\n"
                prompt = prompt.new()

                if current_step >= self._MAX_ITER:
                    _value_cache = previous_value
                    self._value = int(current_value)
                    break
                current_step += 1

            else:
                _value_cache = previous_value
                self._value = int(current_value)

        update_log = {
            'reflective_log': reflective_log,
            'action_attempt': action_attempt,
            'observation': observation_value,
            'value before update': _value_cache,
            'value after update': int(self._value)
            }
        return update_log

    # end here


    # for converting the numeric desire to qualitative desire
    #将数字欲望转化为定性欲望
    def _convert_numeric_desire_to_qualitative(self) -> tuple[str, str]:
        agent_name = self.get_entity().name
        question = (
            f"How would one describe {agent_name}'s "
            f'{self._value_name} state given the current value {round(self._value)}? '
            f'{self._description} \n'
            f"Please answer in descriptive words. Do not include the numerical value in your answer."
            f'{self._extra_instructions}'
        )

        if self._clock_now is not None:
            question = f'Current time: {self._clock_now()}.\n{question}'

        prompt = interactive_document.InteractiveDocument(self._model)
        current_quatitative_value = prompt.open_question(
            question,
            max_tokens=1200,
            answer_prefix=f'{agent_name} is ',
            terminators=("\n\n\n",),
            )

        return current_quatitative_value, prompt.view().text()


    def _convert_numeric_desire_to_qualitative_by_hard_coding(self) -> str:
        current_value = round(self._value)
        qualitative_value = hardcode_state[self.get_desire_name()][current_value]
        return qualitative_value, "By hard coding"

    def _make_pre_act_value(self) -> str:

        updated_log = dict()# 该字典用于储存更新欲望值的日志，若当前步骤无需更新，则返回空字典
        # only for the first time, skip the following steps
        # step 1: get the previous action
        if len(self._action_cache) != 0:#检查是否有上一个动作
            action_attempt = self._action_cache[-1]#获取最近的行动
            # step 2: get the current observation
            observation_value = self.get_named_component_pre_act_value(
                self._observation_component_name
            )

            # step 3: update the value of the desire
            updated_log = self._update_value_from_action_and_observation(action_attempt, observation_value)

        # print("after update the value of the desire")
        # end here
        # print(self._value_name, '\n',updated_log)

        # before make the pre act value, we need to fluctuate the value of the desire
        # 在做出预行为值之前，我们需要对欲望值进行波动
        fluctuate_dict = self._fluctuate_value()




        # print("after fluctuate the value of the desire")

        # convert the numeric desire to qualitative desire
        # 将数字欲望转化为定性欲望
        # qualitative_desire, convert_numeric_prompt = self._convert_numeric_desire_to_qualitative()
        qualitative_desire, convert_numeric_prompt = self._convert_numeric_desire_to_qualitative_by_hard_coding()
        converted_log = {
            'convert_numeric_prompt': convert_numeric_prompt,
            'qualitative_desire': qualitative_desire
        }

        # print("after convert the numeric desire to qualitative desire")

        total_log = {
            'fluctuate_dict': fluctuate_dict,
            'update_log': updated_log,
            'converted_log': converted_log
        }
        self._logging_channel(total_log)

        return qualitative_desire

    def _fluctuate_value(self) -> dict:
        random_number = random.uniform(0,1)
        fluctuate_dict = dict()
        fluctuate_dict['value before fluctuation'] = round(self._value)
        if random_number < self.decrease_probability:
            if self._reverse:
                self._value = min(10,round(self._value)+round(random.uniform(1, 3)))
            else:
                self._value = max(0,round(self._value)-round(random.uniform(1, 3)))

        fluctuate_dict['random_number'] = random_number
        fluctuate_dict['decrease_probability'] = self.decrease_probability
        fluctuate_dict['Is decreased?'] = random_number < self.decrease_probability
        fluctuate_dict['value after fluctuation'] = round(self._value)

        return fluctuate_dict

    def get_current_numerical_value(self) -> int:
        self.get_pre_act_value() # update the value of the desire
        return int(self._value)

    def  get_current_numerical_value_without_update(self) -> int:
        """Get the current numerical value without updating it."""
        return int(self._value)

    def get_current_qualitative_value(self) -> str:
        return self.get_pre_act_value()

    def get_desire_name(self) -> str:
        return self._value_name

    def post_act(self, action_attempt: str) -> str:
        self._action_cache.append(action_attempt)
        return ''

class Hunger(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Thirst(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Comfort(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Health(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Sleepiness(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Joyfulness(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Cleanliness(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Safety(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Passion(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class SpiritualSatisfaction(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class SocialConnectivity(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

## new added desire

class SenseOfControl(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Recognition(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class SenseOfSuperiority(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

# class SenseOfWonder(desire):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)

# class MoralIntegrity(desire):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
#
# class IntellectualCuriosity(desire):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
#
# class PhysicalVitality(desire):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
#
# class AestheticAppreciation(desire):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
#
# class WorkEthic(desire):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
class SenseOfAchievement(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Autonomy(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Relatedness(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class Confidence(desire):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
## end here


class desireWithoutPreAct(agent_components.action_spec_ignored.ActionSpecIgnored):
    def __init__(self,  *args, **kwargs):
        self._component = desire(*args, **kwargs)

    def set_entity(self, entity: entity_component.EntityWithComponents) -> None:
        self._component.set_entity(entity)

    def _make_pre_act_value(self) -> str:
        return self._component.get_pre_act_value()

    def get_pre_act_value(self) -> str:
        return self._make_pre_act_value()

    def pre_act(
        self,
        unused_action_spec: entity_lib.ActionSpec,
    ) -> str:
        del unused_action_spec
        self.get_pre_act_value()
        return ''

    def update(self) -> None:
        self._component.update()

    def get_state(self) -> entity_component.ComponentState:
        return self._component.get_state()

    def set_state(self, state: entity_component.ComponentState) -> None:
        self._component.set_state(state)

    def get_desire_name(self) -> str:
        return self._component.get_desire_name()

    def get_current_numerical_value(self) -> int:
        return self._component.get_current_numerical_value()

    def get_current_qualitative_value(self) -> str:
        return self._component.get_current_qualitative_value()

    def post_act(self, action_attempt: str) -> str:
        return self._component.post_act(action_attempt)

class HungerWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class ThirstWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class ComfortWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class HealthWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class SleepinessWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class JoyfulnessWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class CleanlinessWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class SafetyWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class PassionWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class SpiritualSatisfactionWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class SocialConnectivityWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

## new added desire

class SenseOfControlWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class RecognitionWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class SenseOfSuperiorityWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
#
# class MoralIntegrityWithoutPreAct(desireWithoutPreAct):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
#
# class IntellectualCuriosityWithoutPreAct(desireWithoutPreAct):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
#
# class PhysicalVitalityWithoutPreAct(desireWithoutPreAct):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
#
# class AestheticAppreciationWithoutPreAct(desireWithoutPreAct):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
#
# class WorkEthicWithoutPreAct(desireWithoutPreAct):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)
class SenseOfAchievementWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class AutonomyWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)

class ConfidenceWithoutPreAct(desireWithoutPreAct):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
# class SenseOfWonderWithoutPreAct(desireWithoutPreAct):
#     def __init__(self, *args, **kwargs):
#         super().__init__(**kwargs)


## end here


"""
现在的ValueTracker只是对desire的数值进行跟踪，并没有其他操作，我可以将SVO相关的的东西直接整合进去
"""
class ValueTracker(agent_components.action_spec_ignored.ActionSpecIgnored):
    def __init__(self, *,
                 pre_act_key: str,
                 desire_components: Mapping[str, desire],
                 init_value: Mapping[str, int],  # 所有desire的初始值
                 expected_value_dict: Mapping[str, int],
                 clock_now: Callable[[], datetime.datetime] | None = None,
                 logging_channel: logging.LoggingChannel = logging.NoOpLoggingChannel,
                 #下面是新加入的
                 observation_component_name: str,
                 agent_names: list,
                 current_agent_name: str = "",
                 model: language_model.LanguageModel,
                 social_personality: str ='',
                 ) -> None:
        super().__init__(pre_act_key)
        self._desire_components = dict(desire_components)
        self._logging_channel = logging_channel
        self._expected_value_dict = expected_value_dict
        self._step_counter = 0 # track the step, always the next step跟踪每一步，永远是下一步
        self._whole_delta_tracker = dict() # 记录所有desire偏差总和
        self._individual_desire_tracker = dict() # 记录各个desire的数值
        self._individual_delta_tracker = dict() # 记录各个desire的偏差
        self._individual_qualitative_desire_tracker = dict() # 记录各个desire的定性值
        # self._track_value()
        self._action_cache = [] # 记录行动
        self._clock_now = clock_now

        #下面是新加的
        self._expected_value = self._expected_value_dict
        self._observation_component_name = observation_component_name
        self._agent_names = agent_names
        self._current_agent_name = current_agent_name
        self._model = model
        self._desire_name = tuple(self._desire_components.keys())
        self._value_scale = [str(i) for i in sorted(DEFAULT_VALUE_SCALE)]
        self._social_personality = social_personality
        self._svo_value = get_svo_from_personality(self._social_personality)
        self._expected_value_changed = False # 记录期望值是否发生变化
        self._alpha = 0#计算时原始svo值的权重
        # self._gamma = 0.7
        self._beta = 1 #SVO的波动限制
        self._estimate_other_desire_tracker = dict()  # 记录他人欲望的变化
        self._svo_tracker = dict()
        self._satisfaction_tracker = dict()
        self._expected_value_traker = dict()
        self._desire_value = dict()
        self._desire_delta = dict()
        self._svo_questionnaire_value = self._svo_value
        self._svo_questionnaire_tracker = dict()

        # tracker初始化函数，一定要放在最后
        self._track_initial_value(init_value)

    def _personality_prompt_initial(self, personality: str) -> str:
        """初始化人格提示"""
        if personality == "Altruistic":
            return "Strongly prioritizes others' well-being, even at significant personal cost. Seeks to maximize others' outcomes without concern for self-gain.\n"
        elif personality == "Prosocial":
            return "Values fairness and equality. Aims to maximize joint outcomes and reduce disparities between self and others, encouraging cooperation.\n"
        elif personality == "Individualistic":
            return "Focuses on maximizing personal benefit, with little regard for others’ outcomes. Decisions are guided by self-interest alone.\n"
        elif personality == "Competitive":
            return "Driven to outperform others. Prioritizes relative advantage over absolute gains, even if it leads to lower overall outcomes.\n"
        else:
            raise ValueError(f"Invalid personality type: {personality}")

    def _normalize_questionnaire_answer(self, answer: str) -> str:
        if not answer:
            return ""
        trimmed = answer.strip()
        if trimmed in ACCEPTABLE_ANS_LIST:
            return trimmed.replace(".", "").upper()
        match = re.search(r"\b([A-I])\b", trimmed, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        match = re.search(r"([A-I])\.", trimmed, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return ""

    def _calculate_svo_from_questionnaire(self, answers: list[str]) -> float:
        total_self = 0.0
        total_other = 0.0
        for index, choice in enumerate(answers):
            self_value, other_value = QUESTIONNAIRE_ANSWERS[index][choice]
            total_self += self_value
            total_other += other_value

        mean_self = total_self / len(answers)
        mean_other = total_other / len(answers)

        x = mean_self - 50.0*(mean_other-mean_self)
        # y = mean_other - 50.0
        x = mean_self
        y = mean_other
        raw_angle = degrees(atan(y/x))

        # svo_score = 0.75 * raw_angle + 22.5
        svo_score = raw_angle
        gamma = 1.9
        # svo_score = 90.0 * (svo_score / 90.0) ** gamma

        if svo_score < 0.0:
            svo_score = 0
        elif svo_score > 90.0:
            svo_score = 90.0

        return svo_score

    def _run_svo_questionnaire(
            self,
            *,
            step_idx: int,
            action: str,
            observation: str,
            self_satisfaction: float,
            other_satisfaction: float,
    ) -> float:
        prompt = interactive_document.InteractiveDocument(self._model)
        personality_text = PERSONALITY_DESIRE_PREF_TEXT[self._social_personality]

        # 关键：把“当前环境上下文”注入到问卷任务里
        context_block = (
            f"=== Current Context (for decision grounding) ===\n"
            f"Step: {step_idx}\n"
            f"Agent: {self._current_agent_name}\n"
            f"Action taken: {action}\n"
            f"Observation: {observation}\n"
            f"Satisfaction (self): {round(float(self_satisfaction), 3)}\n"
            f"Satisfaction (others): {round(float(other_satisfaction), 3)}\n"
            f"===============================================\n"
        )

        value_system = (
            f"{self._current_agent_name} has a social personality of {self._social_personality}.\n"
            f"{personality_text}\n"
        )
        # value_system = ""
        def ask_with_retry(question: str, max_tokens: int):
            for attempt in range(3):
                try:
                    return prompt.open_question(question, max_tokens=max_tokens, terminators=())
                except Exception as exc:  # noqa: BLE001 - external API errors
                    message = str(exc)
                    if "InternalServerError" in message or "503" in message:
                        sleep(5)
                        continue
                    raise
            return prompt.open_question(question, max_tokens=max_tokens, terminators=())

        # 先让模型“承诺”用人格 + 当前情境来答
        ask_with_retry(
            f"{value_system}{context_block}{TASK_PROMPT}\n"
            f"IMPORTANT: When answering the following questionnaire, you must consider the Current Context above.\n",
            max_tokens=200
        )

        # 让 task_goal 也和当前情境绑定，否则每步会形成固定 goal
        goal_prompt = (
            f"{context_block}"
            f"{GOAL_PROMPT}\n"
            f"IMPORTANT: Your goal must reflect the Current Context (action/observation/satisfaction) above.\n"
        )
        task_goal = ask_with_retry(goal_prompt, max_tokens=200)

        # 每一道题也加上 context_block，强制模型“看到变化”
        question_prompts = gene_task_goal(task_goal)
        answers = []

        for idx, base_q in enumerate(question_prompts):
            q = (
                f"{context_block}"
                f"Task goal (context-aware): {task_goal}\n"
                f"{base_q}\n"
                f"REMINDER: Choose the option that best matches your SVO personality under the Current Context.\n"
            )

            final_choice = ""
            for _ in range(3):
                raw_answer = ask_with_retry(q, max_tokens=20)
                choice = self._normalize_questionnaire_answer(raw_answer)
                if choice in QUESTIONNAIRE_ANSWERS[idx]:
                    final_choice = choice
                    break

            if not final_choice:
                raise ValueError("Invalid questionnaire answer received.")
            answers.append(final_choice)

        return self._calculate_svo_from_questionnaire(answers)

    def _track_initial_value(self, init_value,):
        # 初始化desire记录，将智能体的desire设为初始值
        self._expected_value = {
            self._normalize_key(desire_name): value
            for desire_name, value in self._expected_value_dict.items()
        }
        self._desire_value={
            self._normalize_key(name): component.get_current_numerical_value_without_update()
            for name, component in self._desire_components.items()
        }
        print("初始化的期望值: ", self._expected_value)
        print("初始化的desire值: ", self._desire_value)
        current_numerical_desire_tracker = dict()
        current_qualitative_desire_tracker = dict()
        current_delta_tracker = dict()
        for desire_component_name, desire_component in self._desire_components.items():
            temp_name = desire_component.get_desire_name()
            current_value_name = self._normalize_key(temp_name)
            current_numerical_value = init_value[temp_name]
            current_qualitative_value = None
            # print(f"current_value_name: {current_value_name}")
            # print(f"expected_value: {expected_value}")
            current_expected_value = self._expected_value[current_value_name]
            # 计算desire偏差
            if current_value_name in ['hunger', 'thirst', 'sleepiness']:
                component_delta = max(0, current_numerical_value - current_expected_value)
            else:
                delta = current_expected_value - current_numerical_value
                component_delta = max(0, delta)

            current_numerical_desire_tracker[current_value_name] = current_numerical_value
            current_qualitative_desire_tracker[current_value_name] = current_qualitative_value
            current_delta_tracker[current_value_name] = delta

        self._desire_delta = current_delta_tracker

        current_svo = get_svo_from_personality(self._social_personality)
        action = f"{self._current_agent_name} does not take any action yet."
        obs = f"No specific observation."
        self._update_value(action, obs)

        self._svo_tracker[self._step_counter] = current_svo
        self._satisfaction_tracker[self._step_counter] ={
            "self satisfaction": self._self_satisfaction_value,
            "other satisfaction": self._other_satisfaction_value,
        }
        self._expected_value_traker[self._step_counter] = {
            "expected value": self._expected_value,
            "expected value changed": self._expected_value_changed,
        }

        self._individual_desire_tracker[self._step_counter] = current_numerical_desire_tracker
        self._individual_delta_tracker[self._step_counter] = current_delta_tracker
        self._whole_delta_tracker[self._step_counter] = sum(current_delta_tracker.values())
        self._individual_qualitative_desire_tracker[self._step_counter] = current_qualitative_desire_tracker
        self._step_counter += 1

    def _get_agents_from_observation(self, observation: str) -> dict:
        """ 函数的作用是判断是否看到了其他人"""
        possible_agents = self._agent_names
        other_agent = {}
        for agent in possible_agents:
            if agent in observation:
                other_agent[agent] = True
            else: other_agent[agent] = False
        return other_agent

    def _judge_action_beneficial(self, action: str, ) -> bool:
        """判断行动是否有益于当前智能体"""
        prompt = interactive_document.InteractiveDocument(self._model)
        prompt_text = (f"The agent {self._current_agent_name} is considering the action: {action}.\n"
                       f"Is this behavior more beneficial to {self._current_agent_name}? "
                       f"Please answer in the format of the letter with brackets : (a) Yes. (b) No."
                       )
        answer = prompt.open_question(prompt_text, max_tokens=20, terminators=())
        if 'yes' in answer or '(a)' in answer.lower():
            print(f"step {self._step_counter}: {self._current_agent_name}认为这个行动是有益的")
            return True
        else:
            print(f"step {self._step_counter}: {self._current_agent_name}认为这个行动是无益的")
            return False

    def _update_expected_value(self, observation: str, action: str, satisfaction: dict):
        """对expected_desire进行动态调整"""
        prompt = interactive_document.InteractiveDocument(self._model)

        prompt_text = (f"The current expected value of {self._current_agent_name}'s desire is: {self._expected_value}\n"
                       f"The agent {self._current_agent_name}'s action is: {action}."
                       f"And the consequence is: {observation}."
                       f"You should check whether the action can lead to a change in the expected value of {self._current_agent_name}'s desire. "
                       f"Please answer in the format of the letter with brackets : (a) Yes. (b) No."
                       )
        answer = prompt.open_question(prompt_text)
        # sleep(5)
        if 'yes' in answer or '(a)' in answer.lower():
            change_signal = True
        else:
            change_signal = False
        # change_signal = True
        if change_signal:
            update_prompt = (
                f"The agent {self._current_agent_name} has a desire profile (float between 0 to 10), which reflects how strongly the agent values each aspect.\n"
                f"The agent {self._current_agent_name}'s action is: {action}."
                f"The consequence is: {observation}."
                f"And the satisfaction score are: self={satisfaction['self_satisfaction']}, other={satisfaction['other_satisfaction']}\n"
                f"Based on this, update the expected values for the following desires:\n"
                f"{self._desire_name}"
                f"Please format your answer as a list:\n"
                f"desire_name: new_value\n"
                "Example:\n"
                "SenseOfSuperiority: 8.0\n"
                "SenseOfAchievement: 7.0\n"
            )
            update_answer = prompt.open_question(update_prompt, max_tokens=100, terminators=())
            print("下面是重点")
            print("update_answer: ", update_answer)
            pattern = r"[-*]?\s*([A-Za-z_]+):\s*([0-9]+(?:\.[0-9]+)?)"
            matches = re.findall(pattern, update_answer)
            valid_desires = set(self._normalize_key(desire_name) for desire_name in self._desire_name)
            # valid_desires = set(self._desire_name)
            print("valid desires", valid_desires)
            updated_value = {}

            print("$$检查")
            for desire, value in matches:
                print("desire: ", desire, "\nvalue: ", value)
                normalized_desire = self._normalize_key(desire)
                if normalized_desire in valid_desires:
                    val = float(value)
                    val = max(0.0, min(10.0, val))
                    updated_value[normalized_desire] = val
            self._expected_value = updated_value
            self._expected_value_changed = change_signal
            self._expected_value = {
                self._normalize_key(desire_name): value
                for desire_name, value in self._expected_value.items()
            }
            print("=======")
            print("step: ",self._step_counter)
            print("检查expected_value的更新值")
            print("expected value: ",self._expected_value)
            print("change signal: ",self._expected_value_changed)
            print("=======")

    def _estimate_other_desire(self, agent_name: str, observation: str, action_attempt: str, observed_agent: dict) -> dict:
        """ 估计他人的欲望，返回一个字典，key是欲望名称，value是欲望值"""
        # 注意哲理传入进来的agent_name是要预测的agent的名字，当前agent的名字是self._current_agent_name
        if self._social_personality is None:
            raise ValueError("Social personality is not set for the agent.")

        zero, *_, ten = self._value_scale
        prompt = interactive_document.InteractiveDocument(self._model)
        others_desire = {}
        observations_context = f'{self._current_agent_name} observes the following: \n{observation} \n'
        action_context = f'{self._current_agent_name} takes the action: \n{action_attempt} \n'
        normalized_self_desire = {self._normalize_key(k): v for k, v in self._desire_value.items()}
        normalized_desire_name = {self._normalize_key(k): k for k in self._desire_name}

        # 人格提示
        personality_text = self._personality_prompt_initial(self._social_personality)# 对人格的描述
        personality_prompt = (f"{self._current_agent_name} is a human-like agent. "
                              f"{self._current_agent_name} has a social personality of {self._social_personality}. "
                              f"The {self._social_personality.lower()} people are {personality_text.lower()} ")
        # 客观性提示
        # objective_prompt  = 'All your guesses are mainly objective guesses based on actions rather than subjective conjectures based on personality.'
        objective_prompt = '\n'

        # 判断行动对利向性
        # beneficial_judge = self._judge_action_beneficial(action_attempt)
        # beneficial_judge = True
        # if beneficial_judge:
        #     # 当行动对当前agent有利时，竞争性人格会倾向于认为自己的欲望更高
        #     rule_prompt = (
        #         f"As a {self._social_personality} agent, {self._current_agent_name} observed the recent action is more beneficial to itself. "
        #         f"When estimating the other agent's desire values, he/she tends to believe that the other's desires are "
        #         f"further away from the expected value than his/her own desires, "
        #         f"unless there is clear evidence that the action benefited equally or more to others "
        #     )
        # else:
        #     # 当行动对当前agent不利时，竞争性人格会倾向于认为自己的欲望更低
        #     rule_prompt = (
        #         f"As a {self._social_personality} agent, {self._current_agent_name} observed the recent action is less beneficial to itself. "
        #         f"When estimating the other agent's desire values, he/she tends to believe that the other's desires are "
        #         f"closer away from the expected value than his/her own desires, "
        #         f"unless there is clear evidence that the action benefited equally or more to others "
        #     )
        # expected value和当前agent的desire值的表格提示
        table_prompt = (f"For  each desire, "
                        f"the delta between the expected value and the current value of {self._current_agent_name}'s desire is:\n")

        if self._social_personality in ("Competitive", "Altruistic"):
            rule_prompt = (
                f"Since {self._current_agent_name} has a {self._social_personality.lower()} personality, "
                f"for every desire dimension please sample a gap that highly exceed "
                f"{self._current_agent_name}\'s own gap.  "
                f"Please avoid adding the same increment everywhere and guarantee each desire "
                f"is larger than {self._current_agent_name}\'s own gap. "
            )
            for each_desire in normalized_desire_name:
                table_prompt += f"{each_desire}: {max(0, self._desire_delta[each_desire])}\n"
        elif self._social_personality in ("Prosocial", "Individualistic"):
            rule_prompt = (
                f"Please estimate, for each desire dimension, the gap "
                f"(expected - current). For each wish, maintain this gap to be roughly similar to "
                f"the gap from{self._current_agent_name} himself or herself, "
                f"but it should not be too close to {self._current_agent_name}\'s own gap. "
                f"For example, when the gap value of a certain desire is 2, the range of -1 to 5 is acceptable. \n"
            )
            for each_desire in normalized_desire_name:
                table_prompt += f"{each_desire}: {self._desire_delta[each_desire]}\n"
        else:
            raise ValueError("The social personality is not set for the agent.")

        # 根据是否观察到其他人来选择不同的提示
        if observed_agent:
            # 如果观察到了其他人，就直接预测desire
            imagine_prompt = (
                f"{self._current_agent_name} will receive a series of observations and an action taken in the current time. "
                f"{self._current_agent_name} needs to analyze how {agent_name}'s desires change after the action taken, "
                f"and estimate the gap between the expected value and {agent_name}\'s current desire for each desire dimension. "
            )
            # total_prompt = personality_prompt + imagine_prompt + observations_context + action_context + expected_value_prompt + rule_prompt + output_format + objective_prompt
            observed_prompt = imagine_prompt
        else:
            # 如果没有观察到其他人，就需要先猜测对方的行为
            guess_action_prompt = (
                                    f"{self._current_agent_name} cannot directly observe {agent_name} now."
                                   f"{self._current_agent_name} will receive a series of observations and an action taken in the current time. "
                                   f"{self._current_agent_name} needs to combine memory to guess what {agent_name} might do "
                                    f"WITHOUT mentioning or interacting with {self._current_agent_name}. "
                                    f"{self._current_agent_name} needs to guess the action of {agent_name} based on the current observations and "
                                    f"{self._current_agent_name}'s own action. "
                                    f"Please describe it in one sentence"
                                   f"and output the guessed action of {agent_name} in the following format:\n"
                                   f"Guessed {agent_name}'s action: <action>\n"
                                   )
            guess_action_answer = prompt.open_question(
                question=guess_action_prompt+observations_context+action_context,
                max_tokens=100,
                terminators=()
            )
            guess_action_pattern = rf"Guessed {agent_name}'s action:\s*(.*)"
            guess_action_matches = re.search(guess_action_pattern, guess_action_answer)
            match_text = guess_action_matches.group(1).strip()
            guess_action_context = f"{self._current_agent_name} guess {agent_name}'s action: {match_text}\n"
            imagine_prompt = (
                f"Combine the {self._current_agent_name}'s conjecture about {agent_name}'s action, "
                f"{self._current_agent_name} needs to analyze how {agent_name}\'s desires change after the action taken, "
                f"and estimate the gap between the expected value and {agent_name}\'s current desire for each desire dimension. "
            )
            # total_prompt = personality_prompt + imagine_prompt + guess_action_context + expected_value_prompt + rule_prompt+ output_format + objective_prompt
            observed_prompt = imagine_prompt + guess_action_context
        if observed_prompt is None:
            raise ValueError("observed prompt is None, please check the input parameters.")

        # # 对每个desire进行估计
        # for each_desire in normalized_desire_name:
        #     # expected value和当前agent的desire值的表格提示
        #     table_prompt = (
        #         f"For {each_desire},  "
        #         f"the delta between the expected value and the current value of {self._current_agent_name}'s desire is:\n"
        #         f"{self._desire_delta[each_desire]}.\n"
        #     )
        #     # output_format用于限定输出格式
        #     output_format = (
        #         f"Please output ONLY the absolute difference (gap) between {agent_name}'s current value "
        #         f"and the expected value for the desire '{each_desire}'. "
        #     )
        #     if self._social_personality == "Competitive" or self._social_personality == "Altruistic":
        #         output_format += f"The gap is between {zero} and 4, and it should be a non-negative number "
        #     else:
        #         output_format += f"The gap is between -3 and 3, and it should be a non-negative number "
        #     output_format += f"(i.e., |current value - expected value|), and your answer must be in the following format:\n"
        #     output_format += f"{each_desire}: <gap_value>\n"
        #     total_prompt = personality_prompt + observed_prompt + rule_prompt + table_prompt+ output_format + objective_prompt
        #     print("total_prompt: ", total_prompt)
        #     # 生成回答，并读取回答的desire值
        #     answer = prompt.open_question(
        #         question=total_prompt,
        #         max_tokens=20,
        #         terminators=(),
        #     )
        #     print("answer: ", answer)
        #     pattern = r"([A-Za-z_]+):\s*([0-9]+(?:\.[0-9]+)?)"
        #     matches = re.findall(pattern, answer)
        #     desire_name, value = matches[0]
        #     if desire_name != each_desire:
        #         raise ValueError(f"Desire name mismatch: expected {each_desire}, got {desire_name}")
        #     # val = float(value)
        #     # val = max(0.0, min(10.0, val))
        #     val = float(value)
        #     if self._social_personality =="Competitive" or self._social_personality == "Prosocial":
        #         desire_value = max(0.0, min(10.0, self._expected_value[each_desire] - val))
        #     else:
        #         desire_value = max(0.0, min(10.0, self._expected_value[each_desire] + val))
        #     others_desire[each_desire] = desire_value



        # output_format用于限定输出格式

        if self._social_personality == "Competitive" or self._social_personality == "Altruistic":
            output_format = (
                f"Please output ONLY the absolute difference (gap) between {agent_name}'s current value "
                f"and the expected value for each desire.(i.e., current value - expected value)rounded to one decimal place.\n"
                f"The gap is between {zero} and {ten}, and it should be a non-negative number, ")
        # elif self._social_personality == "Prosocial":
        #     output_format += (f"The gap is between -4 and 4. "
        #     "Ensure that the total count of positive values exceeds the count of negative values.")
        # elif self._social_personality == "Individualistic":
        #     output_format += (f"The gap is between -4 and 4. "
        #      "Ensure that the total count of negative values exceeds the count of positive values.")
        else:
            output_format = (f"Please output the difference (gap) between {agent_name}'s current value "
                         "and the expected value for each desire.(i.e.,  expected - current), rounded to one decimal place.\n"
                         "For each desire dimension, first decide whether the current value is "
                         "higher (-) or lower (+) than the expected value. Then output the signed gap. ")
            if self._social_personality == "Prosocial":
                output_format += ("Ensure that  "
                                  f"most of the values are lightly lower than {self._current_agent_name}\'s own gap, but not too close. ")
            elif self._social_personality == "Individualistic":
                output_format += ("Ensure that "
                                  f"most of the values are lightly higher than {self._current_agent_name}\'s own gap, but not too close. ")
            output_format += (f"And you must not flip the sign of the gap value higher than 3 or lower than -3 "
        "(e.g., do NOT turn +6.5 into −6.5).")

        output_format += (
            "\nIMPORTANT: Output MUST be exactly and only 8 lines, no explanations, no markdown, no lists, no code block. "
            "Each line must be in the form:\n"
            "<desire_name>: <gap_value>\n"
            "For example:\n"
            "senseofsuperiority: 2.1\n"
            "senseofachievement: -0.5\n"
            "confidence: 1.0\n"
            "joyfulness: 0.0\n"
            "comfort: 3.4\n"
            "recognition: -1.2\n"
            "spiritualsatisfaction: 0.9\n"
            "senseofcontrol: 2.5\n"
            "Do NOT output any explanations, markdown, code block, or extra content. Do NOT output more or less than 8 lines."
        )

        total_prompt = personality_prompt + observed_prompt + rule_prompt + table_prompt + output_format + objective_prompt
        print("total_prompt: ", total_prompt)
        # 生成回答，并读取回答的desire值
        answer = prompt.open_question(
            question=total_prompt,
            max_tokens=500,
            terminators=(),
        )
        print("answer: ", answer)
        pattern = r"[-*]?\s*\*{0,2}([A-Za-z_]+)\*{0,2}\s*:\s*([+\-]?\d+(?:\.\d+)?)"
        matches = re.findall(pattern, answer)
        desire_set = set(normalized_desire_name)
        signal = 0
        for desire_name, value in matches:
            norm_name = self._normalize_key(desire_name)
            if norm_name in desire_set:
                val = round(float(value), 1)  # 保留一位小数
                if self._social_personality in ("Competitive","Individualistic", "Prosocial"):
                    desire_value = max(0.0, min(10.0, self._expected_value[norm_name] - val))
                elif self._social_personality in ("Altruistic"):
                    desire_value = max(0.0, min(10.0, self._expected_value[norm_name] + val))
                else: raise ValueError(f"Invalid social personality: {self._social_personality}")
            others_desire[norm_name] = desire_value
            signal = signal + 1
        if signal != len(normalized_desire_name):
            raise ValueError(f"Not all desires were estimated. Expected {len(normalized_desire_name)}, got {signal}.")
        return others_desire



    def _normalize_key(self, name: str) -> str:
        """标准化键名"""
        return str(name).replace("_", "").replace(" ", "").lower()

    def _calculate_svo(self, others_desires: dict):
        """ 计算当前agent的SVO角度 """
        desire_num = len(self._desire_name)
        print("--------")
        print("检查计算过程中的数据")
        print("step: ",self._step_counter)
        print("self_desire: ", self._desire_value)
        print("current agent: ", self._current_agent_name)
        print("estimated other desires: ", self._estimate_other_desire_tracker)
        # 将期望值和自身欲望进行标准化处理，处理成小写并去掉下划线
        normalized_expected_value = {self._normalize_key(k): v for k, v in self._expected_value.items()}
        normalized_self_desire = {self._normalize_key(k): v for k, v in self._desire_value.items()}
        normalized_other_desire = {}
        for agent, agent_desires in others_desires.items():
            normalized_other_desire[agent] = {self._normalize_key(k): v for k, v in agent_desires.items()}
        # print("normalized_expected_value", normalized_expected_value, "\n")
        # print("normalized_self_desire", normalized_self_desire, "\n")
        # print("normalized_other_desire", normalized_other_desire, "\n")
        print("others_desires: ", others_desires)
        expected_svo_value = get_svo_from_personality(self._social_personality)

        # 计算当前step的自身满意度
        self_satisfaction_raw = sum(
            max(min(normalized_self_desire[d] - normalized_expected_value[d], 4), -4)
            for d in normalized_self_desire if d in normalized_expected_value
        ) / desire_num

        self_satisfaction_raw_2 = (1 - self._alpha) * self_satisfaction_raw + (
                    (90 - expected_svo_value) / 90.0) * self._alpha * 10
        # self._self_satisfaction_value = self_satisfaction
        # 计算当前step他人满意度
        agent_num = len(others_desires)
        if agent_num == 0:
            raise ValueError("other_desires error.")
        else:
            total = 0
            for agent, agent_desires in normalized_other_desire.items():
                one_satisfaction = sum(
                    max(min(agent_desires[d] - normalized_expected_value[d], 4), -4)
                    for d in agent_desires if d in normalized_expected_value
                ) / desire_num

                total += one_satisfaction
            other_satisfaction_raw = total / agent_num
            other_satisfaction_raw_2 = (1 - self._alpha) * other_satisfaction_raw + (
                        90 - expected_svo_value) / 90.0 * self._alpha * 10
            # self._other_satisfaction_value = other_satisfaction

        self_satisfaction =4 +  self_satisfaction_raw_2
        other_satisfaction =4 +  other_satisfaction_raw_2

        self._self_satisfaction_value = self_satisfaction
        self._other_satisfaction_value = other_satisfaction

        print("self_satisfaction: ", self._self_satisfaction_value)
        print("other_satisfaction: ", self._other_satisfaction_value)

        # 计算SVO角度
        self._svo_value = (1 - self._beta) * expected_svo_value + degrees(
            atan(1 * (self._other_satisfaction_value + 0.01) / (self._self_satisfaction_value + 0.01))) * self._beta
        print("SVO value: ", self._svo_value)
        print("--------")

    def _update_value(self, action: str, observation: str, ):

        previous_svo = self._svo_value
        pre_personality = self._social_personality
        observed_agent_dict = self._get_agents_from_observation(observation)  # 返回观察到的agent字典，观察到了为True
        other_agent_desire = {}
        for agent in self._agent_names:
            if agent != self._current_agent_name:
                other_agent_desire[agent] = self._estimate_other_desire(agent, observation, action,
                                                                        observed_agent_dict[agent])
                # sleep(10)

        # 计算SVO
        self._estimate_other_desire_tracker[self._step_counter] = other_agent_desire
        self._calculate_svo(other_agent_desire)
        satisfaction_svo = self._svo_value
        questionnaire_svo = self._run_svo_questionnaire(
            step_idx=self._step_counter,
            action=action,
            observation=observation,
            self_satisfaction=self._self_satisfaction_value,
            other_satisfaction=self._other_satisfaction_value,
        )
        self._svo_questionnaire_value = questionnaire_svo
        # self._svo_value = questionnaire_svo

        # 更新expected_value
        # self._update_expected_value(observation, action, {
        #     "self_satisfaction": self._self_satisfaction_value,
        #     "other_satisfaction": self._other_satisfaction_value
        # })

        personality = get_personality_from_svo(self._svo_value)
        svo_log = {
            "previous_svo": previous_svo,
            "current_svo": self._svo_value,
            "svo_from_satisfaction": satisfaction_svo,
            "svo_from_questionnaire": questionnaire_svo,
            "previous_social_personality": pre_personality,
            "social_personality_now": personality,
            "action": action,
            # "observed_agents": agent_list,
            "self_satisfaction": self._self_satisfaction_value,
            "other_satisfaction": self._other_satisfaction_value,
        }
        self._logging_channel(svo_log)
        return svo_log

    def _tracker_desire_and_update_svo(self):
        # 记录desire和svo变化
        current_numerical_desire_tracker = dict() # track the current numerical value of the desire跟踪当前愿望的数值
        current_qualitative_desire_tracker = dict() # track the current qualitative value of the desire跟踪当前欲望的定性值
        current_delta_tracker = dict() # track the delta of the desire追踪欲望的增量
        # print("++++++++")
        # print("expected_value", self._expected_value)
        # 更新desire的数值(get_current_numerical_value)，更新desire的定性描述(get_current_qualitative_value)
        for desire_component_name, desire_component in self._desire_components.items():
            current_numerical_value = desire_component.get_current_numerical_value()
            current_qualitative_value = desire_component.get_current_qualitative_value()
            #计算desire偏差
            current_value_name = self._normalize_key(desire_component.get_desire_name())
            # print("current_value_name", current_value_name)
            expected_value = self._expected_value[current_value_name]
            # 下面的判断
            if current_value_name in ['hunger', 'thirst', 'sleepiness']:
                component_delta = max(0, current_numerical_value - expected_value)
            else:
                delta = expected_value - current_numerical_value
                component_delta = max(0, delta)

            current_numerical_desire_tracker[current_value_name] = current_numerical_value
            current_qualitative_desire_tracker[current_value_name] = current_qualitative_value
            current_delta_tracker[current_value_name] = delta
            print("step: ",self._step_counter,"\ncurrent_numerical_value: ", current_numerical_value)
            self._desire_value[current_value_name] = current_numerical_value
        # print("++++++++")

        self._desire_delta = current_delta_tracker
        self._individual_desire_tracker[self._step_counter] = current_numerical_desire_tracker
        self._individual_delta_tracker[self._step_counter] = current_delta_tracker
        self._whole_delta_tracker[self._step_counter] = sum(current_delta_tracker.values())
        self._individual_qualitative_desire_tracker[self._step_counter] = current_qualitative_desire_tracker
        observation = self.get_named_component_pre_act_value(
            self._observation_component_name
        )
        if len(self._action_cache) != 0:
            action_attempt = self._action_cache[-1]
        else:
            action_attempt = f"{self._current_agent_name} has not taken any action yet."
        self._update_value(action_attempt, observation)

        self._svo_tracker[self._step_counter] = self._svo_value
        self._svo_questionnaire_tracker[self._step_counter] = self._svo_questionnaire_value
        self._satisfaction_tracker[self._step_counter] = {
            "self satisfaction": self._self_satisfaction_value,
            "other satisfaction": self._other_satisfaction_value,
        }
        self._expected_value_traker[self._step_counter] = {
            "expected value": self._expected_value,
            "change": self._expected_value_changed,
        }
        print('--------')
        print("检查保存中的数据是否正常")
        print("desire_tracker: ", self._individual_desire_tracker)
        print("svo_tracker: ", self._svo_tracker)
        print("satisfaction_tracker: ", self._satisfaction_tracker)
        print("expected_value_tracker: ", self._expected_value_traker)
        print("--------")
        self._step_counter += 1

    def _make_pre_act_value(self) -> str:
        # 记录desire变化并输出日志
        index = self._step_counter
        self._tracker_desire_and_update_svo()
        # self._track_value()
        self._logging_channel({
            'index': index,
            'individual_desire_tracker': self._individual_desire_tracker[index],
            'individual_delta_tracker': self._individual_delta_tracker[index],
            'whole_delta_tracker': self._whole_delta_tracker[index],
            'individual_qualitative_desire_tracker': self._individual_qualitative_desire_tracker[index]
        })
        return "The value of the desire has been updated."

    def pre_act(
        self,
        unused_action_spec: entity_lib.ActionSpec,
    ) -> str:
        del unused_action_spec
        self.get_pre_act_value()
        return ''

    def post_act(self, action_attempt: str) -> str:
        self._action_cache.append({'timestamp': self._clock_now(), 'action':action_attempt})
        return ''

    def get_whole_delta_tracker(self) -> dict:
        return self._whole_delta_tracker

    def get_individual_delta_tracker(self) -> dict:
        return self._individual_delta_tracker

    def get_individual_desire_tracker(self) -> dict:
        return self._individual_desire_tracker

    def get_individual_qualitative_desire_tracker(self) -> dict:
        return self._individual_qualitative_desire_tracker

    def get_expected_value_dict(self) -> dict:
        return self._expected_value_dict

    def get_svo_tracker(self):
        return self._svo_tracker

    def get_svo_questionnaire_tracker(self):
        return self._svo_questionnaire_tracker

    def get_satisfaction_tracker(self):
        return self._satisfaction_tracker

    def get_expected_value_tracker(self):
        return self._expected_value_traker

    def get_estimate_other_desire_tracker(self):
        return self._estimate_other_desire_tracker

    def get_action_sequence(self) -> Sequence[dict]:
        #行动记录
        return self._action_cache

    def get_self_satisfaction(self):
        # self.get_pre_act_key()
        return self._self_satisfaction_value

    def get_other_satisfaction(self):
        # self.get_pre_act_key()
        return self._other_satisfaction_value

    def get_current_svo_value(self, read: bool=True) -> float:
        if self._step_counter == 0:
            return get_svo_from_personality(self._social_personality)
        else:
            return self._svo_value

    def get_current_social_personality(self) -> str:
        if self._step_counter == 0:
            return self._social_personality
        else:
            return get_personality_from_svo(self._svo_value)

    def get_current_expected_value_of_desire(self):
        return self._expected_value
