"""
Docker and Kubernetes detectors.

Kubernetes manifests are recognised by their content (``apiVersion:`` and
``kind:`` at the top level), not by their file name, so files such as
Symfony's ``services.yml`` are not mistaken for manifests.
"""
import os
import re

COMPOSE_FILES = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']
K8S_DIRS = ['k8s', 'kubernetes', 'manifests', 'helm', 'charts']

_API_VERSION = re.compile(r'^apiVersion:\s*\S', re.MULTILINE)
_KIND = re.compile(r'^kind:\s*\S', re.MULTILINE)


def _list(root):
    try:
        return os.listdir(root)
    except OSError:
        return None


def detect_docker(root):
    names = _list(root)
    if names is None:
        return None
    dockerfiles = [n for n in names if n == 'Dockerfile' or n.startswith('Dockerfile.') or n.endswith('.Dockerfile')]
    if not dockerfiles and not any(n in names for n in COMPOSE_FILES):
        return None
    return "Docker", ['Dockerfile', 'Dockerfile.*', '*.Dockerfile', *COMPOSE_FILES]


def _is_manifest(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            head = f.read(4096)
    except OSError:
        return False
    return bool(_API_VERSION.search(head) and _KIND.search(head))


def detect_kubernetes(root):
    names = _list(root)
    if names is None:
        return None
    manifests = sorted(
        n for n in names
        if n.endswith(('.yml', '.yaml')) and _is_manifest(os.path.join(root, n))
    )
    dirs = [d for d in K8S_DIRS if os.path.isdir(os.path.join(root, d))]
    has_chart = 'Chart.yaml' in names
    if not (manifests or dirs or has_chart):
        return None

    priority = manifests + ['Chart.yaml', 'values.yaml']
    for d in dirs:
        priority += [f'{d}/*.yaml', f'{d}/*.yml', f'{d}/*/Chart.yaml', f'{d}/*/values.yaml']
    return "Kubernetes", priority
