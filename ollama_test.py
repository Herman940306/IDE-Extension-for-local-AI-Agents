try:
    from langchain_community.llms import Ollama

    print("Successfully imported Ollama")
    # Try to instantiate it
    llm = Ollama(model="codellama:7b")
    print("Successfully instantiated Ollama")
    print(llm)
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
