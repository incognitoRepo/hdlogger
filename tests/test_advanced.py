# -*- coding: utf-8 -*-
# vscode-fold=1
from .context import hdlogger

import unittest


class AdvancedTestSuite(unittest.TestCase):
  """Advanced test cases."""

  def test_thoughts(self):
    print('test_thoughts')
    self.assertIsNone(hdlogger.hmm())


if __name__ == '__main__':
    unittest.main()
