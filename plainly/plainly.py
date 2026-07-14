from __future__ import annotations

"""A small Plainly interpreter for a beginner-friendly core subset of Python.

Supported features include variables, numbers, text, arithmetic, comparisons,
conditionals, while loops, and simple functions written in plain English.
"""

import re
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

try:
    import tkinter as tk
except ImportError:
    tk = None


class PlainlyError(Exception):
    pass


class Environment:
    def __init__(self, parent: Optional["Environment"] = None):
        self.parent = parent
        self.values: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise PlainlyError(f"Undefined variable: {name}")

    def set(self, name: str, value: Any) -> None:
        self.values[name] = value


@dataclass
class AssignmentNode:
    name: str
    expression: str


@dataclass
class ChangeNode:
    name: str
    expression: str


@dataclass
class SayNode:
    expression: str
    color: Optional[str] = None
    style: Optional[str] = None
    font_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class ReturnNode:
    expression: str


@dataclass
class OpenWindowNode:
    title_expression: str
    message_expression: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    font_size: Optional[int] = None
    buttons: Optional[List[str]] = None


@dataclass
class IfNode:
    branches: List[Tuple[str, List[Any]]]
    else_body: List[Any] = field(default_factory=list)


@dataclass
class RepeatNode:
    kind: str
    expression: Optional[str]
    body: List[Any]


@dataclass
class ForEachNode:
    variable: str
    iterable_expression: str
    body: List[Any]


@dataclass
class FunctionNode:
    name: str
    parameters: List[str]
    body: List[Any]


class Parser:
    def __init__(self, statements: List[str]):
        self.statements = statements
        self.index = 0

    def peek(self) -> Optional[str]:
        if self.index >= len(self.statements):
            return None
        return self.statements[self.index]

    def advance(self) -> str:
        statement = self.peek()
        if statement is None:
            raise PlainlyError("Unexpected end of program")
        self.index += 1
        return statement

    def parse(self) -> List[Any]:
        body: List[Any] = []
        while self.peek() is not None:
            statement = self.peek()
            if statement in {"End function", "End if", "End repeat", "End for"}:
                break
            body.append(self.parse_statement())
        return body

    def parse_statement(self) -> Any:
        statement = self.advance()
        lowered = statement.lower()
        if lowered.startswith("set "):
            match = re.match(r"^set (.+) to (.+)$", statement, re.IGNORECASE)
            if not match:
                raise PlainlyError(f"Unsupported assignment: {statement}")
            return AssignmentNode(match.group(1).strip(), match.group(2).strip())

        if lowered.startswith("change "):
            match = re.match(r"^change (.+) to (.+)$", statement, re.IGNORECASE)
            if not match:
                raise PlainlyError(f"Unsupported change statement: {statement}")
            return ChangeNode(match.group(1).strip(), match.group(2).strip())

        if lowered.startswith("say "):
            return self.parse_say_statement(statement)

        if lowered.startswith("open window "):
            return self.parse_window_statement(statement)

        if lowered.startswith("return "):
            return ReturnNode(statement[7:].strip())

        if lowered.startswith("if "):
            return self.parse_if_statement(statement)

        if lowered.startswith("repeat "):
            return self.parse_repeat_statement(statement)

        if lowered.startswith("for each "):
            return self.parse_for_each(statement)

        if lowered.startswith("define a function called "):
            return self.parse_function(statement)

        if lowered.startswith("add "):
            return self._list_mutation_statement("add", statement)

        if lowered.startswith("remove "):
            return self._list_mutation_statement("remove", statement)

        if lowered.startswith("get item "):
            return self._get_item_statement(statement)

        if lowered.startswith("ask the user for "):
            return self._ask_statement(statement)

        if lowered.startswith("note "):
            return None

        raise PlainlyError(f"Unsupported statement: {statement}")

    def parse_say_statement(self, statement: str) -> SayNode:
        payload = statement[4:].strip()
        color: Optional[str] = None
        style: Optional[str] = None
        font_size: Optional[int] = None
        rest = payload

        while rest.lower().startswith("color "):
            parts = rest.split(None, 2)
            if len(parts) < 3:
                raise PlainlyError(f"Unsupported color statement: {statement}")
            color = parts[1].lower()
            rest = parts[2].strip()

        while rest.lower().startswith("format "):
            parts = rest.split(None, 2)
            if len(parts) < 3:
                raise PlainlyError(f"Unsupported format statement: {statement}")
            style = parts[1].lower()
            rest = parts[2].strip()

        while rest.lower().startswith("font size ") or rest.lower().startswith("pixel size "):
            if rest.lower().startswith("font size "):
                parts = rest.split(None, 3)
                if len(parts) < 3:
                    raise PlainlyError(f"Unsupported font size statement: {statement}")
                font_size = int(parts[2])
                rest = parts[3].strip() if len(parts) > 3 else ""
            else:
                parts = rest.split(None, 3)
                if len(parts) < 3:
                    raise PlainlyError(f"Unsupported pixel size statement: {statement}")
                font_size = int(parts[2])
                rest = parts[3].strip() if len(parts) > 3 else ""

        size_match = re.match(r"^(\d+)x(\d+)\s+(.*)$", rest)
        width: Optional[int] = None
        height: Optional[int] = None
        if size_match:
            width = int(size_match.group(1))
            height = int(size_match.group(2))
            rest = size_match.group(3).strip()

        if rest.startswith('"') and rest.endswith('"'):
            expression = f'the text ({rest[1:-1]})'
        else:
            expression = rest

        return SayNode(expression=expression, color=color, style=style, font_size=font_size, width=width, height=height)

    def parse_window_statement(self, statement: str) -> OpenWindowNode:
        rest = statement[len("open window "):].strip()
        if not rest.lower().startswith("called "):
            raise PlainlyError(f"Unsupported open window statement: {statement}")
        rest = rest[7:].strip()

        title, rest = self._parse_quoted_string(rest)
        if title is None:
            raise PlainlyError(f"Window title must be quoted: {statement}")

        message: Optional[str] = None
        width: Optional[int] = None
        height: Optional[int] = None
        font_size: Optional[int] = None
        buttons: Optional[List[str]] = None

        while rest:
            lowered = rest.lower()
            if lowered.startswith("with text "):
                rest = rest[10:].strip()
                message, rest = self._parse_quoted_string(rest)
                if message is None:
                    raise PlainlyError(f"Window message must be quoted: {statement}")
                rest = rest.strip()
            elif lowered.startswith("with button "):
                rest = rest[12:].strip()
                button, rest = self._parse_quoted_string(rest)
                if button is None:
                    raise PlainlyError(f"Window button must be quoted: {statement}")
                buttons = [button]
                rest = rest.strip()
            elif lowered.startswith("with buttons "):
                rest = rest[13:].strip()
                if not rest.startswith("(") or ")" not in rest:
                    raise PlainlyError(f"Window buttons must be a parenthesized list: {statement}")
                end = rest.find(")")
                list_content = rest[1:end].strip()
                buttons = [item.strip().strip('"') for item in list_content.split(",") if item.strip()]
                rest = rest[end + 1 :].strip()
            elif lowered.startswith("width "):
                parts = rest.split(None, 2)
                width = int(parts[1])
                rest = parts[2].strip() if len(parts) > 2 else ""
            elif lowered.startswith("height "):
                parts = rest.split(None, 2)
                height = int(parts[1])
                rest = parts[2].strip() if len(parts) > 2 else ""
            elif lowered.startswith("font size "):
                parts = rest.split(None, 3)
                font_size = int(parts[2])
                rest = parts[3].strip() if len(parts) > 3 else ""
            else:
                raise PlainlyError(f"Unsupported open window option: {rest}")

        return OpenWindowNode(
            title_expression=f'the text ({title})',
            message_expression=f'the text ({message})' if message is not None else None,
            width=width,
            height=height,
            font_size=font_size,
            buttons=buttons,
        )

    def _parse_quoted_string(self, text: str) -> tuple[Optional[str], str]:
        if not text.startswith('"'):
            return None, text
        end = text.find('"', 1)
        if end == -1:
            return None, text
        return text[1:end], text[end + 1:].strip()

    def parse_if_statement(self, statement: str) -> IfNode:
        condition = statement[len("If "):].strip() if statement.lower().startswith("if ") else statement.strip()
        body = self.parse_block({"Else if", "Else", "End if", "end if"})
        branches = [(condition, body)]

        while self.peek() is not None and self.peek().lower().startswith("else if "):
            else_if_statement = self.advance()
            branch_condition = else_if_statement[len("Else if "):].strip() if else_if_statement.lower().startswith("else if ") else else_if_statement.strip()
            branch_body = self.parse_block({"Else if", "Else", "End if", "end if"})
            branches.append((branch_condition, branch_body))

        else_body: List[Any] = []
        if self.peek() is not None and self.peek().lower() == "else":
            self.advance()
            else_body = self.parse_block({"End if", "end if"})

        if self.peek() is not None and self.peek().lower() == "end if":
            self.advance()
        else:
            raise PlainlyError("Missing End if")

        return IfNode(branches=branches, else_body=else_body)

    def parse_repeat_statement(self, statement: str) -> RepeatNode:
        lowered = statement.lower()
        if lowered.startswith("repeat while "):
            expression = statement[len("Repeat while "):].strip() if statement.lower().startswith("repeat while ") else statement.strip()
            body = self.parse_block({"End repeat", "end repeat"})
            if self.peek() is not None and self.peek().lower() == "end repeat":
                self.advance()
            else:
                raise PlainlyError("Missing End repeat")
            return RepeatNode(kind="while", expression=expression, body=body)

        match = re.match(r"^repeat (\d+) times$", statement, re.IGNORECASE)
        if match:
            body = self.parse_block({"End repeat", "end repeat"})
            if self.peek() is not None and self.peek().lower() == "end repeat":
                self.advance()
            else:
                raise PlainlyError("Missing End repeat")
            return RepeatNode(kind="count", expression=match.group(1), body=body)

        raise PlainlyError(f"Unsupported repeat statement: {statement}")

    def parse_for_each(self, statement: str) -> ForEachNode:
        match = re.match(r"^for each (.+) in (.+)$", statement, re.IGNORECASE)
        if not match:
            raise PlainlyError(f"Unsupported for each statement: {statement}")
        body = self.parse_block({"End for", "end for"})
        if self.peek() is not None and self.peek().lower() == "end for":
            self.advance()
        else:
            raise PlainlyError("Missing End for")
        return ForEachNode(variable=match.group(1).strip(), iterable_expression=match.group(2).strip(), body=body)

    def parse_function(self, statement: str) -> FunctionNode:
        match = re.match(r"^define a function called (.+) that takes (.+)$", statement, re.IGNORECASE)
        if not match:
            raise PlainlyError(f"Unsupported function definition: {statement}")
        name = match.group(1).strip()
        parameters = [param.strip() for param in match.group(2).split(",") if param.strip()]
        body = self.parse_block({"End function", "end function"})
        if self.peek() is not None and self.peek().lower() == "end function":
            self.advance()
        else:
            raise PlainlyError("Missing End function")
        return FunctionNode(name=name, parameters=parameters, body=body)

    def parse_block(self, end_keywords: set[str]) -> List[Any]:
        body: List[Any] = []
        end_keywords_lower = {keyword.lower() for keyword in end_keywords}
        while self.peek() is not None:
            statement = self.peek()
            if statement is None:
                break
            lowered = statement.lower()
            if lowered in end_keywords_lower or lowered == "else" or lowered == "else if" or lowered.startswith("else if "):
                break
            body.append(self.parse_statement())
        return body

    def _list_mutation_statement(self, action: str, statement: str) -> Any:
        match = re.match(rf"^{action} (.+) to (.+)$", statement, re.IGNORECASE)
        if not match:
            raise PlainlyError(f"Unsupported list mutation statement: {statement}")
        return (action, match.group(1).strip(), match.group(2).strip())

    def _get_item_statement(self, statement: str) -> Any:
        match = re.match(r"^Get item (.+) from (.+)$", statement)
        if not match:
            raise PlainlyError(f"Unsupported get item statement: {statement}")
        return ("get_item", match.group(1).strip(), match.group(2).strip())

    def _ask_statement(self, statement: str) -> Any:
        match = re.match(r"^Ask the user for (.+) and set it to (.+)$", statement)
        if not match:
            raise PlainlyError(f"Unsupported ask statement: {statement}")
        return ("ask", match.group(1).strip(), match.group(2).strip())


class Interpreter:
    def __init__(self, input_fn: Optional[Callable[[str], str]] = None, gui_enabled: bool = False):
        self.input_fn = input_fn or input
        self.environment = Environment()
        self.functions: dict[str, FunctionNode] = {}
        self.output: List[str] = []
        self.windows: List[Tuple[str, str]] = []
        self.gui_enabled = gui_enabled

    def interpret(self, source: str) -> List[str]:
        statements = split_statements(source)
        parser = Parser(statements)
        program = parser.parse()
        self.execute_statements(program)
        return self.output

    def execute_statements(self, statements: List[Any]) -> None:
        for statement in statements:
            if statement is None:
                continue
            self.execute_statement(statement)

    def execute_statement(self, statement: Any) -> None:
        if isinstance(statement, AssignmentNode):
            value = self.evaluate_expression(statement.expression)
            self.environment.set(statement.name, value)
            return

        if isinstance(statement, ChangeNode):
            value = self.evaluate_expression(statement.expression)
            self.environment.set(statement.name, value)
            return

        if isinstance(statement, SayNode):
            value = self.evaluate_expression(statement.expression)
            text = self.format_value(value)
            if statement.color:
                text = self.apply_color(text, statement.color)
            if statement.style:
                text = self.apply_style(text, statement.style)
            print(text)
            self.output.append(text)
            if statement.width is not None and statement.height is not None:
                title = "Plainly"
                self.windows.append((title, text, statement.width, statement.height, statement.font_size, None))
                if self.gui_enabled:
                    self._open_window(title, text, statement.width, statement.height, statement.font_size, None)
            return

        if isinstance(statement, OpenWindowNode):
            title = self.evaluate_expression(statement.title_expression)
            message = self.evaluate_expression(statement.message_expression) if statement.message_expression else ""
            self.windows.append((title, message, statement.width, statement.height, statement.font_size, statement.buttons))
            if self.gui_enabled:
                self._open_window(title, message, statement.width, statement.height, statement.font_size, statement.buttons)
            return

        if isinstance(statement, ReturnNode):
            raise ReturnSignal(self.evaluate_expression(statement.expression))

        if isinstance(statement, IfNode):
            for condition, body in statement.branches:
                if self.is_truthy(self.evaluate_expression(condition)):
                    self.execute_statements(body)
                    return
            self.execute_statements(statement.else_body)
            return

        if isinstance(statement, RepeatNode):
            if statement.kind == "count":
                count = int(self.evaluate_expression(statement.expression or "0"))
                for _ in range(count):
                    self.execute_statements(statement.body)
            else:
                while self.is_truthy(self.evaluate_expression(statement.expression or "false")):
                    self.execute_statements(statement.body)
            return

        if isinstance(statement, ForEachNode):
            iterable = self.evaluate_expression(statement.iterable_expression)
            for item in iterable:
                local = Environment(self.environment)
                local.set(statement.variable, item)
                previous = self.environment
                self.environment = local
                try:
                    self.execute_statements(statement.body)
                finally:
                    self.environment = previous
            return

        if isinstance(statement, FunctionNode):
            self.functions[statement.name] = statement
            return

        if isinstance(statement, tuple) and statement[0] == "add":
            target_name = statement[1]
            value = self.evaluate_expression(statement[2])
            target = self.environment.get(target_name)
            target.append(value)
            self.environment.set(target_name, target)
            return

        if isinstance(statement, tuple) and statement[0] == "remove":
            target_name = statement[1]
            value = self.evaluate_expression(statement[2])
            target = self.environment.get(target_name)
            if value in target:
                target.remove(value)
            self.environment.set(target_name, target)
            return

        if isinstance(statement, tuple) and statement[0] == "get_item":
            index = int(self.evaluate_expression(statement[1]))
            target = self.environment.get(statement[2])
            value = target[index - 1]
            self.environment.set(statement[1], value)
            return

        if isinstance(statement, tuple) and statement[0] == "ask":
            prompt = self.evaluate_expression(statement[1])
            response = self.input_fn(prompt)
            self.environment.set(statement[2], response)
            return

        if isinstance(statement, tuple) and statement[0] == "call":
            self._call_function(statement[1], statement[2])
            return

        raise PlainlyError(f"Unsupported node: {statement}")

    def evaluate_expression(self, expression: str) -> Any:
        expr = expression.strip()
        if expr == "":
            return None

        lowered = expr.lower()
        if lowered in {"true", "false", "nothing"}:
            return {"true": True, "false": False, "nothing": None}[lowered]

        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]

        if lowered.startswith("the text (") and expr.endswith(")"):
            return expr[len("the text (") : -1]

        if lowered.startswith("the list (") and expr.endswith(")"):
            inner = expr[len("the list (") : -1].strip()
            if inner == "":
                return []
            items = split_top_level(inner)
            return [self.evaluate_expression(item.strip()) for item in items]

        if lowered.startswith("the length of "):
            return len(self.evaluate_expression(expr[len("the length of "):]))

        if lowered.startswith("call "):
            return self._call_function_expression(expr)

        if lowered.startswith("not "):
            return not self.is_truthy(self.evaluate_expression(expr[4:].strip()))

        if lowered.startswith("negative "):
            return -self._coerce_number(self.evaluate_expression(expr[len("negative "):]))

        if " combined with " in lowered:
            left, right = split_operator(expr, " combined with ")
            return str(self.evaluate_expression(left)) + str(self.evaluate_expression(right))

        for operator, evaluator in [
            (" is greater than or equal to ", lambda left, right: left >= right),
            (" is less than or equal to ", lambda left, right: left <= right),
            (" is greater than ", lambda left, right: left > right),
            (" is less than ", lambda left, right: left < right),
            (" is equal to ", lambda left, right: left == right),
            (" is not equal to ", lambda left, right: left != right),
        ]:
            if operator in lowered:
                left, right = split_operator(expr, operator)
                return evaluator(self.evaluate_expression(left), self.evaluate_expression(right))

        for operator, evaluator in [
            (" and ", lambda left, right: self.is_truthy(left) and self.is_truthy(right)),
            (" or ", lambda left, right: self.is_truthy(left) or self.is_truthy(right)),
            (" plus ", lambda left, right: left + right),
            (" minus ", lambda left, right: left - right),
            (" times ", lambda left, right: left * right),
            (" divided by ", lambda left, right: left / right),
            (" modulo ", lambda left, right: left % right),
        ]:
            if operator in lowered:
                left, right = split_operator(expr, operator)
                return evaluator(self.evaluate_expression(left), self.evaluate_expression(right))

        if re.fullmatch(r"-?\d+", expr):
            return int(expr)

        if re.fullmatch(r"-?\d+ point \d+", expr, re.IGNORECASE):
            return self._parse_decimal(expr)

        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_ ]*", expr):
            try:
                return self.environment.get(expr)
            except PlainlyError:
                return expr

        raise PlainlyError(f"Unable to evaluate expression: {expression}")

    def _call_function_expression(self, expression: str) -> Any:
        match = re.match(r"^call ([A-Za-z_][A-Za-z0-9_]*) with arguments \((.*)\)$", expression, re.IGNORECASE)
        if not match:
            raise PlainlyError(f"Unsupported function call: {expression}")
        name = match.group(1)
        args_text = match.group(2).strip()
        arguments = []
        if args_text:
            arguments = [self.evaluate_expression(item.strip()) for item in split_top_level(args_text)]
        function = self.functions.get(name)
        if function is None:
            raise PlainlyError(f"Undefined function: {name}")
        return self._call_function(function, arguments)

    def _call_function(self, function: FunctionNode | str, arguments: List[Any]) -> Any:
        if isinstance(function, str):
            function = self.functions.get(function)
            if function is None:
                raise PlainlyError(f"Undefined function: {function}")

        local = Environment(self.environment)
        for parameter, argument in zip(function.parameters, arguments):
            local.set(parameter, argument)

        previous = self.environment
        self.environment = local
        try:
            for statement in function.body:
                try:
                    self.execute_statement(statement)
                except ReturnSignal as signal:
                    return signal.value
        finally:
            self.environment = previous
        return None

    def is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, list):
            return len(value) > 0
        return True

    def format_value(self, value: Any) -> str:
        if value is None:
            return "nothing"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)

    def apply_color(self, text: str, color: str) -> str:
        codes = {
            "red": "31",
            "green": "32",
            "yellow": "33",
            "blue": "34",
            "magenta": "35",
            "cyan": "36",
            "white": "37",
        }
        code = codes.get(color.lower(), "39")
        return f"\x1b[{code}m{text}\x1b[0m"

    def apply_style(self, text: str, style: str) -> str:
        codes = {
            "bold": "1",
            "underline": "4",
            "italic": "3",
            "reverse": "7",
        }
        code = codes.get(style.lower(), "0")
        return f"\x1b[{code}m{text}\x1b[0m"

    def _open_window(self, title: str, message: str, width: Optional[int], height: Optional[int], font_size: Optional[int], buttons: Optional[List[str]]) -> None:
        if tk is None:
            print(f"Window: {title} - {message} - buttons={buttons}")
            return

        def show():
            root = tk.Tk()
            root.title(str(title))
            if width is not None and height is not None:
                root.geometry(f"{width}x{height}")
            label_font = ("Arial", font_size if font_size is not None else 12)
            label = tk.Label(root, text=str(message), font=label_font, padx=20, pady=20)
            label.pack(expand=True, fill='both')

            if buttons:
                button_frame = tk.Frame(root)
                button_frame.pack(pady=10)
                for button_text in buttons:
                    def make_command(text=button_text):
                        def command():
                            root.destroy()
                        return command
                    tk.Button(button_frame, text=button_text, command=make_command()).pack(side='left', padx=5)

            root.mainloop()

        thread = threading.Thread(target=show, daemon=False)
        thread.start()
        thread.join()

    def _coerce_number(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value)
        raise PlainlyError("Expected a number")

    def _parse_decimal(self, text: str) -> float:
        parts = text.split()
        if parts[0] == "negative":
            sign = -1
            parts = parts[1:]
        else:
            sign = 1
        return sign * float(parts[0] + "." + parts[2])


class ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


def split_statements(source: str) -> List[str]:
    statements: List[str] = []
    current: List[str] = []
    depth = 0
    source = source.lstrip("\ufeff")

    for character in source:
        if character == "(":
            depth += 1
            current.append(character)
        elif character == ")":
            depth = max(0, depth - 1)
            current.append(character)
        elif character == "." and depth == 0:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(character)

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    return [statement.strip().lstrip("\ufeff") for statement in statements if statement.strip()]


def split_top_level(text: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for character in text:
        if character == "(":
            depth += 1
            current.append(character)
        elif character == ")":
            depth = max(0, depth - 1)
            current.append(character)
        elif character == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(character)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def split_operator(text: str, operator: str) -> Tuple[str, str]:
    lowered = text.lower()
    look_for = operator.lower()
    depth = 0
    for index in range(len(lowered)):
        character = lowered[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and lowered.startswith(look_for, index):
            return text[:index].strip(), text[index + len(operator):].strip()
    raise PlainlyError(f"Operator not found: {operator} in {text}")


def interpret(source: str, input_fn: Optional[Callable[[str], str]] = None) -> List[str]:
    interpreter = Interpreter(input_fn=input_fn)
    return interpreter.interpret(source)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python plainly.py <source_file>")

    with open(sys.argv[1], "r", encoding="utf-8-sig") as handle:
        interpreter = Interpreter(gui_enabled=True)
        interpreter.interpret(handle.read())
