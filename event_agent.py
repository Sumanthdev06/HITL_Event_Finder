"""
langgraph
langchain
langchain-core
langchain-openai
streamlit
tavily-python
requests
python-dotenv
"""

### Import Necessary Libraries
import os
import requests
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv

### Load API Keys from .env file
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')
os.environ["TAVILY_API_KEY"] = os.getenv('TAVILY_API_KEY')
WEATHER_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')

### Define the Agent's Tools
@tool
def search_events(query: str):
    """Searches for local events, concerts, or sports games."""
    from tavily import TavilyClient
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    results = tavily.search(query=query, search_depth="basic")
    return results['results'][:3]

@tool
def get_weather(city: str):
    """Fetches the weather forecast for a given city."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        weather_report = {
            "city": city,
            "temperature_celsius": data["main"]["temp"],
            "description": data["weather"][0]["description"]
        }
        return weather_report
    else:
        print(f"Weather API Error - Status Code: {response.status_code}")
        print(f"Weather API Response: {response.json()}")
        return "Could not retrieve weather data."
tools = [search_events, get_weather]

### Define State Structure
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]

### Define Node Functions
def call_model(state):
    messages = state['messages']
    model = ChatOpenAI(model="gpt-4-turbo", temperature=0)
    model_with_tools = model.bind_tools(tools)
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

def human_approval(state):
    return {}

def should_continue(state):
    if state['messages'][-1].tool_calls:
        return "continue"
    else:
        return "human_approval"

### Create and Configure the Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)
workflow.add_node("human_approval", human_approval)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent", should_continue, {"continue": "action", "human_approval": "human_approval"}
)
workflow.add_edge('action', 'agent')


workflow.add_edge('human_approval', END)

app = workflow.compile()