from sentence_transformers import SentenceTransformer

# Load once when the application starts
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")


def get_embeddings(texts):
    """
    Generate embeddings for a list of texts.
    """
    return embedding_model.encode(
        texts,
        convert_to_numpy=True
    )
