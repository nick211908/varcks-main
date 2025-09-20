import asyncio
import logging

logger = logging.getLogger(__name__)

async def call_local(prompt: str) -> str:
	"""Minimal placeholder for a local model call.
	This would run an on-device model or local server in production.
	"""
	await asyncio.sleep(0)
	logger.debug(f"call_local received prompt: {prompt}")
	return f"[local response for: {prompt}]"

__all__ = ["call_local"]

