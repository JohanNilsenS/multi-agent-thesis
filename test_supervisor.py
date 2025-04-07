# test_supervisor.py

from src.model.supervisor import SupervisorAgent
from src.model.tools.internet_search import search_duckduckgo

test_research = False
test_git = False
internet_search = True
def main():
    supervisor = SupervisorAgent()

    # After creating the supervisor and running a task
    git_agent = next(agent for agent in supervisor.agents if agent.name == "GitAgent")
    git_agent.print_file_index_preview()

    if test_research:
        task = "research why flamingos are pink"
        result = supervisor.delegate(task)

        print(f"Task Source: {result['source']}")
        print("Content:")
        print(result['content'])

        print("\n--- Running same task again to test DB retrieval ---\n")
        result = supervisor.delegate(task)
        print(f"Task Source: {result['source']}")
        print("Content:")
        print(result['content'])


    if test_git:
        print("\n--- Git Commit Summary ---\n")
        result = supervisor.delegate("git summary")
        print(result)

        print("\n--- Project Overview ---\n")
        result = supervisor.delegate("project overview")
        print(result)

        print("\n--- Suggestions ---\n")
        result = supervisor.delegate("suggest improvement")
        print(result)

        print("\n--- Explain Function: process_invoice ---\n")
        git_agent.reindex_files()
        explanation = git_agent.explain_function("explain_function")
        print(explanation)

        print("\n--- All Indexed Functions ---\n")
        for func in git_agent.list_all_functions():
            print(f"{func['name']}  ➜  {func['path']}")

    if internet_search:
        queries = [
            "research how to build a supervisor agent system in python",
            "research why the world is round"
        ]

        for query in queries:
            print(f"\n--- Research: {query} ---")
            result = supervisor.delegate(query)
            print(f"Source: {result['source']}")
            print(f"Content:\n{result['content']}")



if __name__ == "__main__":
    main()
