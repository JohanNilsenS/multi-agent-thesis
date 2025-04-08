from transformers import AutoTokenizer, AutoModel
import torch

# Load once
tokenizer = AutoTokenizer.from_pretrained("KBLab/bert-base-swedish-cased")
model = AutoModel.from_pretrained("KBLab/bert-base-swedish-cased")

def get_embedding_from_llm(text: str) -> list[float]:
    inputs = tokenizer(
    text,
    return_tensors="pt",
    truncation=True,
    padding=True,
    max_length=512
)

    with torch.no_grad():
        outputs = model(**inputs)

    # Mean pooling
    token_embeddings = outputs.last_hidden_state.squeeze(0)
    attention_mask = inputs["attention_mask"].squeeze(0)
    mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size())
    masked_embeddings = token_embeddings * mask
    summed = torch.sum(masked_embeddings, dim=0)
    count = torch.clamp(mask.sum(dim=0), min=1e-9)
    mean_pooled = summed / count

    return mean_pooled.tolist()
