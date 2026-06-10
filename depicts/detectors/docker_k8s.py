import os

def detect_docker_k8s(root):
    """Detects Docker/Kubernetes stacks. Returns None if the directory is inaccessible."""
    try:
        root_files = [f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]
    except PermissionError:
        return None

    has_docker = os.path.exists(os.path.join(root, 'Dockerfile'))
    has_k8s = any(f.endswith('.yaml') or f.endswith('.yml') for f in root_files)

    if has_docker or has_k8s:
        priority = ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']
        priority.extend([f for f in root_files if f.endswith('.yaml') or f.endswith('.yml')])
        return "Docker / Kubernetes", priority
    return None
