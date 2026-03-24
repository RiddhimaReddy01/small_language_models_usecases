import ollama
try:
    models = ollama.list()
    for m in models['models']:
        print(m['name'])
except Exception as e:
    print(f"Error: {e}")
