import os

def detect_go(root):
    if os.path.exists(os.path.join(root, 'go.mod')):
        priority = ['README.md', 'go.mod', 'main.go', 'cmd/main.go']
        return "Go", priority
    return None
