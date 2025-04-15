from src.model.tools.internet_search import search_duckduckgo

results = search_duckduckgo("how does langchain memory work?")
for r in results:
    print("\n---\n" + r)
