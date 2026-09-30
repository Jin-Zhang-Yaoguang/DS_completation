"""将四个自有纯模块静态内联为互不污染的名称空间；不读取父策略。"""
import ast
import hashlib
from pathlib import Path

MODULES = ('calendar_compiler', 'scheduler', 'checker', 'route_admission')


def prefix(module, name):
    return '_r10_' + module + '_' + name


def top_bindings(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    raise ValueError('Only simple top-level bindings are supported')
                names.add(target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == '__future__':
                continue
            for item in node.names:
                if item.name == '*' or (isinstance(node, ast.Import) and '.' in item.name and not item.asname):
                    raise ValueError('Ambiguous import binding')
                names.add(item.asname or item.name)
        elif not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            raise ValueError('Unexpected top-level executable statement: ' + type(node).__name__)
    return names


class Isolate(ast.NodeTransformer):
    def __init__(self, mapping):
        self.mapping = mapping

    def visit_Name(self, node):
        return ast.copy_location(ast.Name(id=self.mapping.get(node.id, node.id), ctx=node.ctx), node)

    def visit_FunctionDef(self, node):
        node.name = self.mapping.get(node.name, node.name)
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        node.name = self.mapping.get(node.name, node.name)
        return self.generic_visit(node)

    def visit_Import(self, node):
        for item in node.names:
            item.asname = self.mapping.get(item.asname or item.name, item.asname or item.name)
        return node

    def visit_ImportFrom(self, node):
        if node.module in MODULES or node.module == '__future__':
            return None
        for item in node.names:
            item.asname = self.mapping.get(item.asname or item.name, item.asname or item.name)
        return node

    def visit_Global(self, node):
        node.names = [self.mapping.get(name, name) for name in node.names]
        return node


def render(directory=None):
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parent
    pieces, metadata = [], {}
    raw = {name: (directory / (name + '.py')).read_text() for name in MODULES}
    trees = {name: ast.parse(source) for name, source in raw.items()}
    bindings = {name: top_bindings(tree) for name, tree in trees.items()}
    for module, tree in trees.items():
        mapping = {name: prefix(module, name) for name in bindings[module]}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in MODULES:
                for item in node.names:
                    if item.name not in bindings[node.module]:
                        raise ValueError('Unresolved internal import')
                    mapping[item.asname or item.name] = prefix(node.module, item.name)
        # This bounded inliner rejects lexical ambiguity instead of guessing.
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.Lambda)):
                args = node.args
                arguments = args.posonlyargs + args.args + args.kwonlyargs
                arguments += [a for a in (args.vararg, args.kwarg) if a is not None]
                if any(arg.arg in mapping for arg in arguments):
                    raise ValueError('Parameter shadows module binding')
            if isinstance(node, (ast.Nonlocal, ast.AsyncFunctionDef)):
                raise ValueError('Unsupported lexical form')
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('eval', 'exec', 'globals', 'locals', '__import__'):
                raise ValueError('Dynamic name resolution is not supported')
        isolated = Isolate(mapping).visit(tree)
        ast.fix_missing_locations(isolated)
        code = ast.unparse(isolated) + '\n'
        compile(code, 'isolated_' + module, 'exec')
        pieces.append('# Static module: ' + module + '\n' + code)
        metadata[module] = {'source_sha256': hashlib.sha256(raw[module].encode()).hexdigest(),
                            'isolated_sha256': hashlib.sha256(code.encode()).hexdigest(),
                            'bindings': mapping}
    source = '\n'.join(pieces)
    return source, {'modules': metadata, 'combined_sha256': hashlib.sha256(source.encode()).hexdigest(),
                    'contains_parent_strategy': False, 'strategy_calls': 0}


if __name__ == '__main__':
    import json
    _, metadata = render()
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
