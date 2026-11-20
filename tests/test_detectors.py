from depicts.collectors import resolve_files, scan_project
from depicts.config import DEFAULT_EXCLUDES
from depicts.detectors import detect_stack
from depicts.detectors.docker_k8s import detect_docker, detect_kubernetes
from depicts.detectors.python import MAX_MODULES_PER_PACKAGE

MANIFEST = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\n"


def selected(root):
    """The files depicts would include for this project."""
    _, patterns = detect_stack(str(root))
    scan = scan_project(str(root), list(DEFAULT_EXCLUDES))
    return [ref.path for ref in resolve_files(root, scan.files, patterns)]


def test_generic_project(make_files):
    root = make_files({"README.md": "x", "notes.txt": ""})
    assert detect_stack(str(root))[0] == "Generic"
    assert selected(root) == ["README.md"]


def test_python_flat_layout_includes_package_modules(make_files):
    # Regression: for a flat layout (like depicts itself) no source file was included.
    root = make_files({
        "pyproject.toml": "", "README.md": "",
        "mypkg/__init__.py": "", "mypkg/cli.py": "", "mypkg/core.py": "", "mypkg/sub/__init__.py": "",
        "tests/__init__.py": "", "tests/test_x.py": "",
    })
    assert detect_stack(str(root))[0] == "Python"
    assert selected(root) == ["README.md", "mypkg/__init__.py", "mypkg/cli.py", "mypkg/core.py", "pyproject.toml"]


def test_python_src_layout(make_files):
    root = make_files({"setup.cfg": "", "src/mypkg/__init__.py": "", "src/mypkg/__main__.py": "", "src/tool.py": ""})
    assert selected(root) == ["setup.cfg", "src/mypkg/__init__.py", "src/mypkg/__main__.py", "src/tool.py"]


def test_python_large_package_only_contributes_entry_modules(make_files):
    files = {"pyproject.toml": "", "big/__init__.py": "", "big/cli.py": "", "big/models.py": ""}
    files.update({f"big/mod{i}.py": "" for i in range(MAX_MODULES_PER_PACKAGE)})
    root = make_files(files)
    assert selected(root) == ["big/__init__.py", "big/cli.py", "big/models.py", "pyproject.toml"]


def test_node_excludes_lock_files_and_nested_index(make_files):
    root = make_files({
        "package.json": "{}", "package-lock.json": "{}", "yarn.lock": "", "src/index.ts": "",
        **{f"src/components/C{i}/index.js": "" for i in range(30)},
    })
    assert detect_stack(str(root))[0] == "Node.js"
    assert selected(root) == ["package.json", "src/index.ts"]


def test_go_cmd_layout(make_files):
    root = make_files({"go.mod": "", "cmd/server/main.go": "", "cmd/cli/main.go": "", "internal/x/main.go": ""})
    assert selected(root) == ["cmd/cli/main.go", "cmd/server/main.go", "go.mod"]


def test_rust(make_files):
    root = make_files({"Cargo.toml": "", "src/main.rs": "", "src/util.rs": ""})
    assert selected(root) == ["Cargo.toml", "src/main.rs"]


def test_dockerfile_alone_is_docker_not_kubernetes(make_files):
    root = make_files({"Dockerfile": "FROM python", "Dockerfile.dev": "FROM python"})
    assert detect_stack(str(root))[0] == "Docker"
    assert selected(root) == ["Dockerfile", "Dockerfile.dev"]


def test_compose_v2_file_name(make_files):
    assert detect_docker(str(make_files({"compose.yaml": "services: {}\n"})))[0] == "Docker"


def test_yaml_named_like_k8s_resource_is_not_kubernetes(make_files):
    # Regression: Symfony's services.yml was detected as Kubernetes by file name.
    root = make_files({"services.yml": "services:\n  app: ~\n", "podman.yaml": "x: 1\n"})
    assert detect_kubernetes(str(root)) is None


def test_kubernetes_manifest_recognised_by_content(make_files):
    root = make_files({"web.yaml": MANIFEST, "other.yaml": "a: 1\n"})
    name, patterns = detect_kubernetes(str(root))
    assert name == "Kubernetes"
    assert "web.yaml" in patterns and "other.yaml" not in patterns


def test_kubernetes_directory_contents_are_included(make_files):
    root = make_files({"k8s/deploy.yaml": MANIFEST, "k8s/svc.yml": MANIFEST, "helm/app/Chart.yaml": "name: app\n"})
    assert detect_stack(str(root))[0] == "Kubernetes"
    assert selected(root) == ["helm/app/Chart.yaml", "k8s/deploy.yaml", "k8s/svc.yml"]


def test_multiple_stacks_are_combined(make_files):
    root = make_files({"pyproject.toml": "", "Dockerfile": "", "package.json": "{}"})
    assert detect_stack(str(root))[0] == "Python / Node.js / Docker"


def test_github_workflows_are_included(make_files):
    root = make_files({".github/workflows/ci.yml": "", ".github/workflows/release.yaml": "", "README.md": ""})
    assert selected(root) == [".github/workflows/ci.yml", ".github/workflows/release.yaml", "README.md"]
