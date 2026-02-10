import sentence_transformers

from concordia.language_model import my_utils as utils
import json
import os

# the root path of the project, this is used to import the ASVO module
ROOT = r""

# how many episodes in each simulation
episode_length = 1
NUM_PLAYERS = 2
# whether to use the language model, if set to True, No language model will be used
# use for debugging
# disable_language_model = True
disable_language_model = False

# the sentence transformer model used to encode the text
st_model = sentence_transformers.SentenceTransformer(
    'sentence-transformers/all-mpnet-base-v2')
embedder = lambda x: st_model.encode(x, show_progress_bar=False)

# the agents that will be tested, there are four agents: [ 'ASVO','ReAct', 'BabyAGI', 'LLMob','D2A']

tested_agents = [
                  'ASVO',
                  'ReAct',
                  'BabyAGI',
                  'LLMob',
                  'D2A',
                  ]

# whether to use the previous profile, if set to True, the previous profile will be used
# used to run with the same profile as the previous run
Use_Previous_profile = False
previous_profile_file = None
previous_profile = None

# if Use_Previous_profile is True, the previous profile file should be provided
if Use_Previous_profile:
  previous_profile_file = os.path.join(r'examples\ASVO\result_folder\outdoor_result\Your folder name', 'Your previous profile name.json')
  try:
    with open(previous_profile_file, 'r') as f:
      previous_profile = json.load(f)
  except:
    raise ValueError('The previous profile file is not found.')
else:
  previous_profile = None

# the language model used to generate the text
# you can also use other models, detailed see the definition of language_model_setup
api_type = 'your api type'
model_name = 'your model name'
api_key = 'your api key'

device = 'cpu'
model = utils.language_model_setup(
    api_type=api_type,
    model_name=model_name,
    api_key=api_key,
    disable_language_model=disable_language_model,
)

# the desires that will be used in the simulation
###
wanted_desires = [
    "sense of superiority",
    "sense_of_achievement",
    "confidence",
    "joyfulness",
    "comfort",
    "recognition",
    'spiritual satisfaction',
    'sense of control',
]
###
# the hidden desires that will be used in the simulation
hidden_desires = []
###

# the path to store the result
current_file_path = os.path.dirname(os.path.abspath(__file__))
result_folder_name = 'result_folder'
current_folder_path = os.path.join(current_file_path, result_folder_name)
if not os.path.exists(current_folder_path):
  os.makedirs(current_folder_path)


