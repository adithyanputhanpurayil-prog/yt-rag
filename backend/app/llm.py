"""Turn retrieved chunks + a question into a grounded answer."""

import os
from openai import OpenAI

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
CHAT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You answer questions about a YouTube video using only the transcript "
    "excerpts provided. If the excerpts don't contain the answer, say you "
    "couldn't find it in the video rather than guessing."
)


def generate_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no matching excerpts found)"
    user_prompt = f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}"

    response = _client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
