# coding: utf-8

"""
    almdrlib Exceptions
"""


class AlmdrlibException(Exception):
    """The base exception class for all almdrlib exceptions"""
    pass


class AlmdrlibTypeError(AlmdrlibException, TypeError):
    def __init__(self, msg):
        super().__init__(msg)


class AlmdrlibValueError(AlmdrlibException, ValueError):
    def __init__(self, msg):
        super().__init__(msg)


class AlmdrlibKeyError(AlmdrlibException, KeyError):
    def __init__(self, msg):
        super().__init__(msg)
