import asyncio
import json
import logging
import re
from typing import List, TypedDict, Dict, Any

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
# ✨ --- Use the more modern agent constructor --- ✨
from langchain.agents import AgentExecutor, create_tool_calling_agent

from backend.core.config import settings
from backend.services.interface.openai_client import call_openai
from backend.services.interface.huggingface_client import call_huggingface
from backend.services.interface.local_client import call_local

logger = logging.getLogger(__name__)

class GraphState(TypedDict):
    user_query: str
    subscription_tier: str
    requested_model: str
    micro_prompts: List[str]
    model_assignments: Dict[str, str]
    llm_responses: Dict[str, str]
    aggregated_response: str
    models_used: List[Dict[str, str]]

class LangGraphAgent:
    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=settings.GOOGLE_API_KEY, temperature=0.0, convert_system_message_to_human=True)
        # The tool itself is correct, but we don't need the specific name anymore.
        self.search_tool = TavilySearchResults(max_results=3)
        self.graph = self._build_graph()

    def _get_prompt_breaker_chain(self):
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert at breaking down complex user queries into a series of simple, self-contained, and actionable micro-prompts. Respond with a JSON object containing a single key 'prompts' which is a list of strings."),
            ("human", "Deconstruct the following query:\n\n---\n{query}\n---")
        ])
        return prompt_template | self.llm | JsonOutputParser()

    # ✨ --- THIS FUNCTION CONTAINS THE MAIN FIX --- ✨
    def _get_researcher_agent_executor(self):
        # This prompt is strengthened to be more directive and ensure correct output.
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert LLM router with access to a search engine. Your job is to select the best model for a given task.\n"
             "Follow these steps:\n"
             "1. For each micro-prompt, analyze the user's goal.\n"
             "2. Consult the provided model descriptions to see if there is an obvious best choice.\n"
             "3. If the best choice is not clear, use your search tool to find the most effective model for the specific task.\n"
             "4. **CRITICAL**: Your final decision for each prompt MUST be one of the models from the 'Available Models' list provided.\n\n"
             "**Available Models:**\n{available_models}\n\n"
             "**Model Descriptions:**\n{model_info}\n\n"
             "After your research, you MUST provide your final answer as a single, valid JSON object. The keys should be the micro-prompts, and the values should be the chosen model names."),
            ("human", "{input}"),
            # This placeholder is now correctly handled by create_tool_calling_agent
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Use the modern constructor which correctly handles the agent_scratchpad
        agent = create_tool_calling_agent(self.llm, [self.search_tool], prompt)
        
        return AgentExecutor(agent=agent, tools=[self.search_tool], verbose=True, handle_parsing_errors=True)

    def _get_generic_linkage_chain(self):
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert at synthesizing information. You will be given an original user query and a series of responses from different AI models. Your goal is to weave these individual responses into a single, cohesive, and natural-sounding final answer."),
            ("human", "Original Query: {query}\n\nComponent Responses:\n---\n{responses}\n---\n\nSynthesized Answer:")
        ])
        return prompt_template | self.llm | StrOutputParser()

    def _get_code_linkage_chain(self):
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert web developer. You will be given separate blocks of HTML, CSS, and JavaScript code. Your task is to assemble these blocks into a single, complete, and runnable `index.html` file. Place CSS in `<style>` tags in the `<head>` and JavaScript in `<script>` tags at the end of the `<body>`. Present the final output inside a single markdown code block."),
            ("human", "Original Request: Create a {app_type}\n\nComponent Code Blocks:\n---\n{responses}\n---\n\nAssembled `index.html` file:")
        ])
        return prompt_template | self.llm | StrOutputParser()

    async def _prompt_breaking_agent(self, state: GraphState) -> GraphState:
        logger.info("--- Running Prompt Breaking Agent ---")
        breaker_chain = self._get_prompt_breaker_chain()
        response = await breaker_chain.ainvoke({"query": state["user_query"]})
        micro_prompts = response.get("prompts", [state["user_query"]])
        return {**state, "micro_prompts": micro_prompts}

    # ✨ --- THIS NODE IS ALSO UPDATED --- ✨
    async def _research_agent(self, state: GraphState) -> GraphState:
        logger.info("--- Running Research Agent ---")
        
        available_models = [name for name, config in self.model_config.items() if state["subscription_tier"] in config.get("allowed_subs", [])]
        
        model_info_str = json.dumps({
            name: {"provider": config["provider"], "capabilities": config["capabilities"]} 
            for name, config in self.model_config.items() if name in available_models
        }, indent=2)

        # We only need to create the agent executor once
        agent_executor = self._get_researcher_agent_executor()
        
        prompts_as_string = "\n".join(f"- {p}" for p in state["micro_prompts"])
        
        response = await agent_executor.ainvoke({
            "input": prompts_as_string,
            "available_models": ", ".join(available_models),
            "model_info": model_info_str
        })
        
        # The output from this agent is cleaner
        output_text = response['output']
        assignments = {}
        try:
            # The output should now be a clean JSON string, but we keep the regex for safety
            json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
            if json_match:
                assignments = json.loads(json_match.group(0))
            else: # Fallback if JSON is not found
                assignments = {prompt: available_models[0] for prompt in state["micro_prompts"]}
        except json.JSONDecodeError: # Fallback if JSON is malformed
            assignments = {prompt: available_models[0] for prompt in state["micro_prompts"]}
        return {**state, "model_assignments": assignments}

    async def _llm_caller_node(self, state: GraphState) -> GraphState:
        logger.info("--- Running LLM Caller Node ---")
        model_assignments = state["model_assignments"]
        tasks = []
        for prompt, model_name in model_assignments.items():
            if prompt not in state["micro_prompts"]: continue
            provider = self.model_config.get(model_name, {}).get("provider")
            if provider == "openai": tasks.append(call_openai(prompt))
            elif provider == "huggingface": tasks.append(call_huggingface(prompt))
            elif provider == "local": tasks.append(call_local(prompt))
            else: tasks.append(asyncio.sleep(0, result=f"Error: Unknown provider for {model_name}"))
        responses = await asyncio.gather(*tasks)
        llm_responses = {prompt: response for prompt, response in zip(model_assignments.keys(), responses) if prompt in state["micro_prompts"]}
        models_used = [{"model": name, "provider": self.model_config.get(name, {}).get("provider")} for name in model_assignments.values()]
        return {**state, "llm_responses": llm_responses, "models_used": models_used}
    
    async def _linkage_agent(self, state: GraphState) -> GraphState:
        logger.info("--- Running Linkage Agent ---")
        user_query = state["user_query"].lower()
        is_code_task = all(kw in user_query for kw in ["html", "css", "js"])

        if is_code_task:
            logger.info("Code generation task detected. Using specialized code linkage chain.")
            linkage_chain = self._get_code_linkage_chain()
            app_type = "web application"
            input_data = {"app_type": app_type, "responses": json.dumps(state["llm_responses"], indent=2)}
        else:
            logger.info("Using generic linkage chain.")
            linkage_chain = self._get_generic_linkage_chain()
            input_data = {"query": state["user_query"], "responses": json.dumps(state["llm_responses"], indent=2)}
            
        aggregated_response = await linkage_chain.ainvoke(input_data)
        return {**state, "aggregated_response": aggregated_response}

    def _build_graph(self):
        workflow = StateGraph(GraphState)
        workflow.add_node("prompt_breaker", self._prompt_breaking_agent)
        workflow.add_node("researcher", self._research_agent)
        workflow.add_node("llm_caller", self._llm_caller_node)
        workflow.add_node("linker", self._linkage_agent)
        workflow.set_entry_point("prompt_breaker")
        workflow.add_edge("prompt_breaker", "researcher")
        workflow.add_edge("researcher", "llm_caller")
        workflow.add_edge("llm_caller", "linker")
        workflow.add_edge("linker", END)
        return workflow.compile()

    async def run(self, user_query: str, subscription_tier: str, requested_model: str) -> Dict:
        initial_state = GraphState(user_query=user_query, subscription_tier=subscription_tier, requested_model=requested_model, micro_prompts=[], model_assignments={}, llm_responses={}, aggregated_response="", models_used=[])
        final_state = await self.graph.ainvoke(initial_state)
        return final_state