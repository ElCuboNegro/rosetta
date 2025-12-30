"""
Visualize sense clusters using dimensionality reduction.

Usage:
    python scripts/visualize_clusters.py pretender
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rosetta_dict.pipelines.sense_induction.nodes import (
    compute_embeddings,
    compute_ensemble_embeddings,
)


def visualize_clusters(word, use_ensemble=True):
    """Visualize clusters for a specific word using PCA and t-SNE."""
    # Load data
    clusters_path = Path("data/04_feature/sense_clusters.parquet")
    if not clusters_path.exists():
        print(f"Error: {clusters_path} not found!")
        return

    df = pd.read_parquet(clusters_path)
    word_df = df[df["source_word"] == word].copy()

    if len(word_df) == 0:
        print(f"No data found for word '{word}'")
        return

    print(f"Visualizing {len(word_df)} examples for '{word}'")

    # Compute embeddings
    if use_ensemble:
        embeddings_series = compute_ensemble_embeddings(
            word_df["sentence_text"], word_df["source_word"]
        )
        title_suffix = "(Ensemble Embeddings)"
    else:
        embeddings_series = compute_embeddings(
            word_df["sentence_text"], word_df["source_word"]
        )
        title_suffix = "(Standard Embeddings)"

    embeddings = np.stack(embeddings_series.values)
    labels = word_df["sense_cluster_id"].values

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # PCA reduction
    pca = PCA(n_components=2)
    embeddings_2d_pca = pca.fit_transform(embeddings)

    # t-SNE reduction
    if len(embeddings) > 2:
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(5, len(embeddings) - 1))
        embeddings_2d_tsne = tsne.fit_transform(embeddings)
    else:
        embeddings_2d_tsne = embeddings_2d_pca

    # Plot PCA
    colors = plt.cm.tab10(np.linspace(0, 1, len(np.unique(labels))))
    for cluster_id in np.unique(labels):
        mask = labels == cluster_id
        ax1.scatter(
            embeddings_2d_pca[mask, 0],
            embeddings_2d_pca[mask, 1],
            c=[colors[int(cluster_id)]],
            label=f"Cluster {int(cluster_id)}",
            s=100,
            alpha=0.7,
            edgecolors="black",
        )

    # Annotate points with truncated sentences
    for i, (x, y) in enumerate(embeddings_2d_pca):
        sentence = word_df.iloc[i]["sentence_text"][:30] + "..."
        ax1.annotate(
            sentence,
            (x, y),
            fontsize=8,
            alpha=0.7,
            xytext=(5, 5),
            textcoords="offset points",
        )

    ax1.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)")
    ax1.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)")
    ax1.set_title(f"PCA Projection - '{word}' {title_suffix}")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot t-SNE
    for cluster_id in np.unique(labels):
        mask = labels == cluster_id
        ax2.scatter(
            embeddings_2d_tsne[mask, 0],
            embeddings_2d_tsne[mask, 1],
            c=[colors[int(cluster_id)]],
            label=f"Cluster {int(cluster_id)}",
            s=100,
            alpha=0.7,
            edgecolors="black",
        )

    # Annotate t-SNE
    for i, (x, y) in enumerate(embeddings_2d_tsne):
        sentence = word_df.iloc[i]["sentence_text"][:30] + "..."
        ax2.annotate(
            sentence,
            (x, y),
            fontsize=8,
            alpha=0.7,
            xytext=(5, 5),
            textcoords="offset points",
        )

    ax2.set_xlabel("t-SNE Dimension 1")
    ax2.set_ylabel("t-SNE Dimension 2")
    ax2.set_title(f"t-SNE Projection - '{word}' {title_suffix}")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save figure
    output_dir = Path("data/06_metrics/cluster_visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{word}_{'ensemble' if use_ensemble else 'standard'}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\nSaved visualization to: {output_path}")

    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/visualize_clusters.py <word>")
        print("Example: python scripts/visualize_clusters.py pretender")
        sys.exit(1)

    word = sys.argv[1]
    use_ensemble = "--standard" not in sys.argv

    print(f"Visualizing clusters for: {word}")
    print(f"Using {'ensemble' if use_ensemble else 'standard'} embeddings\n")

    visualize_clusters(word, use_ensemble=use_ensemble)
