import os
import litellm

def test_nvidia_embeddings():
    models = [
        "nvidia_nim/nvidia/nv-embedqa-e5-v5",
        "nvidia_nim/nvidia/nv-embed-v1"
    ]
    
    for model in models:
        print(f"\nTesting embedding model: {model}")
        try:
            response = litellm.embedding(
                model=model,
                input=["Test sentence for embedding dimensions."],
                input_type="passage",  # Required by NV-Embed
                encoding_format="float"
            )
            dim = len(response.data[0]['embedding'])
            print(f"SUCCESS! Dimension: {dim}")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_nvidia_embeddings()