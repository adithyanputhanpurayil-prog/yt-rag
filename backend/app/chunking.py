"""Split raw transcript text into overlapping chunks suitable for embedding."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ~800 chars (~150-200 tokens) with overlap keeps chunks small enough for
# precise retrieval but large enough to preserve context across sentence
# boundaries. Tune per video length / LLM context budget.
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_transcript(text: str) -> list[str]:
    return _splitter.split_text(text)
