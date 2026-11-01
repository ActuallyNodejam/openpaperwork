"""Loader: the rule lives in the skills tree, where the pack's own check runs.

The pack check runs inside the sandbox on a real turn, where only the skills are mounted; the
library's cases load the same file from here, so there is one copy of every rule.
"""
import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

_repo = None
for _base in [_Path(__file__).resolve(), _Path.cwd().resolve()]:
    for _parent in _base.parents:
        if (_parent / "skills/_checks/academic_style.py").is_file():
            _repo = _parent
            break
    if _repo:
        break
if _repo is None:
    raise SystemExit("check: cannot find skills/_checks/academic_style.py")

_spec = _ilu.spec_from_file_location("_skill_academic_style", _repo / "skills/_checks/academic_style.py")
_mod = _ilu.module_from_spec(_spec)
_sys.modules["_skill_academic_style"] = _mod
_spec.loader.exec_module(_mod)
check = _mod.check
main = getattr(_mod, "main", None)
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})

if __name__ == "__main__":
    import json as _json

    _rid, _path = _sys.argv[1], _sys.argv[2]
    _case = {}
    if len(_sys.argv) > 3 and _sys.argv[3]:
        _case = _json.loads(Path(_sys.argv[3]).read_text())
    _ok, _why = check(_rid, _path, _case, "first")
    print(_json.dumps({"rule": _rid, "passed": _ok, "evidence": _why}))
    _sys.exit(0 if _ok else 1)
