import os


def detect_go(root):
    if os.path.exists(os.path.join(root, 'go.mod')):
        return "Go", ['go.mod', 'main.go', 'cmd/main.go', 'cmd/*/main.go']
    return None
