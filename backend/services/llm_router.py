from typing import List, Tuple, Dict
import asyncio
import logging
from .splitter import split_prompt
from ..core.config import settings
from .interface.openai_client import call_openai
from .interface.huggingface_client import call_huggingface
from .interface.local_client import call_local

logger = logging.getLogger(__name__)

class LLMRouter:
    """
    Handles the logic for splitting prompts, routing them to the appropriate
    LLMs based on subscription, and aggregating the results.
    """

    def _get_available_models_for_sub(self, user_sub: str) -> List[str]:
        """
        Filters the global model config to get a list of model names
        available for the given subscription tier.
        """
        available_models = []
        for model_name, config in settings.MODEL_CONFIG.items():
            if user_sub in config.get("allowed_subs", []):
                available_models.append(model_name)
        logger.info(f"User sub '{user_sub}' has access to models: {available_models}")
        return available_models

    async def route_and_process_prompts(self, user_query: str, subscription_tier: str, requested_model: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Splits the user query, routes micro-prompts to models, and aggregates responses.
        """
        # Step 1: Split the main query into micro-prompts
        prompts = split_prompt(user_query)
        if not prompts:
            return "Could not process the query.", []

        models_used = []
        tasks = []
        
        if requested_model == "auto":
            allowed_models = self._get_available_models_for_sub(subscription_tier)
            if not allowed_models:
                raise Exception("No models available for this subscription tier.")
            
            # Simple routing: cycle through the user's allowed models
            for i, prompt in enumerate(prompts):
                model_choice = allowed_models[i % len(allowed_models)]
                models_used.append({"micro_prompt": prompt, "model": model_choice})
                
                provider = settings.MODEL_CONFIG[model_choice]["provider"]
                if provider == "openai":
                    tasks.append(call_openai(prompt))
                elif provider == "huggingface":
                    tasks.append(call_huggingface(prompt))
                else: # "local"
                    tasks.append(call_local(prompt))
        else:
            # A specific model was requested (access is already validated in the router)
            provider = settings.MODEL_CONFIG[requested_model]["provider"]
            for prompt in prompts:
                models_used.append({"micro_prompt": prompt, "model": requested_model})
                if provider == "openai":
                    tasks.append(call_openai(prompt))
                elif provider == "huggingface":
                    tasks.append(call_huggingface(prompt))
                else: # "local"
                    tasks.append(call_local(prompt))

        # Process all tasks concurrently
        responses = await asyncio.gather(*tasks)
        aggregated_response = " ".join(filter(None, responses))
        
        return aggregated_response, models_used

