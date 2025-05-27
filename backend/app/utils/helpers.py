def load_yaml_knowledge():
    """Helper to load initial YAML knowledge"""
    import yaml
    try:
        with open('data/knowledge_base.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML: {e}")
        return {}