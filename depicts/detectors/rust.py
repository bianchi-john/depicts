import os

def detect_rust(root):
    if os.path.exists(os.path.join(root, 'Cargo.toml')):
        priority = ['README.md', 'Cargo.toml', 'main.rs', 'src/main.rs', 'src/lib.rs']
        return "Rust", priority
    return None
