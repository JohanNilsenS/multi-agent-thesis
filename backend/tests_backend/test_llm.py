# test_llm.py

from src.model.llm_client import LLMClient

def main():
    llm = LLMClient()
    prompt = "Tell me a fun fact about space."
    response = llm.query(prompt)
    print(f"LLM Response:\n{response}")

if __name__ == "__main__":
    main()
