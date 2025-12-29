from rosetta_dict.pipeline_registry import register_pipelines


def main():
    pipelines = register_pipelines()
    print("Registered Pipelines:")
    for name, pipe in pipelines.items():
        print(f"- {name}")
        print(f"  Inputs: {pipe.inputs()}")
        print(f"  Outputs: {pipe.outputs()}")
        if name == "__default__":
            print("  Nodes:")
            for node in pipe.nodes:
                print(f"    - {node.name} (Out: {node.outputs})")


if __name__ == "__main__":
    main()
