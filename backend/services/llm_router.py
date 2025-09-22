import logging
from backend.services.langgraph_agent import LangGraphAgent
from backend.core.config import settings

logger = logging.getLogger(__name__)

class LLMRouter:
    def __init__(self):
        self.agent = LangGraphAgent(settings.MODEL_CONFIG)
        logger.info("LLMRouter initialized with LangGraphAgent.")

    async def route_and_process_prompts(self, user_query: str, subscription_tier: str, requested_model: str):
        logger.info(f"Routing query via LangGraphAgent for user with sub '{subscription_tier}'.")
        
        result = await self.agent.run(
            user_query=user_query,
            subscription_tier=subscription_tier,
            requested_model=requested_model
        )

        aggregated_response = result.get("aggregated_response", "No response generated.")
        models_used = result.get("models_used", [])

        logger.info(f"LangGraphAgent finished processing. Response: '{aggregated_response[:100]}...'")
        return aggregated_response, models_used