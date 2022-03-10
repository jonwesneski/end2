from end2 import RunMode


__run_mode__ = RunMode.SEQUENTIAL


def test_python_gotcha_1(logger):
    def append_to(element, to=[]):
        to.append(element)
        return to

    my_list = append_to(12)
    assert my_list == [12]
    my_other_list = append_to(42)
    assert my_other_list == [12, 42]
    logger.info("Don't put a mutable object as a parameter")


def test_python_gotcha_2(logger):
    class A:
        x = 1

    class C(A):
        pass

    assert A.x == 1 and C.x == 1
    A.x = 3
    assert A.x == 3 and C.x == 3
    logger.info('Class variables are handled as dictionaries internally')
