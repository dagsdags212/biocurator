from biocurator.utils.logging import log_function_call


def test_log_function_call_preserves_name():
    @log_function_call
    def my_func():
        """My docstring."""
        return 42
    assert my_func.__name__ == "my_func"


def test_log_function_call_preserves_docstring():
    @log_function_call
    def my_func():
        """My docstring."""
        return 42
    assert my_func.__doc__ == "My docstring."


def test_log_function_call_still_calls_function():
    @log_function_call
    def add(a, b):
        return a + b
    assert add(2, 3) == 5
