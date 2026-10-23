"""Bounded interpreter for a documented subset of ordinary OT-2 Python.

Never eval/exec/import agent code. Only capability objects below expose SDK calls.
Annotations are ignored. Unsupported syntax fails closed, including dead branches.
"""
import ast
import operator


class ProtocolError(ValueError):
    pass


class Runtime:
    MAX_STEPS = 20000
    MAX_ITEMS = 384
    ALLOWED = (
        ast.Module, ast.ImportFrom, ast.alias, ast.FunctionDef, ast.arguments,
        ast.arg, ast.Assign, ast.Expr, ast.For, ast.If, ast.Pass, ast.Return,
        ast.Name, ast.Load, ast.Store, ast.Constant, ast.List, ast.Tuple, ast.Dict,
        ast.Subscript, ast.Slice, ast.Attribute, ast.Call, ast.keyword, ast.BinOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.UnaryOp, ast.USub, ast.UAdd,
        ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    )

    def __init__(self, robot):
        self.robot = robot
        self.env = {}
        self.steps = 0

    def tick(self):
        self.steps += 1
        if self.steps > self.MAX_STEPS:
            raise ProtocolError("Protocol exceeds interpreter step budget")

    def run(self, code):
        if len(code.encode()) > 50000:
            raise ProtocolError("Protocol exceeds 50 KB")
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if not isinstance(node, self.ALLOWED):
                raise ProtocolError(f"Unsupported Python syntax: {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id.startswith("_"):
                raise ProtocolError("Private names are unavailable")
            if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
                raise ProtocolError("Private attributes are unavailable")
            if isinstance(node, ast.Constant):
                if not isinstance(node.value, (str, int, float, bool, type(None))):
                    raise ProtocolError("Unsupported constant")
                if isinstance(node.value, str) and len(node.value) > 2000:
                    raise ProtocolError("String too long")
        run = None
        metadata = None
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                if node.level or node.module != "opentrons" or len(node.names) != 1 or node.names[0].name != "protocol_api" or node.names[0].asname:
                    raise ProtocolError("Only 'from opentrons import protocol_api' is allowed")
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "metadata":
                metadata = ast.literal_eval(node.value)
            elif isinstance(node, ast.FunctionDef) and node.name == "run" and run is None:
                run = node
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                pass
            else:
                raise ProtocolError("Top level must contain metadata and one run(protocol) function")
        if not isinstance(metadata, dict) or metadata.get("apiLevel") != self.robot.scenario["api_level"]:
            raise ProtocolError(f"metadata must set apiLevel={self.robot.scenario['api_level']!r}")
        if run is None or len(run.args.args) != 1 or run.args.posonlyargs or run.args.kwonlyargs or run.args.defaults or run.args.vararg or run.args.kwarg or run.decorator_list:
            raise ProtocolError("Expected undecorated run(protocol) with one argument")
        self.env[run.args.args[0].arg] = self.robot
        self.block(run.body)

    def bind(self, target, value):
        if isinstance(target, ast.Name):
            self.env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (list, tuple)) and len(target.elts) == len(value):
            for item, val in zip(target.elts, value):
                self.bind(item, val)
        else:
            raise ProtocolError("Only variable assignment and tuple unpacking are supported")

    def block(self, nodes):
        for node in nodes:
            self.tick()
            if isinstance(node, ast.Assign):
                value = self.expr(node.value)
                for target in node.targets:
                    self.bind(target, value)
            elif isinstance(node, ast.Expr):
                self.expr(node.value)
            elif isinstance(node, ast.For):
                values = self.expr(node.iter)
                if not isinstance(values, (list, tuple, range)) or len(values) > self.MAX_ITEMS:
                    raise ProtocolError("Loops require a bounded sequence")
                if node.orelse:
                    raise ProtocolError("for/else is unsupported")
                for value in values:
                    self.bind(node.target, value)
                    self.block(node.body)
            elif isinstance(node, ast.If):
                self.block(node.body if self.expr(node.test) else node.orelse)
            elif isinstance(node, ast.Pass):
                pass
            else:
                raise ProtocolError(f"Unsupported statement: {type(node).__name__}")

    def expr(self, node):
        self.tick()
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in self.env:
                raise ProtocolError(f"Unknown name: {node.id}")
            return self.env[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            if len(node.elts) > self.MAX_ITEMS:
                raise ProtocolError("Sequence too long")
            return [self.expr(item) for item in node.elts]
        if isinstance(node, ast.Dict):
            if len(node.keys) > self.MAX_ITEMS or any(key is None for key in node.keys):
                raise ProtocolError("Invalid dictionary")
            return {self.expr(k): self.expr(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.Subscript):
            obj, key = self.expr(node.value), self.expr(node.slice)
            from src.simulator import LabwareHandle
            if not isinstance(obj, (list, tuple, dict, str, LabwareHandle)):
                raise ProtocolError("Cannot index this object")
            return obj[key]
        if isinstance(node, ast.Slice):
            return slice(*(self.expr(v) if v else None for v in (node.lower, node.upper, node.step)))
        if isinstance(node, ast.UnaryOp):
            value = self.number(self.expr(node.operand))
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            left, right = self.number(self.expr(node.left)), self.number(self.expr(node.right))
            op = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}[type(node.op)]
            return self.number(op(left, right))
        if isinstance(node, ast.Compare):
            left = self.expr(node.left)
            for op, item in zip(node.ops, node.comparators):
                right = self.expr(item)
                compare = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}[type(op)]
                if not compare(left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Call):
            args = [self.expr(arg) for arg in node.args]
            if any(kw.arg is None for kw in node.keywords):
                raise ProtocolError("Keyword unpacking is unavailable")
            kwargs = {kw.arg: self.expr(kw.value) for kw in node.keywords}
            if isinstance(node.func, ast.Name):
                return self.builtin(node.func.id, args, kwargs)
            if isinstance(node.func, ast.Attribute):
                obj = self.expr(node.func.value)
                from src.simulator import Capability
                if not isinstance(obj, Capability) or node.func.attr not in obj.methods:
                    raise ProtocolError(f"Method unavailable: {node.func.attr}")
                return getattr(obj, node.func.attr)(*args, **kwargs)
        raise ProtocolError(f"Unsupported expression: {type(node).__name__}")

    def number(self, value):
        import math
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1000000:
            raise ProtocolError("Expected a finite number of magnitude <= 1,000,000")
        return value

    def builtin(self, name, args, kwargs):
        if kwargs:
            raise ProtocolError("Builtin keyword arguments are unavailable")
        if name == "range":
            values = range(*args)
        elif name in ("zip", "enumerate", "len"):
            if not args or not all(isinstance(arg, (list, tuple, dict, str, range, int)) for arg in args):
                raise ProtocolError("Builtin requires bounded data")
            if name == "len":
                return len(*args)
            values = list(zip(*args)) if name == "zip" else list(enumerate(*args))
        else:
            raise ProtocolError(f"Builtin unavailable: {name}")
        if len(values) > self.MAX_ITEMS:
            raise ProtocolError("Sequence exceeds 384 items")
        return values
