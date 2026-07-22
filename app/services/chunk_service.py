from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(pages):
    """
    Split extracted PDF pages into chunks while preserving page numbers.
    Prefer paragraph/sentence/word boundaries so chunks do not cut mid-word.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
        keep_separator=True,
    )

    chunks = []

    for page in pages:
        texts = splitter.split_text(page["text"])

        for text in texts:
            cleaned = text.strip()
            if cleaned:
                chunks.append({
                    "page": page["page"],
                    "text": cleaned,
                })

    return chunks
