# File: backend/fastapi/services/semantic_search.py

import os
import numpy as np
from typing import List, Dict
from collections import defaultdict
import math
import time

# Import observability
try:
    from backend.fastapi.observability.honeycomb import get_tracer
    tracer = get_tracer(__name__)
except ImportError:
    # Fallback if observability module is not available
    class MockTracer:
        def start_as_current_span(self, name):
            from contextlib import contextmanager
            @contextmanager
            def mock_span():
                yield None
            return mock_span()
    tracer = MockTracer()

# Debugging helper function for consistent logging
def debug_log(message: str):
    """Utility function to print debug logs with a consistent format."""
    print(f"[DEBUG] {message}")

def load_tfidf_components(cache_dir: str) -> Dict[str, Dict[str, np.ndarray]]:
    """Load the sparse TF-IDF matrix and associated metadata from cache."""
    with tracer.start_as_current_span("load_tfidf_components") as span:
        matrix_path = os.path.join(cache_dir, "tfidf_matrix.npz")
        metadata_path = os.path.join(cache_dir, "tfidf_metadata.npz")
        document_metadata_path = os.path.join(cache_dir, "document_metadata.npz")

        # Load sparse matrix components using numpy
        debug_log(f"Loading sparse TF-IDF matrix from: {matrix_path}")
        matrix_data = np.load(matrix_path)
        debug_log(f"Loaded matrix file: {matrix_path}")
        debug_log(f"Matrix keys found: {matrix_data.files}")

        # Extract components from the npz file
        data = matrix_data['data']
        indices = matrix_data['indices']
        indptr = matrix_data['indptr']
        shape = tuple(matrix_data['shape'])

        debug_log(f"TF-IDF matrix shape: {shape}, data length: {len(data)}, indices length: {len(indices)}")
        if span:
            span.set_attribute("tfidf.matrix_shape", str(shape))
            span.set_attribute("tfidf.data_length", len(data))

        # Load metadata
        debug_log(f"Loading metadata from: {metadata_path}")
        metadata = np.load(metadata_path, allow_pickle=True)
        debug_log(f"Loaded metadata keys: {metadata.files}")
        vocabulary = metadata['vocabulary'].item()
        idf_values = metadata['idf_values']
        
        if span:
            span.set_attribute("tfidf.vocabulary_size", len(vocabulary))

        # Load document metadata and print available keys for debugging
        debug_log(f"Loading document metadata from: {document_metadata_path}")
        document_metadata = np.load(document_metadata_path, allow_pickle=True)
        debug_log(f"Document metadata keys: {document_metadata.files}")

        documents = document_metadata['documents']

        debug_log(f"Loaded document metadata with {len(documents)} entries.")
        if span:
            span.set_attribute("tfidf.document_count", len(documents))
            
        return {
            "tfidf_matrix": {
                "data": data,
                "indices": indices,
                "indptr": indptr,
                "shape": shape
            },
            "vocabulary": vocabulary,
            "idf_values": idf_values,
            "documents": documents
        }

def vectorize_query(query: str, vocabulary: Dict[str, int], idf_values: np.ndarray) -> Dict[int, float]:
    """Create a sparse representation for the query based on the vocabulary and IDF values."""
    with tracer.start_as_current_span("vectorize_query") as span:
        debug_log(f"Vectorizing query: '{query}'")
        query_vector = defaultdict(float)
        tokens = query.lower().split()
        token_counts = {token: tokens.count(token) for token in set(tokens)}

        for term, count in token_counts.items():
            if term in vocabulary:
                index = vocabulary[term]
                query_vector[index] = count * idf_values[index]

        debug_log(f"Query vector created with {len(query_vector)} non-zero entries")
        if span:
            span.set_attribute("query.token_count", len(tokens))
            span.set_attribute("query.vector_size", len(query_vector))
            
        return query_vector

def cosine_similarity_manual(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Manually compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)

    if norm_vec1 != 0 and norm_vec2 != 0:
        return dot_product / (norm_vec1 * norm_vec2)
    return 0.0

def semantic_search(query: str, cache_dir: str, top_n: int = 5) -> List[Dict]:
    """Perform a semantic search using the precomputed TF-IDF matrix."""
    with tracer.start_as_current_span("semantic_search_core") as span:
        debug_log(f"Starting semantic search for query: '{query}' in directory: {cache_dir}")
        
        if span:
            span.set_attribute("search.query", query)
            span.set_attribute("search.top_n", top_n)
            span.set_attribute("search.cache_dir", cache_dir)
            
        try:
            # Load the TF-IDF matrix and metadata
            tfidf_data = load_tfidf_components(cache_dir)
            tfidf_matrix = tfidf_data['tfidf_matrix']
            vocabulary = tfidf_data['vocabulary']
            idf_values = tfidf_data['idf_values']
            documents = tfidf_data['documents']
        except RuntimeError as e:
            debug_log(f"Failed to load TF-IDF components: {e}")
            if span:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise RuntimeError(f"Semantic search failed: {e}")

        # Create a vector for the query
        try:
            query_vector = vectorize_query(query, vocabulary, idf_values)
        except Exception as e:
            debug_log(f"Error vectorizing query '{query}': {e}")
            if span:
                span.record_exception(e)
            raise RuntimeError(f"Query vectorization failed: {e}")

        # Calculate cosine similarities manually
        try:
            with tracer.start_as_current_span("calculate_similarities") as sim_span:
                debug_log("Calculating cosine similarities...")
                start_time = time.time()
                
                data, indices, indptr, shape = (
                    tfidf_matrix["data"],
                    tfidf_matrix["indices"],
                    tfidf_matrix["indptr"],
                    tfidf_matrix["shape"]
                )

                # Create a sparse vector representation for the query
                query_sparse_vector = np.zeros(shape[1])

                for index, value in query_vector.items():
                    query_sparse_vector[index] = value

                # Calculate cosine similarity manually
                cosine_similarities = []
                for i in range(shape[0]):
                    document_vector = np.zeros(shape[1])
                    start_idx = indptr[i]
                    end_idx = indptr[i + 1]
                    document_vector[indices[start_idx:end_idx]] = data[start_idx:end_idx]

                    # Cosine similarity calculation
                    cosine_similarity_score = cosine_similarity_manual(document_vector, query_sparse_vector)
                    cosine_similarities.append((cosine_similarity_score, i))

                duration = time.time() - start_time
                if sim_span:
                    sim_span.set_attribute("calculation.duration_seconds", duration)
                    sim_span.set_attribute("calculation.documents_processed", shape[0])

            # Sort by similarity in descending order and return top_n results
            cosine_similarities.sort(reverse=True, key=lambda x: x[0])
            top_results = cosine_similarities[:top_n]

            # Retrieve corresponding documents and return results
            results = []
            for score, idx in top_results:
                document = documents[idx]  # Directly access the document from the dict
                results.append({
                    "score": score,
                    "document": document
                })

            debug_log(f"Search results returned: {len(results)}")
            if span:
                span.set_attribute("search.results_count", len(results))
                
            return results

        except Exception as e:
            debug_log(f"Error during semantic search: {e}")
            if span:
                span.record_exception(e)
            raise RuntimeError(f"Semantic search failed: {e}")
