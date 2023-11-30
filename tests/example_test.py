def add(a, b):
    return a + b


def test_add():
    assert add(1, 2) == 3
    assert add(-5, 6) == 1
    assert add(9, -1) == 8
