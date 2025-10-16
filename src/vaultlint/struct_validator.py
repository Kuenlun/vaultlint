"""
Folder structure validator driven by a YAML specification.

Specification shape (YAML):
  allow_extra_dirs: <bool>         # global default for directories
  allow_extra_files: <bool>        # global default for files
  structure:                       # list of top-level items under the target root
    - type: dir|file
      name: <string>
      optional: <bool>             # optional presence, defaults to false
      # For directories only:
      allow_extra_dirs: <bool>     # overrides global within this directory subtree
      allow_extra_files: <bool>    # overrides global within this directory subtree
      children:                    # only for type: dir
        - ... same node structure ...

Exit codes:
  0 = validation passed
  1 = validation failed (mismatches discovered)
  2 = usage or spec error (bad YAML, unreadable path, etc.)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import yaml

# ---------- Data model ----------


@dataclass(frozen=True)
class GlobalSettings:
    allow_extra_dirs: bool = False
    allow_extra_files: bool = False


@dataclass(frozen=True)
class BaseNode:
    name: str
    optional: bool = False

    def key(self) -> str:
        return self.name


@dataclass(frozen=True)
class FileNode(BaseNode):
    kind: str = field(default="file", init=False)


@dataclass(frozen=True)
class DirNode(BaseNode):
    allow_extra_dirs: Optional[bool] = None
    allow_extra_files: Optional[bool] = None
    children: List[Union["DirNode", FileNode]] = field(default_factory=list)
    kind: str = field(default="dir", init=False)

    def effective_allow_dirs(self, globals_: GlobalSettings) -> bool:
        return (
            self.allow_extra_dirs
            if self.allow_extra_dirs is not None
            else globals_.allow_extra_dirs
        )

    def effective_allow_files(self, globals_: GlobalSettings) -> bool:
        return (
            self.allow_extra_files
            if self.allow_extra_files is not None
            else globals_.allow_extra_files
        )


# ---------- Spec parsing and validation helpers ----------


class SpecError(ValueError):
    pass


def _require_bool(
    d: Dict[str, Any], key: str, default: Optional[bool] = None
) -> Optional[bool]:
    if key not in d:
        return default
    val = d[key]
    if isinstance(val, bool):
        return val
    raise SpecError(f"Field '{key}' must be a boolean")


def _require_str(d: Dict[str, Any], key: str) -> str:
    if key not in d:
        raise SpecError(f"Missing required field '{key}'")
    val = d[key]
    if isinstance(val, str) and val != "":
        return val
    raise SpecError(f"Field '{key}' must be a non-empty string")


def _optional_bool(d: Dict[str, Any], key: str, default: bool = False) -> bool:
    val = d.get(key, default)
    if isinstance(val, bool):
        return val
    raise SpecError(f"Field '{key}' must be a boolean")


def _parse_node(obj: Dict[str, Any]) -> Union[DirNode, FileNode]:
    if not isinstance(obj, dict):
        raise SpecError("Each node must be a mapping")
    t = _require_str(obj, "type")
    name = _require_str(obj, "name")
    optional = _optional_bool(obj, "optional", False)

    if t == "file":
        if "children" in obj:
            raise SpecError(f"File '{name}' cannot have 'children'")
        if "allow_extra_dirs" in obj or "allow_extra_files" in obj:
            raise SpecError(
                f"File '{name}' cannot set 'allow_extra_dirs' or 'allow_extra_files'"
            )
        return FileNode(name=name, optional=optional)

    if t == "dir":
        allow_extra_dirs = _require_bool(obj, "allow_extra_dirs", None)
        allow_extra_files = _require_bool(obj, "allow_extra_files", None)
        children_raw = obj.get("children", [])
        if children_raw is None:
            children_raw = []
        if not isinstance(children_raw, list):
            raise SpecError(f"Dir '{name}': 'children' must be a list")
        children: List[Union[DirNode, FileNode]] = [
            _parse_node(ch) for ch in children_raw
        ]
        return DirNode(
            name=name,
            optional=optional,
            allow_extra_dirs=allow_extra_dirs,
            allow_extra_files=allow_extra_files,
            children=children,
        )

    raise SpecError(f"Unsupported node type '{t}' for '{name}'")


def parse_spec(spec_dict: Dict[str, Any]) -> Tuple[GlobalSettings, DirNode]:
    """
    Parse a YAML-loaded dict into GlobalSettings and a synthetic root DirNode.
    The synthetic root represents the target directory passed on the CLI.
    """
    if not isinstance(spec_dict, dict):
        raise SpecError("Top-level spec must be a mapping")

    globals_ = GlobalSettings(
        allow_extra_dirs=bool(spec_dict.get("allow_extra_dirs", False)),
        allow_extra_files=bool(spec_dict.get("allow_extra_files", False)),
    )

    structure = spec_dict.get("structure")
    if structure is None or not isinstance(structure, list):
        raise SpecError("Top-level 'structure' must be a list")

    children = [_parse_node(item) for item in structure]
    root = DirNode(
        name="<root>",
        optional=False,
        allow_extra_dirs=globals_.allow_extra_dirs,
        allow_extra_files=globals_.allow_extra_files,
        children=children,
    )
    return globals_, root


# ---------- Validation engine ----------


@dataclass(frozen=True)
class Issue:
    path: Path
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}  ->  {self.path}"


def _rel(base: Path, p: Path) -> Path:
    try:
        return p.relative_to(base)
    except ValueError:
        return p


def validate_tree(
    target_root: Path,
    globals_: GlobalSettings,
    root_spec: DirNode,
    collect_all: bool = True,
) -> List[Issue]:
    """
    Validate the filesystem under 'target_root' against 'root_spec'.
    Returns a list of issues. Empty list means success.
    """
    issues: List[Issue] = []

    def add_issue(p: Path, code: str, msg: str) -> None:
        issues.append(Issue(path=_rel(target_root, p), code=code, message=msg))

    def validate_dir(node: DirNode, path: Path, inherited: GlobalSettings) -> None:
        allow_dirs = node.effective_allow_dirs(inherited)
        allow_files = node.effective_allow_files(inherited)

        if not path.exists():
            if node.optional:
                return
            add_issue(
                path, "MISSING_DIR", f"Required directory '{node.name}' does not exist"
            )
            if not collect_all:
                return
            return

        if not path.is_dir():
            add_issue(
                path,
                "TYPE_MISMATCH",
                f"Expected directory but found a non-directory: '{path.name}'",
            )
            if not collect_all:
                return
            # If it is not a dir, we cannot descend
            return

        # Map expected children by name
        expected_by_name: Dict[str, Union[DirNode, FileNode]] = {
            ch.key(): ch for ch in node.children
        }

        # Validate expected items
        for child in node.children:
            child_path = path / child.name
            if isinstance(child, FileNode):
                if not child_path.exists():
                    if child.optional:
                        continue
                    add_issue(
                        child_path,
                        "MISSING_FILE",
                        f"Required file '{child.name}' does not exist",
                    )
                    if not collect_all:
                        return
                    continue
                if child_path.is_dir():
                    add_issue(
                        child_path,
                        "TYPE_MISMATCH",
                        f"Expected file but found a directory named '{child.name}'",
                    )
                    if not collect_all:
                        return
                # If it is a file (or symlink to file), it is fine
            elif isinstance(child, DirNode):
                validate_dir(
                    child, child_path, inherited=GlobalSettings(allow_dirs, allow_files)
                )
            else:
                add_issue(
                    child_path, "SPEC_ERROR", f"Unknown node kind under '{path.name}'"
                )
                if not collect_all:
                    return

        # Check for unexpected entries when extras are not allowed
        try:
            entries = list(path.iterdir())
        except PermissionError:
            add_issue(path, "PERMISSION", "Cannot list directory due to permissions")
            if not collect_all:
                return
            entries = []

        for entry in entries:
            name = entry.name
            if name in expected_by_name:
                continue
            if entry.is_dir():
                if not allow_dirs:
                    add_issue(
                        entry,
                        "UNEXPECTED_DIR",
                        f"Unexpected directory '{name}' is not allowed here",
                    )
                    if not collect_all:
                        return
            else:
                if not allow_files:
                    add_issue(
                        entry,
                        "UNEXPECTED_FILE",
                        f"Unexpected file '{name}' is not allowed here",
                    )
                    if not collect_all:
                        return

    # Kick off at the synthetic root, which corresponds to target_root
    validate_dir(root_spec, target_root, inherited=globals_)
    return issues


def load_spec(path: Path) -> Dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise SpecError(f"Spec file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SpecError(f"Invalid YAML: {exc}") from exc
    if data is None:
        raise SpecError("Spec file is empty")
    return data
