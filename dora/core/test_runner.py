import unittest
from types import SimpleNamespace

from django.conf import settings
from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment, teardown_test_environment


class _TestState:
    pass


class MyTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        setup_test_environment(debug=self.debug_mode)
        saved_data = SimpleNamespace()
        _TestState.saved_data = saved_data
        saved_data.sib_key = settings.SIB_API_KEY
        settings.SIB_API_KEY = None
        unittest.installHandler()

    def teardown_test_environment(self, **kwargs):
        unittest.removeHandler()
        teardown_test_environment()
        saved_data = _TestState.saved_data
        settings.SIB_API_KEY = saved_data.sib_key
        del _TestState.saved_data
