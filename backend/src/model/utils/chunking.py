from src.model.utils.embedding import tokenizer  # återanvänd tokenizer från embedding.py

def chunk_text(text: str, max_tokens: int = 100):
    sentences = text.split(". ")
    chunks = []
    current_chunk = []

    for sentence in sentences:
        current_chunk.append(sentence.strip())
        tokenized = tokenizer(" ".join(current_chunk), return_tensors="pt", truncation=False)
        if tokenized.input_ids.shape[1] > max_tokens:
            current_chunk.pop()
            chunks.append(". ".join(current_chunk) + ".")
            current_chunk = [sentence.strip()]

    if current_chunk:
        chunks.append(". ".join(current_chunk) + ".")

    return chunks