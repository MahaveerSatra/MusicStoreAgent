"""
TuneDesk — Deep Agent supervisor with two specialist sub-agents.

Architecture:
  create_deep_agent() supervisor
    ├── account_agent: order history, invoice details, customer profile
    └── music_agent:   artist search, album browsing, genre recommendations

Customer identity is injected via context_schema (CustomerContext) so the
LLM never sees or passes customer_id — it flows securely through ToolRuntime.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent, SubAgent

from prompts import SUPERVISOR_PROMPT, ACCOUNT_AGENT_PROMPT, MUSIC_AGENT_PROMPT
from tools import ACCOUNT_TOOLS, MUSIC_TOOLS, CustomerContext

load_dotenv()

# ---------------------------------------------------------------------------
# LLM — NVIDIA NIM (OpenAI-compatible endpoint)
# ---------------------------------------------------------------------------

def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-405b-instruct"),
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API_KEY"],
        temperature=0,
    )


# ---------------------------------------------------------------------------
# Sub-agent definitions
# ---------------------------------------------------------------------------

account_agent: SubAgent = {
    "name": "account_agent",
    "description": (
        "Handles all questions about the customer's account: "
        "purchase history, past invoices, order details, and profile information. "
        "Call this agent for anything related to what the customer has bought or spent."
    ),
    "system_prompt": ACCOUNT_AGENT_PROMPT,
    "tools": ACCOUNT_TOOLS,
    "model": _get_llm(),
}

music_agent: SubAgent = {
    "name": "music_agent",
    "description": (
        "Handles music discovery: searching for artists, browsing albums, "
        "listing tracks, and recommending music by genre. "
        "Call this agent for any question about what music is available in the store."
    ),
    "system_prompt": MUSIC_AGENT_PROMPT,
    "tools": MUSIC_TOOLS,
    "model": _get_llm(),
}

# ---------------------------------------------------------------------------
# Deep Agent supervisor
# ---------------------------------------------------------------------------

agent = create_deep_agent(
    model=_get_llm(),
    system_prompt=SUPERVISOR_PROMPT,
    subagents=[account_agent, music_agent],
    context_schema=CustomerContext,
    checkpointer=True,   # enables conversation memory across turns in Studio
    name="tunedesk",
)
