"""Check every together client call in a directory of scripts against the installed SDK.

Usage: python check_sdk_calls.py <dir>

For each script that assigns Together(...) or AsyncTogether(...) to a name, it walks
every call made through that name (client.a.b.c(...)), checks that the attribute path
exists on a real client object, and that every keyword argument is in the method
signature. It does not make network calls and does not check types or return values.
"""
import ast, inspect, sys, pathlib, together
from together import Together, AsyncTogether
roots = {"Together": Together(api_key="x"), "AsyncTogether": AsyncTogether(api_key="x")}
problems = []
stats = {"files": 0, "client_files": 0, "calls": 0}
def chain(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id); return list(reversed(parts))
    return None
for path in sorted(pathlib.Path(sys.argv[1]).rglob("*.py")):
    stats["files"] += 1
    src = path.read_text()
    try: tree = ast.parse(src)
    except SyntaxError as e: problems.append((str(path), 0, "SyntaxError", str(e))); continue
    # find client variable names: x = Together(...) / AsyncTogether(...)
    clients = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
            f = n.value.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if name in roots:
                for t in n.targets:
                    if isinstance(t, ast.Name): clients[t.id] = name
                    if isinstance(t, ast.Attribute): clients[t.attr] = name
    if not clients: continue
    stats["client_files"] += 1
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call): continue
        c = chain(n.func)
        if not c or len(c) < 2: continue
        base = c[0] if c[0] in clients else (c[1] if c[0]=="self" and len(c)>2 and c[1] in clients else None)
        if base is None: continue
        rest = c[1:] if c[0]==base else c[2:]
        stats["calls"] += 1
        obj = roots[clients[base]]; ok = True
        for i, a in enumerate(rest):
            if not hasattr(obj, a):
                problems.append((str(path), n.lineno, "missing attr", ".".join([base]+rest[:i+1]))); ok=False; break
            obj = getattr(obj, a)
        if not ok or not callable(obj): continue
        try: sig = inspect.signature(obj)
        except (TypeError, ValueError): continue
        params = sig.parameters
        if any(p.kind == p.VAR_KEYWORD for p in params.values()): continue
        for kw in n.keywords:
            if kw.arg and kw.arg not in params:
                problems.append((str(path), n.lineno, "unknown kwarg", ".".join([base]+rest)+"("+kw.arg+"=)"))
for p in problems: print(*p, sep=" | ")
print(f"together {together.__version__}: scanned {stats['files']} files, {stats['client_files']} create a client, checked {stats['calls']} client calls")
print("TOTAL", len(problems))
