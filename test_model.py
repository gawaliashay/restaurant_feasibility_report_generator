# tests/test_model_loader.py

from src.common.model_loader import model_loader

def print_llm(label, obj):
    print(f"{label}: {obj.__class__.__name__}")

def run_basic_checks():
    # direct provider fetch
    groq = model_loader.load_llm("groq")
    print_llm("groq", groq)

    mistral = model_loader.load_llm("mistral")
    print_llm("mistral", mistral)

    openai = model_loader.load_llm("openai")
    print_llm("openai", openai)

    google = model_loader.load_llm("google")
    print_llm("google", google)

    # default-purpose fetch
    primary = model_loader.get_llm("primary_llm")
    print_llm("primary_llm", primary)

    fast = model_loader.get_llm("fast_llm")
    print_llm("fast_llm", fast)

    creative = model_loader.get_llm("creative_llm")
    print_llm("creative_llm", creative)

    analysis = model_loader.get_llm("analysis_llm")
    print_llm("analysis_llm", analysis)

if __name__ == "__main__":
    run_basic_checks()
