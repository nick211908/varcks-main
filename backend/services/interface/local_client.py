import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the model once to be reused
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.1, # Highly deterministic for tasks like translation
    convert_system_message_to_human=True
)

# Define the chain of operations
prompt_template = ChatPromptTemplate.from_template("You are a high-speed, privacy-focused AI assistant. Respond to the following prompt:\n\n{prompt}")
chain = prompt_template | llm | StrOutputParser()

async def call_local(prompt: str) -> str:
    """
    Calls the Google Gemini model, acting as a placeholder for a future local model call.
    """
    logger.info(f"-> Calling Local Interface (using Google Model) with prompt: '{prompt[:50]}...'")
    try:
        response = await chain.ainvoke({"prompt": prompt})
        logger.info(f"<- Local Interface (using Google Model) call successful.")
        return response
    except Exception as e:
        logger.error(f"[!!!] Local Interface (using Google Model) call failed: {e}", exc_info=True)
        return f"Error from placeholder Local Interface: {e}"

__all__ = ["call_local"]