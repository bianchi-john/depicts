import os

def detect_python(root):
    """Detects Python stacks and returns priority files."""
    if any(os.path.exists(os.path.join(root, f)) for f in ['pyproject.toml', 'setup.py', 'requirements.txt']):
        priority = ['README.md', 'README.rst', 'pyproject.toml', 'setup.py', 'requirements.txt']
        
        for app_file in ['main.py', 'app.py', 'wsgi.py', 'manage.py', 'src/main.py', 'src/app.py']:
            if os.path.exists(os.path.join(root, app_file)):
                priority.append(app_file)
        
        for search_dir in ['src', 'src/services', 'src/controllers', 'src/utils']:
            dir_path = os.path.join(root, search_dir)
            if os.path.isdir(dir_path):
                for f in os.listdir(dir_path):
                    if os.path.isfile(os.path.join(dir_path, f)) and f.endswith('.py'):
                        priority.append(os.path.join(search_dir, f).replace('\\', '/'))

        return "Python", priority
    return None
