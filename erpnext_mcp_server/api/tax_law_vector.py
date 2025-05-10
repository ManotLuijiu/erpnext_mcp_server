import frappe

import json
import numpy as np
import requests
from frappe.model.document import Document

# You can use various embedding providers (OpenAI, HuggingFace, etc.)
# For this example, we'll use a hypothetical API

EMBEDDING_API_URL = "https://your-embedding-service.com/embed"
EMBEDDING_API_KEY = "your-api-key"
VECTOR_DIMENSION = 1536  # Depends on your embedding model


def generate_embedding(text: str) -> list[float]:
    """Generate vector embedding for text using an embedding service"""
    try:
        response = requests.post(
            EMBEDDING_API_URL,
            headers={"Authorization": f"Bearer {EMBEDDING_API_KEY}"},
            json={"input": text, "model": "text-embedding-3-small"},
        )
        response.raise_for_status()
        embedding = response.json()["data"][0]["embedding"]
        return embedding
    except Exception as e:
        frappe.log_error(f"Error generating embedding: {str(e)}")
        return []


def update_tax_law_embedding(doc: Document, method=None):
    """Update the vector embedding for a tax law document"""
    if doc.doctype != "Thai Tax Law":
        return

    # Combine relevant text fields for embedding
    text_to_embed = f"{doc.title} {doc.summary} {doc.content_th} {doc.content_en}"

    # Generate embedding
    embedding = generate_embedding(text_to_embed)

    # Store embedding
    if embedding:
        doc.vector_embedding = json.dumps(embedding)
        # Skip db_update to avoid triggering another update
        doc.db_update_with_doctype = False
        frappe.db.set_value(
            "Thai Tax Law", doc.name, "vector_embedding", json.dumps(embedding)
        )
        doc.db_update_with_doctype = True


def search_similar_tax_laws(query: str, top_k: int = 5) -> list[dict]:
    """Search for tax laws similar to the query using vector search"""
    # Generate embedding for the query
    query_embedding = generate_embedding(query)
    if not query_embedding:
        return []

    # Get all tax law embeddings
    tax_laws = frappe.get_all(
        "Thai Tax Law",
        fields=["name", "title", "summary", "vector_embedding", "category"],
        filters={"is_active": 1},
    )

    # Calculate similarities
    results = []
    for law in tax_laws:
        if not law.get("vector_embedding"):
            continue

        law_embedding = json.loads(law.vector_embedding)
        # Calculate cosine similarity
        similarity = np.dot(query_embedding, law_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(law_embedding)
        )

        results.append(
            {
                "name": law.name,
                "title": law.title,
                "summary": law.summary,
                "category": law.category,
                "similarity": float(similarity),
            }
        )

    # Sort by similarity (highest first) and return top_k results
    return sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k]


@frappe.whitelist()
def manually_update_tax_laws():
    """Manually trigger tax law updates"""
    if not frappe.has_permission("Thai Tax Law", "write"):
        frappe.throw("You don't have permission to update tax laws")

    # Run in the background to avoid timeout
    frappe.enqueue(
        "your_app.thai_tax_law.scheduled_tasks.update_tax_laws",
        queue="long",
        timeout=1500,
    )

    return {"message": "Tax law update initiated in the background"}
