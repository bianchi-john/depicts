import os

def detect_node(root):
    if os.path.exists(os.path.join(root, 'package.json')):
        priority = ['README.md', 'package.json', 'package-lock.json', 'yarn.lock', 'index.js', 'index.ts', 'src/index.js', 'src/index.ts', 'main.js', 'main.ts']
        return "Node.js", priority
    return None
