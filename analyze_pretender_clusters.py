"""
Analyze the sense clustering for 'pretender' to diagnose misclustering issues.
"""
import pandas as pd
from pathlib import Path

# Read the sense clusters data
data_path = Path("data/04_feature/sense_clusters.parquet")

# Load and filter for 'pretender'
df = pd.read_parquet(data_path)
pretender_df = df[df['source_word'] == 'pretender']
pretender_examples = pretender_df.to_dict('records')

print(f"Found {len(pretender_examples)} examples for 'pretender'\n")
print("=" * 80)

# Group by sense cluster
by_cluster = {}
for ex in pretender_examples:
    cluster_id = ex.get('sense_cluster_id', -1)
    if cluster_id not in by_cluster:
        by_cluster[cluster_id] = []
    by_cluster[cluster_id].append(ex)

# Display each cluster
for cluster_id in sorted(by_cluster.keys()):
    examples = by_cluster[cluster_id]
    print(f"\nCLUSTER {cluster_id} ({len(examples)} examples):")
    print("-" * 80)
    for i, ex in enumerate(examples, 1):
        sentence = ex.get('sentence_text', '')
        source = ex.get('corpus_source', '')
        print(f"{i}. [{source}] {sentence}")
    print()

print("=" * 80)
print("\nMANUAL SENSE ANALYSIS:")
print("-" * 80)
print("Expected senses for 'pretender':")
print("  Sense A: to court/woo (pretender a alguien)")
print("  Sense B: to intend/plan/aim (pretender + infinitive)")
print("  Sense C: to pretend/feign (pretender que...)")
print("  Sense D: to claim/expect/aspire (other uses)")
print()
print("Check if the clustering aligns with these linguistic senses.")
