import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add project root to path so we can import depicts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from depicts.config import parse_gitignore, load_config
from depicts.collectors import (
    is_excluded,
    build_tree_and_files,
    resolve_priority_files,
    read_file_content,
    matches_gitignore
)
from depicts.formatters.plain import format_plain
from depicts.formatters.markdown import format_md
from depicts.formatters.json_out import format_json
from depicts.cli import run_pipeline

class TestDepictsConfig(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_gitignore(self):
        gitignore_content = """
        # This is a comment
        node_modules/
        *.log
        /absolute_exclude
        relative/exclude/
        """
        with open(os.path.join(self.test_dir, '.gitignore'), 'w') as f:
            f.write(gitignore_content)
        
        rules = parse_gitignore(self.test_dir)
        self.assertEqual(len(rules), 4)
        # Check node_modules rule
        self.assertIn(('node_modules', True, False), rules)
        # Check *.log rule
        self.assertIn(('*.log', False, False), rules)
        # Check /absolute_exclude rule (should be anchored, leading slash removed)
        self.assertIn(('absolute_exclude', False, True), rules)
        # Check relative/exclude/
        self.assertIn(('relative/exclude', True, False), rules)

    def test_load_config_defaults(self):
        config = load_config(self.test_dir)
        self.assertTrue('.git' in config['excludes'])
        self.assertEqual(config['max_lines'], 150)
        self.assertEqual(len(config['gitignore_rules']), 0)


class TestDepictsCollectors(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_matches_gitignore(self):
        rules = [
            ('node_modules', True, False),
            ('*.log', False, False),
            ('config/secret.json', False, True),
            ('dist', True, True)
        ]
        
        # Test directory matching
        self.assertTrue(matches_gitignore('node_modules', rules, is_dir=True))
        self.assertFalse(matches_gitignore('node_modules', rules, is_dir=False)) # is_dir_only is True
        
        # Test wildcards
        self.assertTrue(matches_gitignore('error.log', rules, is_dir=False))
        self.assertTrue(matches_gitignore('src/error.log', rules, is_dir=False))
        
        # Test anchored rules
        self.assertTrue(matches_gitignore('config/secret.json', rules, is_dir=False))
        self.assertTrue(matches_gitignore('dist', rules, is_dir=True))

    def test_is_excluded(self):
        excludes = {'.git', 'custom_exclude'}
        rules = [('ignored_file.txt', False, False)]
        
        self.assertTrue(is_excluded('.git', excludes))
        self.assertTrue(is_excluded('custom_exclude', excludes))
        self.assertTrue(is_excluded('path/custom_exclude/file', excludes)) # subdirectory of custom_exclude
        self.assertTrue(is_excluded('ignored_file.txt', excludes, rules))
        self.assertFalse(is_excluded('src/main.py', excludes, rules))

    def test_build_tree_and_files(self):
        # Create directories and files
        os.makedirs(os.path.join(self.test_dir, 'src'))
        os.makedirs(os.path.join(self.test_dir, 'node_modules'))
        
        with open(os.path.join(self.test_dir, 'src', 'main.py'), 'w') as f:
            f.write("print('hello')")
        with open(os.path.join(self.test_dir, 'node_modules', 'index.js'), 'w') as f:
            f.write("console.log('hello')")
            
        excludes = {'node_modules'}
        tree, files = build_tree_and_files(self.test_dir, excludes)
        
        # Check tree contains src and src/main.py but not node_modules
        tree_str = "\n".join(tree)
        self.assertIn("src/", tree_str)
        self.assertIn("main.py", tree_str)
        self.assertNotIn("node_modules", tree_str)
        self.assertEqual(files, ['src/main.py'])

    def test_resolve_priority_files(self):
        os.makedirs(os.path.join(self.test_dir, 'src'))
        os.makedirs(os.path.join(self.test_dir, 'node_modules'))
        
        with open(os.path.join(self.test_dir, 'src', 'main.py'), 'w') as f:
            f.write("")
        with open(os.path.join(self.test_dir, 'node_modules', 'bad.py'), 'w') as f:
            f.write("")
        with open(os.path.join(self.test_dir, 'README.md'), 'w') as f:
            f.write("")
            
        excludes = {'node_modules'}
        priority = ['README.md', 'src/*.py']
        resolved = resolve_priority_files(self.test_dir, priority, [], excludes)
        
        self.assertEqual(resolved, ['README.md', 'src/main.py'])
        self.assertNotIn('node_modules/bad.py', resolved)

    def test_read_file_content_truncation_and_binary(self):
        # Test binary detection
        bin_file = os.path.join(self.test_dir, 'image.png')
        with open(bin_file, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00')
        self.assertEqual(read_file_content(self.test_dir, 'image.png', 10, False), "<binary file, skipped>")

        # Test truncation
        text_file = os.path.join(self.test_dir, 'large.txt')
        with open(text_file, 'w') as f:
            for i in range(300):
                f.write(f"line {i}\n")
                
        content = read_file_content(self.test_dir, 'large.txt', 5, False)
        self.assertIn("line 4", content)
        self.assertNotIn("line 5", content)
        self.assertIn("truncated to 5 lines", content)


class TestDepictsFormatters(unittest.TestCase):
    def test_format_plain(self):
        summary = {
            'entry_points': 'main.py',
            'source_files': '1 .py files',
            'config_files': 'setup.py',
            'output_size': '100 tokens'
        }
        tree = ['├── main.py']
        files_content = [('main.py', 'print("hello")')]
        
        out = format_plain("Python", summary, tree, files_content)
        self.assertIn("STACK: Python", out)
        self.assertIn("Output size  : 100 tokens", out)
        self.assertIn("[DIRECTORY TREE]", out)
        self.assertIn("[FILE: main.py]", out)

    def test_format_md(self):
        summary = {
            'entry_points': 'main.py',
            'source_files': '1 .py files',
            'config_files': 'setup.py',
            'output_size': '100 tokens'
        }
        tree = ['├── main.py']
        files_content = [('main.py', 'print("hello")')]
        
        out = format_md("Python", summary, tree, files_content)
        self.assertIn("# Project Summary", out)
        self.assertIn("**STACK:** Python", out)
        self.assertIn("- **Output size:** 100 tokens", out)

    def test_format_json(self):
        summary = {
            'entry_points': 'main.py',
            'source_files': '1 .py files',
            'config_files': 'setup.py'
        }
        tree = ['├── main.py']
        files_content = [('main.py', 'print("hello")')]
        
        out = format_json("Python", summary, tree, files_content)
        self.assertIn('"stack": "Python"', out)
        self.assertIn('"main.py": "print(\\"hello\\")"', out)


class TestDepictsE2E(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('depicts.cli.copy_to_clipboard')
    def test_run_pipeline(self, mock_copy):
        mock_copy.return_value = True
        
        # Create a mock Python project
        with open(os.path.join(self.test_dir, 'setup.py'), 'w') as f:
            f.write("setup()")
        with open(os.path.join(self.test_dir, 'main.py'), 'w') as f:
            f.write("print('hello')")
            
        args = MagicMock()
        args.path = self.test_dir
        args.exclude = []
        args.lines = 10
        args.file = []
        args.short = False
        args.no_content = False
        args.full = False
        args.depth = 3
        args.format = 'plain'
        args.clipboard = False
        args.output = None
        
        # Test stdout run
        with patch('sys.stdout') as mock_stdout:
            exit_code = run_pipeline(args)
            self.assertEqual(exit_code, 0)

if __name__ == '__main__':
    unittest.main()
