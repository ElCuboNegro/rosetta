"""Project pipelines registry.

This module registers all the modular pipelines for the Rosetta dictionary project.
Pipelines are organized by functional area for better maintainability and clarity.
We apply namespacing to each pipeline to enable the "Modular Pipeline" expand/collapse
feature in Kedro Viz, while keeping inputs and outputs global to maintain connectivity.
"""

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline, pipeline
from .pipelines import output_formatting, book_alignment, sense_induction, catalog_alignment


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    The pipelines are organized into the following categories:

    1. Data Acquisition: Download raw data sources
    2. Wiktionary Parsing: Parse JSONL files into DataFrames
    3. Bridge Combination: Merge multi-language bridge data
    4. Data Cleaning: Filter unwanted entries
    5. Feature Engineering: Add computed features
    6. Example Processing: Process Tatoeba sentences
    7. Language Alignment: Align Spanish-Hebrew entries
    8. Phonemization: Generate Hebrew IPA
    9. Output Formatting: Format final JSON
    10. Metrics (Parsing): Statistics for parsing phase
    11. Metrics (Alignment): Statistics for alignment phase

    Returns:
        A mapping from pipeline names to Pipeline objects.
    """
    found_pipelines = find_pipelines()
    pipelines = {}

    for name, pipe in found_pipelines.items():
        # Separate parameters from other inputs
        # Kedro requires parameters to be passed via the 'parameters' argument
        # while datasets go into 'inputs'
        all_inputs = pipe.inputs()
        params = {n: n for n in all_inputs if n.startswith("params:") or n == "parameters"}
        inputs = {n: n for n in all_inputs if n not in params}

        # Manually wire metrics_alignment to read from language_alignment intermediates
        if name == "metrics_alignment":
            if "aligned_matches" in inputs:
                inputs["aligned_matches"] = "language_alignment.aligned_matches"
            if "enriched_entries" in inputs:
                inputs["enriched_entries"] = "language_alignment.enriched_entries"

        # Wire language_alignment to receive vector clusters from sense_induction
        if name == "language_alignment":
            if "induced_senses_clusters" in inputs:
                inputs["induced_senses_clusters"] = "sense_induction.induced_senses_clusters"

        # Wrap in namespace using the pipeline name
        # This creates the modular pipeline structure in Kedro Viz
        pipelines[name] = pipeline(
            pipe,
            namespace=name,
            inputs=inputs,
            outputs={ds: ds for ds in pipe.outputs()},
            parameters=params,
        )

    # Explicitly register pipelines that might be missed by find_pipelines
    # We apply the same namespacing logic as the loop above
    for name, module in [
        ("sense_induction", sense_induction),
        ("book_alignment", book_alignment),
        ("catalog_alignment", catalog_alignment),
        ("output_formatting", output_formatting),
    ]:
        pipe = module.create_pipeline()
        all_inputs = pipe.inputs()
        params = {n: n for n in all_inputs if n.startswith("params:") or n == "parameters"}
        inputs = {n: n for n in all_inputs if n not in params}

        pipelines[name] = pipeline(
            pipe,
            namespace=name,
            inputs=inputs,
            outputs={ds: ds for ds in pipe.outputs()},
            parameters=params,
        )
    pipelines["__default__"] = sum(pipelines.values())

    return pipelines
