from src.model.utils.embedding import get_embedding_from_llm

def main():
    test_text = "Varför är flamingos rosa?"
    embedding = get_embedding_from_llm(test_text)

    print(f"Embedding length: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")

if __name__ == "__main__":
    main()