import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the model once to be reused in subsequent calls
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.7, # A bit more creative for general tasks
    convert_system_message_to_human=True
)

# Define the chain of operations
prompt_template = ChatPromptTemplate.from_template("You are a helpful AI assistant. Respond to the following prompt:\n\n{prompt}")
chain = prompt_template | llm | StrOutputParser()

async def call_openai(prompt: str) -> str:
    """
    Calls the Google Gemini model, acting as a placeholder for a future OpenAI model call.
    """
    logger.info(f"-> Calling OpenAI Interface (using Google Model) with prompt: '{prompt[:50]}...'")
    try:
        response = await chain.ainvoke({"prompt": prompt})
        logger.info(f"<- OpenAI Interface (using Google Model) call successful.")
        return response
    except Exception as e:
        logger.error(f"[!!!] OpenAI Interface (using Google Model) call failed: {e}", exc_info=True)
        return f"Error from placeholder OpenAI Interface: {e}"