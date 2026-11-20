import os

MARKERS = ('pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', 'Pipfile')
ROOT_FILES = ['main.py', 'app.py', 'wsgi.py', 'asgi.py', 'manage.py', 'src/*.py']
# Directories that may contain __init__.py but are not the project's code.
NOT_PACKAGES = {'tests', 'test', 'testing', 'docs', 'doc', 'examples', 'example', 'benchmarks', 'scripts'}
# Packages with more top-level modules than this only contribute their likely entry modules.
MAX_MODULES_PER_PACKAGE = 10
ENTRY_MODULES = {
    '__init__.py', '__main__.py', 'cli.py', 'main.py', 'app.py', 'api.py', 'core.py',
    'config.py', 'settings.py', 'models.py', 'views.py', 'urls.py',
}


def _list(path):
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []


def _package_modules(root, base):
    """Top-level modules of the packages directly under ``root/base`` (flat or src layout)."""
    found = []
    base_dir = os.path.join(root, base) if base else root
    for name in _list(base_dir):
        if name in NOT_PACKAGES or name.startswith('.'):
            continue
        pkg_dir = os.path.join(base_dir, name)
        if not os.path.isfile(os.path.join(pkg_dir, '__init__.py')):
            continue
        modules = [m for m in _list(pkg_dir) if m.endswith('.py') and os.path.isfile(os.path.join(pkg_dir, m))]
        if len(modules) > MAX_MODULES_PER_PACKAGE:
            modules = [m for m in modules if m in ENTRY_MODULES]
        prefix = f"{base}/{name}" if base else name
        found.extend(f"{prefix}/{m}" for m in modules)
    return found


def detect_python(root):
    """Detects Python projects (flat and src layouts) and returns priority files."""
    if not any(os.path.exists(os.path.join(root, m)) for m in MARKERS):
        return None
    priority = list(MARKERS) + ROOT_FILES
    priority += _package_modules(root, '')
    priority += _package_modules(root, 'src')
    return "Python", priority
