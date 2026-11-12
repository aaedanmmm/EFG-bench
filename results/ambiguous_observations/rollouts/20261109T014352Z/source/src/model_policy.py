"""Model routing policy for benchmark runs."""


def require_openrouter(model):
    name = str(model)
    provider, _, model_id = name.partition("/")
    if provider != "openrouter" or not model_id.strip():
        raise ValueError("Use an OpenRouter model ID in the form openrouter/<publisher>/<model>.")
