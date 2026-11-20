import os

# Lock files (package-lock.json, yarn.lock, ...) are deliberately left out:
# they are huge and tell an AI nothing that package.json does not.
PRIORITY = [
    'package.json', 'tsconfig.json',
    'index.js', 'index.ts', 'index.mjs', 'main.js', 'main.ts', 'server.js', 'server.ts',
    'src/index.js', 'src/index.ts', 'src/index.jsx', 'src/index.tsx',
    'src/main.js', 'src/main.ts', 'src/main.jsx', 'src/main.tsx',
]


def detect_node(root):
    if os.path.exists(os.path.join(root, 'package.json')):
        return "Node.js", list(PRIORITY)
    return None
