import os
import unittest

from echafauder.main import copy_dir

here = os.path.dirname(__file__)


class BasicTest(unittest.TestCase):
    def test_basic(self):
        copy_dir(
            source=os.path.join(here, '..', 'scaffolding_examples', '1'),
            dest=os.path.join(here, 'results', '1'),
            vars={
                'project_name': 'my_project',
                'version': '1.0.1'
            }
        )
