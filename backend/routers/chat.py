import logging
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.request import Req
from backend.models.response import Res
from backend.services.llm_router import LLMRouter
from backend.services.supabase import SupabaseService
from backend.core.security import validate_model_access

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency Injection for services
def get_llm_router():
    return LLMRouter()

def get_supabase_service():
    return SupabaseService()

@router.post("/chat", response_model=Res)
async def process_chat(
    request: Req,
    llm_router: LLMRouter = Depends(get_llm_router),
    supabase_service: SupabaseService = Depends(get_supabase_service)
):
    """
    Main endpoint to process a user's chat request.
    Orchestrates prompt splitting, LLM routing, and response aggregation.
    """
    try:
        # 1. Validate that the user's subscription allows them to use the requested model.
        # This check is performed only if a specific model is requested (not 'auto').
        if request.model != "auto":
            validate_model_access(request.model, request.user_subs)

        # 2. Process the prompt, get the aggregated response and the list of models used.
        # --- THIS IS THE FIX ---
        # We now capture both `aggregated_response` and `models_used` from the return value.
        aggregated_response, models_used = await llm_router.route_and_process_prompts(
            user_query=request.query,
            subscription_tier=request.user_subs,
            requested_model=request.model
        )

        # 3. Save the interaction to the database.
        # --- AND WE USE THE CAPTURED VARIABLE HERE ---
        # The `models_used` variable is now passed to the save function.
        await supabase_service.save_chat_history(
            chat_id=request.chatId,
            req_id=request.reqId,
            email=request.email,
            query=request.query,
            response=aggregated_response,
            models_used=models_used  # Pass the captured list
        )

        # 4. Construct and return the final response object.
        return Res(
            reqId=request.reqId,
            chatId=request.chatId,
            query=request.query,
            Models=models_used,
            response=aggregated_response,
            statusCode=200,
            statusMessage="Success"
        )

    except HTTPException as he:
        # Re-raise HTTP exceptions (like permission denied) directly.
        raise he
    except Exception as e:
        logger.error(f"Error processing request {request.reqId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

