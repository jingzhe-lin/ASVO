import os.path

from concordia.typing import entity_component
from concordia.document import interactive_document
from concordia.language_model import language_model
from concordia.typing import clock as game_clock
from collections.abc import Sequence
import json



class PredictOtherAction(entity_component.ContextComponent):
    def __init__(
            self,
            model: language_model.LanguageModel,
            clock: game_clock.GameClock,
            storage_folder: str,
            component_order: Sequence[str] | None = None,
    ):
        """
       预测他人行为的组件
        """
        self.model = model
        self.clock = clock
        self.agent_info_path = os.path.join(storage_folder,  "agent_info.json")
        self.store_path = os.path.join(storage_folder, "prediction.json")

        if component_order is None:
            self.component_order = None
        else:
            self.component_order = tuple(component_order)
        if self.component_order is not None:
            if len(self.component_order) != len(set(self.component_order)):
                raise ValueError('component_order should not contain duplicates'+', '.join(self.component_order))


    def _predict_action(self,  target_agent:str, observation:str, full_info:str):
        """预测其他agent的行为"""
        agent_name = self.get_entity().name
        prompt  = interactive_document.InteractiveDocument(self.model)

        prompt.statement(f"{agent_name} has observed: {observation}.")
        prompt.statement(f"{target_agent}'s information: {full_info}.")

        question = (f"Based on the above information, what will {target_agent} do next?"
                    f"Give the most probable action and the reason for this action."
                    f"Please answer in the following format:")
        question += f"{agent_name} predicts {target_agent}'s action: <action>\n"

        answer = prompt.open_question(
            question=question,
            max_tokens=500,

        )

        return answer

    def _load_agent_data(self):
        """从json文件中加载agent信息"""
        if os.path.exists(self.agent_info_path):
            try:
                with open(self.agent_info_path, 'r') as f:
                    data = json.load(f)
                    if not data:
                        return None
                    return data
            except json.JSONDecodeError:
                raise ValueError("Error: agent_info.json is data format is wrong.")
        else:
            raise FileNotFoundError("Error: Warning: agent_info.json does not exist.")

    def _extract_agents_from_observation(self, observation:str):
        """从observation中提取agent，如果没有观察到的agent就不需要预测行为"""
        agent_name = self.get_entity().name
        agent_data =self._load_agent_data()# 读取json文件
        if agent_data is None:
            return  []
        possible_agent = list(agent_data.keys())
        detected_agents = [
            agent for agent in possible_agent if agent in observation and agent != agent_name
        ]
        return detected_agents

    def _get_agent_data(self, target_agent_name: str):
        name = self.get_entity().name
        agent_data = self._load_agent_data()
        if agent_data is None:
            return None
        if target_agent_name not in agent_data:
            raise KeyError(f"Error: Agent {target_agent_name} is not found in agent_info.json.")
        elif target_agent_name == name:
            raise KeyError(f"Error: Agent {target_agent_name} is not other agent.")
        agent_info = agent_data[target_agent_name]
        full_info = "\n".join([f"{key}: {value}" for key, value in agent_info.items()])
        return full_info

    def store_prediction(self, prediction:dict):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r') as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [].append(existing_data)
            except json.JSONDecodeError:
                existing_data = []
        else:
            existing_data = []
        existing_data.append(prediction)
        with open(self.store_path, 'w') as f:
            json.dump(existing_data, f, indent=4,ensure_ascii=False)


    def pre_act(self,action_spec):
        """在pre_act阶段预测其他agent的行为"""
        entity = self.get_entity()

        # 获取observation信息
        observation_comp = entity.get_component('Observation')
        observation = observation_comp.pre_act(action_spec)

        if self._load_agent_data() is None:
            return "skip"

        prediction = {}

        #提取被观察到的agent
        observed_agent = self._extract_agents_from_observation(observation)

        for name in observed_agent:
            full_info = self._get_agent_data(name)
            prediction_action = self._predict_action(
                target_agent=name,
                observation=observation,
                full_info=full_info)
            prediction[name] = prediction_action
        self.store_prediction(prediction)
        return 'Prediction completed'













