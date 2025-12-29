import pytest
import pandas as pd
from rosetta_dict.pipelines.language_alignment.nodes import cluster_polysemic_senses


def test_cluster_polysemic_senses_with_vectors():
    # 1. Setup Enriched Data (The "Receiver")
    enriched_data = pd.DataFrame(
        [
            # "banco" (bank) - Meaning 1: Financial
            {"es_word": "banco", "es_definition": "Entidad financiera", "sense_id": 1},
            # "banco" (bench) - Meaning 2: Seat
            {"es_word": "banco", "es_definition": "Asiento largo", "sense_id": 2},
            # "gato" (cat) - Simple word
            {"es_word": "gato", "es_definition": "Animal felino", "sense_id": 1},
        ]
    )

    # 2. Setup Induced Clusters (The "Brain" Output)
    # Simulator of what sense_induction pipeline outputs
    induced_clusters = pd.DataFrame(
        [
            # For "banco", financial definition gets cluster 100
            {
                "source_word": "banco",
                "sentence_text": "Voy al banco a depositar dinero.",
                "sense_cluster_id": 100,
            },
            # For "banco", seat definition gets cluster 200
            {
                "source_word": "banco",
                "sentence_text": "Me senté en el banco del parque.",
                "sense_cluster_id": 200,
            },
        ]
    )

    # NOTE: The current implementation of `cluster_polysemic_senses` compares definitions.
    # The `induced_clusters` from sense_induction are based on EXAMPLES (sentences).
    # We need to bridge this.
    # The `enrich_entries` step adds 'examples' to `enriched_data`.
    # Let's verify how we can link them.

    # Updated Enriched Data to include examples that match the induced clusters
    enriched_data["examples"] = [
        [{"es": "Voy al banco a depositar dinero.", "he": "..."}],  # Matches cluster 100
        [{"es": "Me senté en el banco del parque.", "he": "..."}],  # Matches cluster 200
        [],
    ]

    # 3. Execution
    # We pass the vector_clusters df.
    # Note: We haven't updated the function signature yet, so this test will fail/error initially if we ran it now.
    result_df = cluster_polysemic_senses(enriched_data, induced_clusters)

    # 4. Assertions
    # Check that "banco" rows have different semantic_cluster IDs
    banco_rows = result_df[result_df["es_word"] == "banco"]

    assert len(banco_rows) == 2
    # The cluster IDs should be distinct because the input vector clusters are distinct (100 vs 200)
    assert banco_rows.iloc[0]["semantic_cluster"] != banco_rows.iloc[1]["semantic_cluster"]

    # In the old logic (fuzzy), "Entidad financiera" and "Asiento largo" might also be distinct (similarity < 70),
    # but we want to ensure it USED the vector info.
    # We can check specific values if we map them directly, or just ensure distinctness for now.

    # Ideally, we'd pass a case where fuzzy matching FAILS (texts are similar) but vectors SUCCEED (meanings are different),
    # or vice versa. But for integration 'plumbing' test, passing the arg is the key step.
