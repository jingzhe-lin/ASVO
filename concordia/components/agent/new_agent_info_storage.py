import  json
import os
import types
import datetime

from collections.abc import Mapping

from concordia.components.agent import action_spec_ignored
from concordia.components.agent import memory_component
#from concordia.typing import entity_component
from concordia.typing import logging

from rich.console import  Console


console = Console()

DEFAULT_INFO_STORAGE_PRE_ACT_KEY = "Agent info storage"

class AgentInfoStorage(action_spec_ignored.ActionSpecIgnored):
    """储存agent的关键信息"""

    def __init__(
            self,
            storage_folder: str,
            memory_component_name: str = (
                memory_component.DEFAULT_MEMORY_COMPONENT_NAME
            ),
            components: Mapping[str, str] = types.MappingProxyType({}),
            pre_act_key: str = DEFAULT_INFO_STORAGE_PRE_ACT_KEY,
            logging_channel: logging.LoggingChannel = logging.NoOpLoggingChannel,
            current_time: str = '',
    ):
        super().__init__(pre_act_key)
        self.storage_folder = storage_folder
        self.file_path = ""
        self._logging_channel = logging_channel
        self._memory_component_name = memory_component_name
        self._components = dict(components)
        self._current_time = current_time

    def load_existing_data(self):
        """读取现有的agent数据，如果不存在则返回空字典"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    try:
                        return json.load(f)
                    except json.JSONDecodeError:
                        return {}
            except:
                with open(self.file_path, "r",encoding='utf-8') as f:
                    try:
                        return json.load(f)
                    except json.JSONDecodeError:
                        return {}
        return {}

    def save_agent_info(self, save_data):
        """"储存所有agent数据到json"""
        try:
            with open(self.file_path, "w") as f:
                json.dump(save_data,f, indent=4,ensure_ascii=False)
        except:
            with open(self.file_path, "w",encoding='utf-8') as f:
                json.dump(save_data,f, indent=4,ensure_ascii=False)
        #self.already_written = True

    def collect_agent_info(self):
        """收集agent的关键信息"""
        agent = self.get_entity()
        #print(f"DEBUG: AgentInfoStorage components = {list(self._components.keys())}")

        agent_info = {"name": agent.name}
        for key,label in self._components.items():
            agent_info[label] = self.get_named_component_pre_act_value(key)
        '''
        agent_info = {
            "name": agent.name,
            "identity": agent.get_component("identity").pre_act(),
            #"profile": agent.get_component('profile_comp').pre_act(),
            #"background": agent.get_component('background_knowledge_comp').pre_act(),
                      }'''
        return agent_info

    def add_agent_info(self):
        """将agent信息保存至json文件中"""
        #if self.already_written:
        #    return
        self.file_path = os.path.join(self.storage_folder, f"{self._current_time}_D2A_agent_info.json")
        agent = self.get_entity()
        agent_data = self.load_existing_data()
        agent_data[agent.name] = self.collect_agent_info()
        self.save_agent_info(agent_data)

        #记录日志
        self._logging_channel(
            {
                "event":"agent_info_storage",
                "agent_name": agent.name,
                "file_path": self.file_path,
            }
        )

    def _make_pre_act_value(self) -> str:
        """在这个阶段储存数据并记录日志"""
        self.add_agent_info()
        self._logging_channel(
            {
                "event":"PreActStorage",
                "file_path": self.file_path,
            }
        )
        return "Agent info stored."
























