import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from backend.models.request import Req
from backend.models.response import Res
from backend.services.llm_router import LLMRouter
from backend.services.supabase import SupabaseService
from backend.core.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Dependency injections remain the same ---
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
    try:
        # ✨ --- NEW: Enforce "auto" model selection --- ✨
        # This check ensures that users cannot bypass the intelligent router.
        if request.model != "auto":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Manual model selection is currently disabled. Please use 'auto' mode."
            )

        req_id = str(uuid.uuid4())
        chat_id = request.chatId if request.chatId else str(uuid.uuid4())
        user_email = current_user.get("email")
        user_subscription = current_user.get("subscription_tier", "free")

        # The old validation logic is no longer needed because of the check above,
        # but we can leave it commented out for future use.
        # if request.model != "auto":
        #     validate_model_access(request.model, user_subscription)

        aggregated_response, models_used = await llm_router.route_and_process_prompts(
            user_query=request.query,
            subscription_tier=user_subscription,
            requested_model=request.model  # This will always be "auto"
        )

        await supabase_service.save_chat_history(
            chat_id=chat_id,
            req_id=req_id,
            email=user_email,
            query=request.query,
            response=aggregated_response,
            models_used=models_used
        )

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
        raise he
    except Exception as e:
        req_id_for_log = locals().get("req_id", "N/A")
        logger.error(f"Error processing request {req_id_for_log}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )