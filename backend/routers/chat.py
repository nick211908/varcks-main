import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.request import Req
from backend.models.response import Res
from backend.services.llm_router import LLMRouter
from backend.services.supabase import SupabaseService
from backend.core.security import get_current_user, validate_model_access

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
    supabase_service: SupabaseService = Depends(get_supabase_service),
    current_user: dict = Depends(get_current_user)
):
    """
    Main endpoint to process a user's chat request.
    Orchestrates prompt splitting, LLM routing, and response aggregation.
    """
    try:
        # 1. Generate unique IDs for the request and for the chat session if not provided.
        # The client receives these IDs in the response and can use the chatId to continue the conversation.
        req_id = str(uuid.uuid4())
        chat_id = request.chatId if request.chatId else str(uuid.uuid4())

        user_email = current_user.get("email")
        user_subscription = current_user.get("subscription_tier", "free")

        # 2. Validate that the user's subscription allows them to use the requested model.
        # This check is performed only if a specific model is requested (not 'auto').
        if request.model != "auto":
            validate_model_access(request.model, user_subscription)

        # 3. Process the prompt, get the aggregated response and the list of models used.
        # --- THIS IS THE FIX ---
        # We now capture both `aggregated_response` and `models_used` from the return value.
        aggregated_response, models_used = await llm_router.route_and_process_prompts(
            user_query=request.query,
            subscription_tier=user_subscription,
            requested_model=request.model
        )

        # 4. Save the interaction to the database.
        # --- AND WE USE THE CAPTURED VARIABLE HERE ---
        # The `models_used` variable is now passed to the save function.
        await supabase_service.save_chat_history(
            chat_id=chat_id,
            req_id=req_id,
            email=user_email,
            query=request.query,
            response=aggregated_response,
            models_used=models_used  # Pass the captured list
        )

        # 5. Construct and return the final response object.
        return Res(
            reqId=req_id,
            chatId=chat_id,
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
        # Use a placeholder if req_id hasn't been generated yet (e.g., error during request binding).
        req_id_for_log = locals().get("req_id", "N/A")
        logger.error(f"Error processing request {req_id_for_log}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
