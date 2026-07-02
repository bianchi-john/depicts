import os

def detect_docker_k8s(root):
    """Detects Docker/Kubernetes stacks. Returns None if the directory is inaccessible."""
    try:
        root_files = [f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]
        root_dirs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
    except PermissionError:
        return None

    has_docker = any(f in root_files for f in ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'])
    
    k8s_patterns = ['deployment', 'service', 'ingress', 'configmap', 'statefulset', 'daemonset', 'cronjob', 'pod', 'namespace', 'pvc', 'hpa']
    has_k8s = any(d in root_dirs for d in ['k8s', 'kubernetes', 'helm'])
    
    k8s_files = []
    if not has_k8s:
        for f in root_files:
            if f.endswith('.yaml') or f.endswith('.yml'):
                if any(p in f.lower() for p in k8s_patterns):
                    has_k8s = True
                    k8s_files.append(f)

    if has_docker or has_k8s:
        priority = ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']
        if 'k8s' in root_dirs or 'kubernetes' in root_dirs or 'helm' in root_dirs:
            pass # We don't recursively add files from dirs yet, handled by force_includes or manual config if needed
        priority.extend(k8s_files)
        return "Docker / Kubernetes", priority
    return None
