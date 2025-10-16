"""Tests for structure validation functionality."""

import tempfile
from pathlib import Path
import pytest

from vaultlint.struct_validator import (
    parse_spec,
    validate_tree,
    load_spec,
    SpecError,
    GlobalSettings,
    DirNode,
    FileNode,
    Issue
)


class TestSpecParsing:
    """Test YAML specification parsing."""
    
    def test_parse_simple_spec(self):
        """Test parsing a simple specification."""
        spec_dict = {
            "allow_extra_dirs": True,
            "allow_extra_files": False,
            "structure": [
                {"type": "dir", "name": "test_dir", "optional": False},
                {"type": "file", "name": "test_file.txt", "optional": True}
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        
        assert globals_.allow_extra_dirs is True
        assert globals_.allow_extra_files is False
        assert len(root.children) == 2
        assert root.children[0].name == "test_dir"
        assert root.children[0].kind == "dir"
        assert root.children[1].name == "test_file.txt"
        assert root.children[1].kind == "file"
        assert root.children[1].optional is True

    def test_parse_nested_spec(self):
        """Test parsing a specification with nested directories."""
        spec_dict = {
            "allow_extra_dirs": False,
            "allow_extra_files": True,
            "structure": [
                {
                    "type": "dir",
                    "name": "parent",
                    "optional": False,
                    "allow_extra_dirs": True,
                    "allow_extra_files": False,
                    "children": [
                        {"type": "file", "name": "child.txt", "optional": False},
                        {"type": "dir", "name": "subdir", "optional": True}
                    ]
                }
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        parent_dir = root.children[0]
        
        assert parent_dir.allow_extra_dirs is True
        assert parent_dir.allow_extra_files is False
        assert len(parent_dir.children) == 2
        assert parent_dir.children[0].name == "child.txt"
        assert parent_dir.children[1].name == "subdir"

    def test_parse_spec_missing_structure_fails(self):
        """Test that spec without structure key fails."""
        spec_dict = {
            "allow_extra_dirs": True,
            "allow_extra_files": False
        }
        
        with pytest.raises(SpecError, match="Top-level 'structure' must be a list"):
            parse_spec(spec_dict)

    def test_parse_spec_invalid_node_type_fails(self):
        """Test that invalid node type fails."""
        spec_dict = {
            "allow_extra_dirs": True,
            "allow_extra_files": False,
            "structure": [
                {"type": "invalid", "name": "test"}
            ]
        }
        
        with pytest.raises(SpecError, match="Unsupported node type 'invalid'"):
            parse_spec(spec_dict)


class TestStructureValidation:
    """Test filesystem structure validation."""
    
    def test_validate_successful_structure(self, tmp_path):
        """Test validation of a correct structure."""
        # Create structure
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")
        
        # Define spec
        spec_dict = {
            "allow_extra_dirs": False,
            "allow_extra_files": False,
            "structure": [
                {"type": "dir", "name": "test_dir", "optional": False},
                {"type": "file", "name": "test_file.txt", "optional": False}
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 0

    def test_validate_missing_required_directory(self, tmp_path):
        """Test validation fails when required directory is missing."""
        spec_dict = {
            "allow_extra_dirs": False,
            "allow_extra_files": False,
            "structure": [
                {"type": "dir", "name": "missing_dir", "optional": False}
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 1
        assert issues[0].code == "MISSING_DIR"
        assert "missing_dir" in issues[0].message

    def test_validate_missing_optional_directory_allowed(self, tmp_path):
        """Test validation passes when optional directory is missing."""
        spec_dict = {
            "allow_extra_dirs": False,
            "allow_extra_files": False,
            "structure": [
                {"type": "dir", "name": "optional_dir", "optional": True}
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 0

    def test_validate_unexpected_directory_not_allowed(self, tmp_path):
        """Test validation fails when unexpected directory exists and not allowed."""
        # Create unexpected directory
        unexpected = tmp_path / "unexpected_dir"
        unexpected.mkdir()
        
        spec_dict = {
            "allow_extra_dirs": False,
            "allow_extra_files": False,
            "structure": []
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 1
        assert issues[0].code == "UNEXPECTED_DIR"
        assert "unexpected_dir" in issues[0].message

    def test_validate_unexpected_directory_allowed(self, tmp_path):
        """Test validation passes when unexpected directory exists and allowed."""
        # Create unexpected directory
        unexpected = tmp_path / "unexpected_dir"
        unexpected.mkdir()
        
        spec_dict = {
            "allow_extra_dirs": True,
            "allow_extra_files": False,
            "structure": []
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 0

    def test_validate_type_mismatch_file_vs_directory(self, tmp_path):
        """Test validation fails when file exists where directory expected."""
        # Create file where directory is expected
        wrong_type = tmp_path / "should_be_dir"
        wrong_type.write_text("content")
        
        spec_dict = {
            "allow_extra_dirs": False,
            "allow_extra_files": False,
            "structure": [
                {"type": "dir", "name": "should_be_dir", "optional": False}
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 1
        assert issues[0].code == "TYPE_MISMATCH"
        assert "Expected directory but found a non-directory" in issues[0].message

    def test_validate_nested_structure(self, tmp_path):
        """Test validation of nested directory structures."""
        # Create nested structure
        parent = tmp_path / "parent"
        parent.mkdir()
        child_file = parent / "child.txt"
        child_file.write_text("content")
        subdir = parent / "subdir"
        subdir.mkdir()
        
        spec_dict = {
            "allow_extra_dirs": False,
            "allow_extra_files": False,
            "structure": [
                {
                    "type": "dir",
                    "name": "parent",
                    "optional": False,
                    "allow_extra_dirs": False,
                    "allow_extra_files": False,
                    "children": [
                        {"type": "file", "name": "child.txt", "optional": False},
                        {"type": "dir", "name": "subdir", "optional": False}
                    ]
                }
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 0


class TestYAMLLoading:
    """Test YAML specification file loading."""
    
    def test_load_valid_yaml_spec(self, tmp_path):
        """Test loading a valid YAML specification file."""
        yaml_content = """
allow_extra_dirs: true
allow_extra_files: false
structure:
  - type: dir
    name: test_dir
    optional: false
  - type: file
    name: test_file.txt
    optional: true
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(yaml_content)
        
        spec_dict = load_spec(spec_file)
        
        assert spec_dict["allow_extra_dirs"] is True
        assert spec_dict["allow_extra_files"] is False
        assert len(spec_dict["structure"]) == 2

    def test_load_nonexistent_file_fails(self, tmp_path):
        """Test loading nonexistent file fails."""
        nonexistent = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(SpecError, match="Spec file not found"):
            load_spec(nonexistent)

    def test_load_invalid_yaml_fails(self, tmp_path):
        """Test loading invalid YAML fails."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [")
        
        with pytest.raises(SpecError, match="Invalid YAML"):
            load_spec(invalid_yaml)

    def test_load_empty_file_fails(self, tmp_path):
        """Test loading empty file fails."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        
        with pytest.raises(SpecError, match="Spec file is empty"):
            load_spec(empty_file)


class TestObsidianVaultValidation:
    """Test validation of typical Obsidian vault structures."""
    
    def test_minimal_obsidian_vault_passes(self, tmp_path):
        """Test that minimal Obsidian vault passes validation."""
        # Create minimal vault structure
        obsidian_dir = tmp_path / ".obsidian"
        obsidian_dir.mkdir()
        
        # Use default Obsidian spec
        spec_dict = {
            "allow_extra_dirs": True,
            "allow_extra_files": True,
            "structure": [
                {
                    "type": "dir",
                    "name": ".obsidian",
                    "optional": False,
                    "allow_extra_dirs": True,
                    "allow_extra_files": True
                }
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 0

    def test_vault_without_obsidian_dir_fails(self, tmp_path):
        """Test that vault without .obsidian directory fails validation."""
        # Create some markdown files but no .obsidian
        note = tmp_path / "note.md"
        note.write_text("# Test Note")
        
        # Use default Obsidian spec
        spec_dict = {
            "allow_extra_dirs": True,
            "allow_extra_files": True,
            "structure": [
                {
                    "type": "dir",
                    "name": ".obsidian",
                    "optional": False,
                    "allow_extra_dirs": True,
                    "allow_extra_files": True
                }
            ]
        }
        
        globals_, root = parse_spec(spec_dict)
        issues = validate_tree(tmp_path, globals_, root)
        
        assert len(issues) == 1
        assert issues[0].code == "MISSING_DIR"
        assert ".obsidian" in issues[0].message