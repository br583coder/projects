import io
import unittest
from contextlib import redirect_stdout

from plainly import Interpreter, interpret


class PlainlyInterpreterTests(unittest.TestCase):
    def run_program(self, source: str):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            interpret(source)
        return buffer.getvalue().strip().splitlines()

    def test_assignment_and_arithmetic(self):
        source = """
Set x to 5.
Change x to x plus 1.
Say x.
"""
        self.assertEqual(self.run_program(source), ["6"])

    def test_function_call(self):
        source = """
Define a function called square that takes n.
    Return n times n.
End function.

Set result to call square with arguments (5).
Say result.
"""
        self.assertEqual(self.run_program(source), ["25"])

    def test_simple_core_subset(self):
        source = """
Set x to 5.
If x is greater than 3.
    Say the text (big).
Else.
    Say the text (small).
End if.
"""
        self.assertEqual(self.run_program(source), ["big"])

    def test_lowercase_keywords(self):
        source = """
set x to 5.
if x is greater than 3.
    say the text (big).
else.
    say the text (small).
end if.
"""
        self.assertEqual(self.run_program(source), ["big"])

    def test_simple_say_syntax(self):
        source = 'say "hello, world!".'
        self.assertEqual(self.run_program(source), ["hello, world!"])

    def test_color_and_formatting_syntax(self):
        source = 'say color red "hello".'
        self.assertEqual(self.run_program(source), ["\x1b[31mhello\x1b[0m"])

        source = 'say format bold "hello".'
        self.assertEqual(self.run_program(source), ["\x1b[1mhello\x1b[0m"])

    def test_font_size_syntax(self):
        source = 'say font size 20 "hello".'
        self.assertEqual(self.run_program(source), ["hello"])

        source = 'say pixel size 18 "hello".'
        self.assertEqual(self.run_program(source), ["hello"])

    def test_open_window_syntax(self):
        interpreter = Interpreter(gui_enabled=False)
        interpreter.interpret('open window called "Test" with text "Hello" width 300 height 200 font size 18.')
        self.assertEqual(interpreter.windows, [("Test", "Hello", 300, 200, 18, None)])

    def test_open_window_buttons(self):
        interpreter = Interpreter(gui_enabled=False)
        interpreter.interpret('open window called "Confirm" with text "Proceed?" with buttons ("Yes", "No").')
        self.assertEqual(interpreter.windows, [("Confirm", "Proceed?", None, None, None, ["Yes", "No"])])

    def test_say_window_size_syntax(self):
        interpreter = Interpreter(gui_enabled=False)
        interpreter.interpret('say 1920x1080 "67".')
        self.assertEqual(interpreter.output, ["67"])
        self.assertEqual(interpreter.windows, [("Plainly", "67", 1920, 1080, None, None)])

    def test_conditional_loop_and_fizzbuzz(self):
        source = """
Define a function called fizzbuzz that takes n.
    If n modulo 15 is equal to 0.
        Return the text (FizzBuzz).
    Else if n modulo 3 is equal to 0.
        Return the text (Fizz).
    Else if n modulo 5 is equal to 0.
        Return the text (Buzz).
    Else.
        Return n.
    End if.
End function.

Set counter to 1.
Repeat while counter is less than or equal to 3.
    Set result to call fizzbuzz with arguments (counter).
    Say result.
    Change counter to counter plus 1.
End repeat.
"""
        self.assertEqual(self.run_program(source), ["1", "2", "Fizz"])

    def test_list_loop(self):
        source = """
Set fruits to the list (apple, banana, cherry).
For each fruit in fruits.
    Say fruit.
End for.
"""
        self.assertEqual(self.run_program(source), ["apple", "banana", "cherry"])


if __name__ == "__main__":
    unittest.main()
