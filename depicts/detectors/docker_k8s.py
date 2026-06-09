import os

def detect_docker_k8s(root):
    has_docker = os.path.exists(os.path.join(root, 'Dockerfile'))
    has_k8s = any(f.endswith('.yaml') or f.endswith('.yml') for f in os.listdir(root) if os.path.isfile(os.path.join(root, f)))
    if has_docker or has_k8s:
        priority = ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']
        priority.extend([f for f in os.listdir(root) if (f.endswith('.yaml') or f.endswith('.yml')) and os.path.isfile(os.path.join(root, f))])
        return "Docker / Kubernetes", priority
    return None
