"""
Test the improved clustering on 'pretender' examples.
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Import the improved clustering functions
from src.rosetta_dict.pipelines.sense_induction.nodes import (
    compute_embeddings,
    compute_ensemble_embeddings,
    find_optimal_k_elbow,
    cluster_hdbscan,
    validate_clustering_quality,
    HDBSCAN_AVAILABLE
)

print("=" * 80)
print("Testing Improved Sense Clustering on 'pretender'")
print("=" * 80)

# Load the existing clusters
clusters_path = Path("data/04_feature/sense_clusters.parquet")
if not clusters_path.exists():
    print(f"Error: {clusters_path} not found!")
    print("Please run the sense induction pipeline first.")
    exit(1)

df = pd.read_parquet(clusters_path)
pretender_df = df[df['source_word'] == 'pretender'].copy()

print(f"\nFound {len(pretender_df)} examples for 'pretender'")
print(f"Original clustering: {pretender_df['sense_cluster_id'].nunique()} clusters\n")

# Display original clusters
print("ORIGINAL CLUSTERING:")
print("-" * 80)
for cluster_id in sorted(pretender_df['sense_cluster_id'].unique()):
    cluster_examples = pretender_df[pretender_df['sense_cluster_id'] == cluster_id]
    print(f"\nCluster {cluster_id} ({len(cluster_examples)} examples):")
    for idx, row in cluster_examples.iterrows():
        print(f"  - {row['sentence_text'][:100]}...")

# Test improved clustering
print("\n" + "=" * 80)
print("TESTING IMPROVED CLUSTERING")
print("=" * 80)

# 1. Test standard embeddings
print("\n1. Computing standard embeddings...")
standard_embeddings = compute_embeddings(
    pretender_df['sentence_text'],
    pretender_df['source_word']
)
standard_emb_array = np.stack(standard_embeddings.values)
print(f"   Shape: {standard_emb_array.shape}")

# 2. Test ensemble embeddings
print("\n2. Computing ensemble embeddings...")
ensemble_embeddings = compute_ensemble_embeddings(
    pretender_df['sentence_text'],
    pretender_df['source_word']
)
ensemble_emb_array = np.stack(ensemble_embeddings.values)
print(f"   Shape: {ensemble_emb_array.shape}")

# 3. Test optimal k finding
print("\n3. Finding optimal k using elbow method...")
optimal_k, metrics = find_optimal_k_elbow(ensemble_emb_array, max_k=5)
print(f"   Optimal k: {optimal_k}")
print(f"   Elbow k: {metrics['elbow_k']}")
print(f"   Best silhouette k: {metrics['best_silhouette_k']}")
if metrics['silhouette_scores']:
    print(f"   Silhouette scores: {[f'{s:.3f}' for s in metrics['silhouette_scores']]}")

# 4. Test KMeans with optimal k
print(f"\n4. Testing KMeans with optimal k={optimal_k}...")
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
kmeans_labels = kmeans.fit_predict(ensemble_emb_array)

print("\nKMeans Results:")
print("-" * 80)
for cluster_id in sorted(np.unique(kmeans_labels)):
    cluster_mask = kmeans_labels == cluster_id
    cluster_examples = pretender_df[cluster_mask]
    print(f"\nCluster {cluster_id} ({len(cluster_examples)} examples):")
    for idx, row in cluster_examples.iterrows():
        print(f"  - {row['sentence_text']}")

# Validate quality
quality_kmeans = validate_clustering_quality(ensemble_emb_array, kmeans_labels, 'pretender')
print(f"\nKMeans Quality Metrics:")
print(f"  Quality Score: {quality_kmeans['quality_score']:.3f}")
print(f"  Silhouette Score: {quality_kmeans['silhouette_score']:.3f}")
print(f"  Davies-Bouldin Score: {quality_kmeans['davies_bouldin_score']:.3f}")
print(f"  Cluster Balance: {quality_kmeans['cluster_balance']:.3f}")
if quality_kmeans['warnings']:
    print(f"  Warnings: {', '.join(quality_kmeans['warnings'])}")

# 5. Test HDBSCAN (if available)
if HDBSCAN_AVAILABLE:
    print(f"\n5. Testing HDBSCAN density-based clustering...")
    hdbscan_labels, hdbscan_metadata = cluster_hdbscan(ensemble_emb_array, min_cluster_size=2)

    print(f"\nHDBSCAN Results:")
    print(f"  Found {hdbscan_metadata['n_clusters']} clusters")
    print(f"  Noise points: {hdbscan_metadata['n_noise_points']}")
    print("-" * 80)

    for cluster_id in sorted(np.unique(hdbscan_labels)):
        cluster_mask = hdbscan_labels == cluster_id
        cluster_examples = pretender_df[cluster_mask]
        label = "NOISE" if cluster_id == -1 else f"Cluster {cluster_id}"
        print(f"\n{label} ({len(cluster_examples)} examples):")
        for idx, row in cluster_examples.iterrows():
            print(f"  - {row['sentence_text']}")

    # Validate quality (excluding noise)
    if hdbscan_metadata['n_clusters'] > 0:
        valid_mask = hdbscan_labels >= 0
        if np.sum(valid_mask) > 1:
            quality_hdbscan = validate_clustering_quality(
                ensemble_emb_array[valid_mask],
                hdbscan_labels[valid_mask],
                'pretender'
            )
            print(f"\nHDBSCAN Quality Metrics:")
            print(f"  Quality Score: {quality_hdbscan['quality_score']:.3f}")
            print(f"  Silhouette Score: {quality_hdbscan['silhouette_score']:.3f}")
            print(f"  Davies-Bouldin Score: {quality_hdbscan['davies_bouldin_score']:.3f}")
            if quality_hdbscan['warnings']:
                print(f"  Warnings: {', '.join(quality_hdbscan['warnings'])}")
else:
    print("\n5. HDBSCAN not available (install with: pip install hdbscan)")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)

# Summary
print("\nSUMMARY:")
print(f"- Original clustering: 3 fixed clusters")
print(f"- Improved clustering: {optimal_k} optimal clusters (data-driven)")
print(f"- Using ensemble embeddings: better sense discrimination")
print(f"- Quality validation: automatic detection of issues")
print("\nThe improved algorithm should better separate:")
print("  1. 'pretender a' (to court/woo)")
print("  2. 'pretender + infinitive' (to intend/plan)")
print("  3. 'pretender que...' with feigning meaning (to pretend)")
print("  4. 'pretender que...' with expectation meaning (to expect/claim)")
