import openai
import re
import httpx
import os
from dotnet import load_dotnet

_ = load_dotnet
from openai import OpenAI

client = OpenAI()

chat_completion = client.chat.completions.create(
    model = "gpt-3.5-turbo",
    messages = [{"role": "user", "content": "Hello world!"}]
)

chat_completion.choices[0].message.content

## create an agnet from scratch
class Agent:
    def __init__(self, system=""):
        self.system = system
        self.messages = []

        if self.system:
            self.messages.append({"role": "system", "content": system})
    
    def __call__(self, message):
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result
    
    def execute(self):
        completion = client.chat.completions.create(
            model = "gpt-4o",
            temperature = 0,
            messages = self.messages
        )

        return completion.choices[0].message.content

## Define the prompt for the agent
prompt = """
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

calculate:
e.g. calculate: 4 * 7 / 3
Runs a calculation and returns the number - uses Python so be sure to use floating point syntax if necessary

average_dog_weight:
e.g. average_dog_weight: Collie
returns average weight of a dog when given the breed

Example session:

Question: How much does a Bulldog weigh?
Thought: I should look the dogs weight using average_dog_weight
Action: average_dog_weight: Bulldog
PAUSE

You will be called again with this:

Observation: A Bulldog weights 51 lbs

You then output:

Answer: A bulldog weights 51 lbs
""".strip()

def calculate(what):
    return eval(what)

def average_dog_weight(breed_name: str):
    if breed_name in "Scotthish Terrier":
        return ("Scotthish Terrier average 20 lbs")
    elif breed_name in "Border Collie":
        return ("a Border Collie average 30 lbs")
    elif breed_name in "Toy Poodle":
        return ("a Toy Poodle average 10 lbs")
    else:
        return("An average dog weight is 30 lbs")
    
known_actions = {
    "calculate": calculate,
    "average_dog_weight": average_dog_weight
}

## call the agent with the system prompt
## calls the Agent class constructor with the prompt
bot = Agent(prompt)

## call the __call__ method of the Agent class with the message
result = bot("How much does a Border Collie weigh?")