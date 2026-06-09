"""
Registry of all stack detectors.
"""
from .python import detect_python
from .node import detect_node
from .rust import detect_rust
from .go import detect_go
from .docker_k8s import detect_docker_k8s

DETECTORS = [
    detect_python,
    detect_node,
    detect_rust,
    detect_go,
    detect_docker_k8s
]

def detect_stack(root):
    """
    Runs all detectors and returns the aggregated stack name and priority files.
    """
    stacks = []
    priority_files = set(['README.md', 'README.rst', '.github/workflows/*.yml'])
    
    for detector in DETECTORS:
        result = detector(root)
        if result:
            name, files = result
            stacks.append(name)
            priority_files.update(files)
            
    if not stacks:
        stacks = ["Generic"]
        
    return " / ".join(stacks), list(priority_files)
