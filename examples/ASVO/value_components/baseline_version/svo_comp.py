#import random
import datetime
import re
from collections.abc import Mapping, Callable
from math import atan, degrees

from concordia.clocks import game_clock
from concordia.components.agent import constant
from concordia.components.agent import memory_component
from concordia.typing import entity_component
from concordia.components import agent as agent_components
from concordia.typing import entity as entity_lib
from concordia.typing import logging
from concordia.language_model import language_model
from concordia.document import interactive_document
from examples.D2A.value_components.old_version.value_comp import DEFAULT_VALUE_SCALE, desire

DEFAULT_SATISFACTION = 5

SVO_RANGES = {
    "Altruistic": (64.89, 84.81),
    "Individualistic": (44.99, 64.89),
    "4": (25.09, 44.99),
    "Competitive": (5.19, 25.09)
}

expected_SVO = {
    "Altruistic": 74.85,
    "Individualistic": 54.94,
    "Prosocial": 35.04,
    "Competitive": 15.14
}


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

class SVO_Component(agent_components.action_spec_ignored.ActionSpecIgnored):
    def __init__(
    self,
    *,
    pre_act_key: str,
    observation_component_name: str,
    agent_names: list,
    #add_to_memory: bool = False,
    model: language_model.LanguageModel,
    memory_component_name: str = (
        memory_component.DEFAULT_MEMORY_COMPONENT_NAME),
    desire_components: Mapping[str, desire],
    expected_values: Mapping[str, int],
    agent_name: str = "",
    clock: game_clock.MultiIntervalClock,
    logging_channel: logging.LoggingChannel = logging.NoOpLoggingChannel,
    )-> None:
        super().__init__(pre_act_key)

        self._memory_component_name = memory_component_name
        self._agent_name = agent_name
        self._model = model
        self._desire_components = dict(desire_components)
        self._player_names = agent_names
        self._desire_name = tuple(self._desire_components.keys())
        self._expected_value = expected_values
        self._expected_value_changed = False
        self._logging_channel = logging_channel
        self._value_scale = [str(i) for i in sorted(DEFAULT_VALUE_SCALE)]
        self._observation_component_name = observation_component_name
        self._step_counter = 0
        self._clock = clock
        self._clock_now = clock.now
        #self._svo_tracker = dict()#记录SVO的变化
        self._action_cache = []

        #self._action = f'{self._agent_name} does not take any action. '
        self._social_personality = "Competitive"
        self._svo_value = get_svo_from_personality(self._social_personality)
        self._self_satisfaction_value = 0
        self._other_satisfaction_value = 0
        self._alpha = 0.4#计算时原始svo值的权重
        self._gamma = 0.7
        self._beta = 0.5 #SVO的波动限制
        self._estimate_other_desire_history = {} # 记录他人欲望的变化
        self._self_satisfaction_history = []
        self._other_satisfaction_history = []  # 记录自己和他人满意度的变化
        self._last_update_step = None # 记录上次更新的时间，防止重复更新导致API浪费

        # 满意度衰减机制相关
        self._time_step = self._clock.get_step_size()
        self._decrease_interval = 1
        self._decrease_step = 1.0
        self._decrease_interval_minus = datetime.timedelta(hours=1)
        self._decrease_probability = self._decrease_step / (self._decrease_interval_minus / self._time_step)

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

    def _get_agents_from_observation(self, observation: str) -> dict:
        """ 函数的作用是判断是否看到了其他人"""
        possible_agents = self._player_names
        other_agent = {}
        for agent in possible_agents:
            if agent in observation:
                other_agent[agent] = True
            else: other_agent[agent] = False
        return other_agent

    def _update_expected_value(self, observation: str, action: str, satisfaction: dict):
        """对expected_desire进行动态调整"""
        prompt = interactive_document.InteractiveDocument(self._model)

        prompt_text = (f"The current expected value of {self._agent_name}'s desire is: {self._expected_value}\n"
                       f"The agent {self._agent_name}'s action is: {action}."
                       f"And the consequence is: {observation}."
                       f"You should check wether the action can lead to a change in the expected value of {self._agent_name}'s desire. "
                       f"Please answer in the format of the letter with brackets : (a) Yes. (b) No."
                       )
        answer = prompt.open_question(prompt_text)
        if 'yes' in answer or '(a)' in answer.lower():
            change_signal = True
        else:
            change_signal = False
        #change_signal = True
        if change_signal:
            update_prompt = (
                f"The agent {self._agent_name} has a desire profile (float between 0 to 10), which reflects how strongly the agent values each aspect.\n"
                f"The agent {self._agent_name}'s action is: {action}."
                f"The consequence is: {observation}."
                f"And the satisfaction score are: self={satisfaction['self_satisfaction']}, other={satisfaction['other_satisfaction']}\n"
                f"Based on this, update the expected values for the following desires:\n"
                f"{self._desire_name}"
                f"Please format your answer as a list:\n"
                f"desire_name: new_value\n"
                )
            update_answer = prompt.open_question(update_prompt, max_tokens=500, terminators=())
            pattern = r"[-*]?\s*([A-Za-z_]+):\s*([0-9]+(?:\.[0-9]+)?)"
            matches = re.findall(pattern, update_answer)
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$\n",prompt.view().text(),"$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
            valid_desires = set(self._desire_name)
            print("valid desires",valid_desires)
            updated_value = {}

            for desire, value in matches:
                if desire in valid_desires:
                    val = float(value)
                    val = max(0.0, min(10.0, val))
                    updated_value[desire] = val
            self._expected_value = updated_value
            self._expected_value_changed = change_signal

    def _estimate_other_desire(self, agent_name: str, observation: str, action_attempt: str, observed_or_not: bool) -> dict:
        """ 估计他人的欲望，返回一个字典，key是欲望名称，value是欲望值"""
        zero, *_, ten = self._value_scale
        prompt = interactive_document.InteractiveDocument(self._model)
        others_desire = {}
        observations_context = f'{self._agent_name} observes the following: \n{observation} \n'
        action_context = f'{self._agent_name} takes the action: \n{action_attempt} \n'

        # output_format用于限定输出格式
        output_format = (f"The desire value of {agent_name} is between {zero} and {ten}, "
            f"Please output ONLY the values of desires in the following format:\n\n")
        for  desire in self._desire_name:
            output_format += f"{desire}: <{desire} value>\n"

        # 人格提示
        personality_text = self._personality_prompt_initial(self._social_personality)# 对人格的描述
        personality_prompt = (f"{self._agent_name} is a human-like agent. "
                              f"{self._agent_name} has a social personality of {self._social_personality}. "
                              f"The {self._social_personality.lower()} people are {personality_text.lower()} ")
        objective_prompt  = 'All your guesses are mainly objective guesses based on actions rather than subjective conjectures based on personality.'
        # 根据是否观察到其他人来选择不同的提示
        if observed_or_not:
            # 如果观察到了其他人，就直接预测desire
            imagine_prompt = (
                              f'{self._agent_name} will receive a series of observations and an action taken in the current time. '
                              f"{self._agent_name} needs to analyze how {agent_name}'s desires change after the action taken, "
                              f"and estimate the desire value of {agent_name} for each desire. ")
            total_prompt = personality_prompt + imagine_prompt + observations_context + action_context + output_format + objective_prompt
        elif not observed_or_not:
            # 如果没有观察到其他人，就需要先猜测对方的行为
            guess_action_prompt = (
                                   f"{self._agent_name} will receive a series of observations and an action taken in the current time. "
                                   f"{self._agent_name} needs to combine your memory to guess what {agent_name} might do, "
                                   f"and please output the guessed action of {agent_name} in the following format:\n"
                                   f"Guessed {agent_name}'s action: <action>\n"
                                   )
            guess_action_answer = prompt.open_question(
                question=guess_action_prompt+observations_context+action_context,
                max_tokens=500,
                terminators=()
            )
            guess_action_pattern = rf"Guessed {agent_name}'s action:\s*(.*)"
            guess_action_matches = re.search(guess_action_pattern, guess_action_answer)
            match_text = guess_action_matches.group(1).strip()
            guess_action_context = f"{self._agent_name} guess {agent_name}'s action: {match_text}\n"
            imagine_prompt  = (f"Combine the {self._agent_name}'s conjecture about {agent_name}'s action, "
                                f"{self._agent_name} needs to analyze how {agent_name}'s desires change after the action taken, "
                                f"and estimate the desire value of {agent_name} for each desire. ")
            total_prompt = personality_prompt + imagine_prompt + guess_action_context + output_format + objective_prompt

        # 生成回答，并读取回答的desire值
        answer = prompt.open_question(
            question=total_prompt,
            max_tokens=500,
            terminators=(),
        )
        pattern = r"([A-Za-z_]+):\s*([0-9]+(?:\.[0-9]+)?)"
        matches = re.findall(pattern, answer)
        desire_set = set(self._desire_name) #用集合可以加速匹配
        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$\n",prompt.view().text(),"$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        for desire, value in matches:
            if desire in desire_set:
                val = float(value)
                val = max(0.0, min(10.0, val))
                others_desire[desire] = val
        print("estimate 里的other desire",others_desire)
        print("@@@@@@@@@@@@@@@@@@@\n",others_desire,"@@@@@@@@@@@@@@@@@@@@@@")
        return others_desire

    # def _fluctuate_satisfaction(self):
    #     """满意度衰减机制"""
    #     random_number = random.uniform(0, 1)
    #     fluctuate_dict = dict()
    #     fluctuate_dict['satisfaction_before_fluctuate'] ={
    #         'self_satisfaction': self._self_satisfaction_value,
    #         'other_satisfaction': self._other_satisfaction_value
    #     }
    #     if random_number < self._decrease_probability:
    #         self._self_satisfaction_value = max(0, self._self_satisfaction_value - 1)
    #
    #     fluctuate_dict['random_number'] = random_number
    #     fluctuate_dict['decrease_probability'] = self._decrease_probability
    #     fluctuate_dict['Is_decrease?'] = random_number < self._decrease_probability
    #     fluctuate_dict['satisfaction_after_fluctuate'] =

    def _compute_delayed_satisfaction(self, history: list, gamma: float) -> float:
        """"计算满意度的衰减加权平均"""
        T = len(history)
        if T== 0:
            return 0.0
        weighted_sum = 0.0
        weight_total = 0.0
        for i, val in enumerate(history):
            decay = gamma**(T-i-1)
            weighted_sum += val * decay
            weight_total += decay
        return weighted_sum / weight_total

    def _calculate_svo(self, others_desires: dict) :
        """ 计算当前agent的SVO角度 （带上了满意度衰减）"""
        self_desire = {
            name: component.get_current_numerical_value()
            for name, component in self._desire_components.items()
        }
        desire_num = len(self._desire_name)

        # 将期望值和自身欲望进行归一化处理，处理成小写并去掉下划线
        normalized_expected_value = {k.replace("_","").lower(): v for k, v in self._expected_value.items()}
        normalized_self_desire = {str(k).replace("_","").lower(): v for k, v in self_desire.items()}
        normalized_other_desire = {}
        for agent, agent_desires in others_desires.items():
            normalized_other_desire[agent] = {k.replace("_","").lower(): v for k, v in agent_desires.items()}
        print("normalized_expected_value",normalized_expected_value,"\n")
        print("normalized_self_desire",normalized_self_desire,"\n")
        print("normalized_other_desire",normalized_other_desire,"\n")

        expected_svo_value = get_svo_from_personality(self._social_personality)

        #计算当前step的自身满意度
        self_satisfaction_raw = 0.5 * sum(10 - (normalized_expected_value[d] - normalized_self_desire[d])
                                for d in normalized_self_desire if d in normalized_expected_value) / desire_num
        self_satisfaction_raw_2 = (1-self._alpha) * self_satisfaction_raw +((90 - expected_svo_value) / 90.0) * self._alpha * 10
        #self._self_satisfaction_value = self_satisfaction
        #计算当前step他人满意度
        agent_num = len(others_desires)
        if agent_num == 0:
            raise ValueError("other_desires error.")
        else:
            total = 0
            for agent, agent_desires in normalized_other_desire.items():
                one_satisfaction = 0.5 * sum(10 - (normalized_expected_value[d] - agent_desires[d])
                                       for d in agent_desires if d in normalized_expected_value) / desire_num
                total += one_satisfaction
            other_satisfaction_raw = total / agent_num
            other_satisfaction_raw_2 = (1-self._alpha) * other_satisfaction_raw + (90-expected_svo_value)/90.0 * self._alpha * 10
            # self._other_satisfaction_value = other_satisfaction

        self_satisfaction = self_satisfaction_raw_2
        other_satisfaction = other_satisfaction_raw_2

        self._self_satisfaction_value = self_satisfaction
        self._other_satisfaction_value = other_satisfaction

        #使用指数衰减计算当前有效满意度
        # decay_gamma = self._gamma
        # decayed_self = self._compute_delayed_satisfaction(self._self_satisfaction_history, decay_gamma)
        # decayed_other = self._compute_delayed_satisfaction(self._other_satisfaction_history, decay_gamma)

        # 将计算的满意度值存储到历史记录中
        self._self_satisfaction_history.append(self_satisfaction)
        self._other_satisfaction_history.append(other_satisfaction)


        #计算SVO角度
        self._svo_value = (1-self._beta) * expected_svo_value + degrees(atan((self._other_satisfaction_value +1) / (self._self_satisfaction_value + 1))) * self._beta

    def _update_value(self, action: str, observation: str,):
        current_step = self._step_counter

        if self._last_update_step is not None and current_step == self._last_update_step:
            return

        previous_svo = self._svo_value
        pre_personality = self._social_personality
        observed_agent_dict = self._get_agents_from_observation(observation) #返回观察到的agent字典，观察到了为True
        other_agent_desire = {}
        for agent in self._player_names:
            if agent != self._agent_name:
                other_agent_desire[agent] = self._estimate_other_desire(agent, observation, action, observed_agent_dict[agent])
        # 计算SVO
        self._estimate_other_desire_history[self._step_counter] = other_agent_desire
        self._calculate_svo(other_agent_desire)

        # 更新expected_value
        self._update_expected_value(observation, action, {
            "self_satisfaction": self._self_satisfaction_value,
            "other_satisfaction": self._other_satisfaction_value
        })

        personality = get_personality_from_svo(self._svo_value)
        svo_log = {
            "previous_svo": previous_svo,
            "current_svo": self._svo_value,
            "previous_social_personality": pre_personality,
            "social_personality_now": personality,
            "action": action,
            # "observed_agents": agent_list,
            "self_satisfaction": self._self_satisfaction_value,
            "other_satisfaction": self._other_satisfaction_value,
        }
        self._logging_channel(svo_log)
        #self._step_counter += 1
        self._last_update_step = current_step
        print("step_counter",self._step_counter)

        return svo_log

    def get_self_satisfaction(self):
        self.get_pre_act_key()
        return self._self_satisfaction_value

    def get_other_satisfaction(self):
        self.get_pre_act_key()
        return self._other_satisfaction_value

    def get_estimate_other_desire_history(self):
        return self._estimate_other_desire_history

    def get_current_svo_value(self, read: bool=True) -> float:
        if self.get_entity().get_phase() == entity_component.Phase.READY:
            return self._svo_value
        if not read:
            self.get_pre_act_value()
        return self._svo_value

    def get_current_social_personality(self) -> str:
        if self.get_entity().get_phase() == entity_component.Phase.READY:
            return get_personality_from_svo(self._svo_value)
        self.get_pre_act_value()
        return get_personality_from_svo(self._svo_value)

    def get_current_expected_value_of_desire(self):
        return self._expected_value, self._expected_value_changed

    def post_act(self, action_attempt: str,) -> str:
        self._action_cache.append(action_attempt)
        return ""

    def _make_pre_act_value(self) -> str:
        if self._last_update_step == self._step_counter:
            return ""  # 本 step 已经更新过，不再重复
        #update_log = dict()
        observation = self.get_named_component_pre_act_value(
            self._observation_component_name
        )
        if len(self._action_cache) != 0:
            action_attempt = self._action_cache[-1]
        else:
            action_attempt = f"{self._agent_name} does not take any action."
        self._update_value(action_attempt, observation,)
        return ""

class SVO_Component_Without_PreAct(agent_components.action_spec_ignored.ActionSpecIgnored):
    def __init__(self, *args, **kwargs):
        self._component = SVO_Component(*args, **kwargs)

    def set_entity(self, entity: entity_component.EntityWithComponents) -> None:
        self._component.set_entity(entity)

    def _make_pre_act_value(self) -> str:
        return self._component.get_pre_act_value()

    def get_pre_act_value(self) -> str:
        return self._make_pre_act_value()

    def pre_act(self, action_spec: entity_lib.ActionSpec) -> str:
        del action_spec
        self.get_pre_act_value()
        return ""

    def update(self) -> None:
        self._component.update()

    def get_state(self) -> entity_component.ComponentState:
        return self._component.get_state()

    def set_state(self, state: entity_component.ComponentState) -> None:
        self._component.set_state(state)

    def get_current_social_personality(self) -> str:
        return self._component.get_current_social_personality()

    def get_current_svo_value(self)->float:
        return self._component.get_current_svo_value()

    def get_self_satisfaction(self)->float:
        return self._component.get_self_satisfaction()

    def get_other_satisfaction(self)->float:
        return self._component.get_other_satisfaction()

    def post_act(self, action_attempt: str) -> str:
        return self._component.post_act(action_attempt)

class SVO_Value_Tracker(agent_components.action_spec_ignored.ActionSpecIgnored):
    def __init__(
            self,
            *,
            pre_act_key: str,
            svo_component: SVO_Component,
            clock_now: Callable[[], datetime.datetime] | None = None,
            logging_channel: logging.LoggingChannel = logging.NoOpLoggingChannel,
    ) -> None:
        super().__init__(pre_act_key)
        self._svo_component = svo_component
        self._step_counter = 0
        self._svo_tracker = dict()
        self.satisfaction_tracker = dict()
        self._expected_value_traker = dict()
        self._action_cache = []
        self.clock_now = clock_now
        self._logging_channel = logging_channel
        self._timestamp_tracker = dict()
        self._initialized = False # 添加标志，避免重复初始化

    def set_entity(self, entity: entity_component.EntityWithComponents) -> None:
        super().set_entity(entity)
        if self._svo_component is not None:
            self._svo_component.set_entity(entity)
        self._initialized = False

    def _tracker_initial(self):
        entity = self.get_entity()
        action = getattr(entity, "last_action", f"{entity.name} does not take any action.")
        obs = f"{entity.name} is in a classroom. No specific observation."

        self._svo_component._update_value(action, obs)

        self_satisfaction = self._svo_component.get_self_satisfaction()
        other_satisfaction = self._svo_component.get_other_satisfaction()
        current_svo = self._svo_component.get_current_svo_value()
        expected_value, change = self._svo_component.get_current_expected_value_of_desire()

        self._svo_tracker[self._step_counter] = current_svo
        self.satisfaction_tracker[self._step_counter] = {
            "self_satisfaction": self_satisfaction,
            "other_satisfaction": other_satisfaction
        }
        self._expected_value_traker[self._step_counter] = {
            "expected_value": expected_value,
            "changed": change,
        }
        self._timestamp_tracker[self._step_counter] = self.clock_now()
        self._step_counter += 1

    def _track_svo(self):
        self_satisfaction = self._svo_component.get_self_satisfaction()
        other_satisfaction = self._svo_component.get_other_satisfaction()
        current_svo = self._svo_component.get_current_svo_value()
        expected_value, change = self._svo_component.get_current_expected_value_of_desire()
        #current_timestamp = self.clock_now()
        #print(self.clock_now())

        self._svo_tracker[self._step_counter] = current_svo
        self.satisfaction_tracker[self._step_counter] = {
            "self_satisfaction": self_satisfaction,
            "other_satisfaction": other_satisfaction
        }
        self._expected_value_traker[self._step_counter] = {
            "expected_value": expected_value,
            "change": change,
        }
        self._timestamp_tracker[self._step_counter] = self._svo_tracker
        self._step_counter += 1
        self._svo_component._step_counter += 1
        #print("BBBBB",self._step_counter)

    def _make_pre_act_value(self) -> str:
        if not self._initialized:
            self._tracker_initial()
            self._initialized=True
        else:
            self._track_svo()
        self._logging_channel({
            'step': self._step_counter - 1,
            'timestamp': self._timestamp_tracker[self._step_counter - 1],
            'svo': self._svo_tracker[self._step_counter - 1],
            'satisfaction': self.satisfaction_tracker[self._step_counter - 1],
            'expected_value': self._expected_value_traker[self._step_counter - 1]
        })
        return ""

    def pre_act(
      self,
      action_spec: entity_lib.ActionSpec,
  ) -> str:
        del action_spec
        #self._svo_component.set_entity(self.get_entity())
        self.get_pre_act_value()
        return ""

    def post_act(self, action_attempt: str) -> str:
        self._action_cache.append({'timestamp': self.clock_now(), 'action': action_attempt})
        return ""

    def get_action_cache(self):
        return self._action_cache

    def get_svo_tracker(self):
        return self._svo_tracker

    def get_satisfaction_tracker(self):
        return self.satisfaction_tracker

    def get_social_personality_tracker(self):
        return self._svo_component.get_current_social_personality()

    def get_expected_value_tracker(self):
        return self._expected_value_traker

    def get_estimate_other_desire_tracker(self):
        return self._svo_component.get_estimate_other_desire_history()

    def get_current_svo_value(self) -> float:
        return self._svo_component.get_current_svo_value()










