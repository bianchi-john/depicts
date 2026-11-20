"""
Registry of all stack detectors.

A detector takes the absolute project root and returns ``(stack_name,
[patterns])`` or ``None``. Patterns are relative to the root and follow the
semantics in ``depicts.patterns``: ``README.md`` only matches the root file,
``**/README.md`` matches at any depth.
"""
from .docker_k8s import detect_docker, detect_kubernetes
from .go import detect_go
from .node import detect_node
from .python import detect_python
from .rust import detect_rust

DETECTORS = [
    detect_python,
    detect_node,
    detect_rust,
    detect_go,
    detect_docker,
    detect_kubernetes,
]

# Included for every project.
COMMON_PATTERNS = [
    'README.md', 'README.rst', 'README.txt', 'README',
    '.github/workflows/*.yml', '.github/workflows/*.yaml',
]


def detect_stack(root):
    """Runs all detectors and returns the aggregated stack name and priority patterns."""
    stacks = []
    priority = list(COMMON_PATTERNS)

    for detector in DETECTORS:
        result = detector(root)
        if result:
            name, files = result
            stacks.append(name)
            priority.extend(p for p in files if p not in priority)

    if not stacks:
        stacks = ["Generic"]

    return " / ".join(stacks), priority
