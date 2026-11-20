import os


def detect_rust(root):
    if os.path.exists(os.path.join(root, 'Cargo.toml')):
        return "Rust", ['Cargo.toml', 'src/main.rs', 'src/lib.rs', 'src/bin/*.rs']
    return None
