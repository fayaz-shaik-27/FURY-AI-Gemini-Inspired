"""
ai_handler.py
© 2026 Fayaz Ahmed Shaik. All rights reserved.
─────────────
Handles all AI intelligence:
  - Maintains per-user conversation memory (in-memory dict)
  - Detects basic intent (greeting, question, farewell, etc.)
  - Sends prompts to Groq LLM and returns the response
  - Applies a friendly, human-like assistant personality

All free – uses Groq's generous free tier (no credit card required).
Sign up at: https://console.groq.com/
"""

import os
import logging
from collections import defaultdict
from datetime import datetime
from groq import Groq

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Groq client – uses GROQ_API_KEY from .env automatically
# ──────────────────────────────────────────────────────────────
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
_ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Fury AI")

# ──────────────────────────────────────────────────────────────
#  System prompt – personality & instructions for the LLM
#  Injected at the start of every conversation.
# ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = f"""
You are {_ASSISTANT_NAME}, a warm, friendly, and highly intelligent AI voice assistant.
Your job is to help users via voice and text messages – just like a helpful personal assistant.

Personality guidelines:
- Be conversational, empathetic, and concise (keep replies under 3 sentences when possible).
- Use natural spoken language – avoid bullet points, markdown, or headers.
- Show personality: be warm and occasionally witty, but always professional.
- If you don't know something, say so honestly rather than making things up.
- Adapt your tone to the user's mood (if they sound stressed, be calming).

Important: Your replies will be converted to audio, so respond as you would speak – naturally.
Today's date is {datetime.now().strftime("%A, %B %d, %Y")}.
""".strip()

# ──────────────────────────────────────────────────────────────
#  Per-user conversation memory
#  Key: platform user_id (int or str)
#  Value: list of {"role": "user"|"assistant", "content": str}
#
#  Note: This is in-memory only. Memory is lost on bot restart.
#  For persistence, swap this dict with a SQLite/Redis store.
# ──────────────────────────────────────────────────────────────
_memory: dict[str | int, list[dict]] = defaultdict(list)

# How many past messages to keep per user (controls context window)
_MAX_HISTORY_PAIRS = 10  # 10 pairs = 20 messages kept


# ──────────────────────────────────────────────────────────────
#  Intent Detection  (rule-based, no ML needed)
# ──────────────────────────────────────────────────────────────

_INTENT_PATTERNS: dict[str, list[str]] = {
    "creator": ["who is your creator", "who created you", "who made you", "who is your developer"],
    "greeting": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy", "sup"],
    "farewell": ["bye", "goodbye", "see you", "take care", "later", "ciao", "gotta go"],
    "gratitude": ["thank", "thanks", "thank you", "appreciate", "cheers"],
    "help": ["help", "can you", "could you", "assist", "support", "i need"],
    "question": ["what", "when", "where", "why", "how", "who", "which", "?"],
    "affirmation": ["yes", "yeah", "yep", "sure", "okay", "ok", "absolutely", "of course"],
    "negation": ["no", "nope", "nah", "not really", "i don't think so"],
}


def detect_intent(text: str) -> str:
    """
    Returns the dominant intent category of the user's message.
    Uses simple keyword matching — no ML required.

    Args:
        text: Raw transcribed user input.

    Returns:
        Intent label (e.g., 'greeting', 'question', 'unknown').
    """
    text_lower = text.lower()
    for intent, keywords in _INTENT_PATTERNS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "unknown"


# ──────────────────────────────────────────────────────────────
#  Memory helpers
# ──────────────────────────────────────────────────────────────

def get_history(session_id: str) -> list[dict]:
    """Returns the stored conversation history for a specific session."""
    return _memory[session_id]


def add_to_history(session_id: str, role: str, content: str) -> None:
    """
    Appends a message to the session's history and trims older messages.
    """
    _memory[session_id].append({"role": role, "content": content})

    # Trim: keep only the most recent N exchanges (2 msgs per exchange)
    max_messages = _MAX_HISTORY_PAIRS * 2
    if len(_memory[session_id]) > max_messages:
        _memory[session_id] = _memory[session_id][-max_messages:]


def load_history_to_memory(session_id: str, messages: list[dict]) -> None:
    """
    Pre-populates the in-memory context from the database history.
    Messages should be a list of {"role": "user"|"assistant", "message": "..."}.
    """
    if session_id in _memory and len(_memory[session_id]) > 0:
        return # Already loaded or active
    
    formatted = []
    for m in messages:
        # Convert DB 'assistant' role to AI handler's 'assistant'
        role = 'assistant' if m['role'] in ['assistant', 'ai'] else 'user'
        formatted.append({"role": role, "content": m['message']})
    
    _memory[session_id] = formatted
    logger.info(f"Loaded {len(formatted)} messages into memory for session {session_id}")


def clear_history(session_id: str) -> None:
    """Wipes conversation memory for a session."""
    _memory[session_id] = []
    logger.info(f"Memory cleared for session {session_id}.")


def generate_session_title(user_text: str) -> str:
    """
    Generates a very short (3-5 word) title for the conversation based on the first input.
    """
    try:
        prompt = f"Generate a 3 to 4 word title for a conversation that starts with: '{user_text}'. Return ONLY the title, no quotes or punctuation."
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.5
        )
        title = response.choices[0].message.content.strip()
        # Clean up in case LLM added quotes
        title = title.replace('"', '').replace("'", "")
        return title
    except Exception as e:
        logger.error(f"Title generation failed: {e}")
        return "New Conversation"


# ──────────────────────────────────────────────────────────────
#  Main AI response function
# ──────────────────────────────────────────────────────────────

_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

def generate_response(session_id: str, user_text: str, image_data: str = None) -> str:
    """
    Generates an AI response using Groq LLM, with full conversation memory.
    Supports optional image data (base64 string) for vision tasks.
    """
    intent = detect_intent(user_text)
    logger.info(f"Session {session_id} | Intent: {intent} | Input: '{user_text[:80]}' | Image: {'Yes' if image_data else 'No'}")

    if intent == "creator":
        creator_reply = "My creator is Fayaz Ahmed, His screen name is Fury So he named me Fury"
        add_to_history(session_id, "user", user_text)
        add_to_history(session_id, "assistant", creator_reply)
        return creator_reply

    # Build the full message list for the API call
    # We don't store the image in history to keep it lean, but we use it for the current turn
    
    current_model = _VISION_MODEL if image_data else _MODEL
    
    if image_data:
        # Groq vision models expect a specific format for multimodal content
        current_user_msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}"
                    }
                }
            ]
        }
    else:
        current_user_msg = {"role": "user", "content": user_text}

    # Store user's message in memory (only text part for history)
    add_to_history(session_id, "user", user_text)

    # Build history (excluding current turn which we handle specially if it has an image)
    history = get_history(session_id)[:-1] # All except the one we just added
    
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + history + [current_user_msg]

    try:
        response = _client.chat.completions.create(
            model=current_model,
            messages=messages,
            max_tokens=300 if image_data else 150, # More tokens for image descriptions
            temperature=0.75,
            top_p=0.9,
        )

        reply = response.choices[0].message.content.strip()
        logger.info(f"AI reply for session {session_id}: '{reply[:80]}'")

        # Store assistant's reply in memory for next turn
        add_to_history(session_id, "assistant", reply)

        return reply

    except Exception as e:
        logger.error(f"LLM call failed for session {session_id}: {e}", exc_info=True)
        # Friendly fallback so the bot doesn't go silent on errors
        return "I'm sorry, I ran into a little hiccup. Could you try saying that again?"
