#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 1999-2020 Alibaba Group Holding Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import numpy as np
import pandas as pd

import mars.tensor as mt
import mars.dataframe as md
from mars.session import new_session
from mars.utils import lazy_import

ray_installed = lazy_import('ray', globals=globals()) is not None


@unittest.skipIf(not ray_installed, 'ray not installed')
class Test(unittest.TestCase):
    def testRayTask(self):
        with new_session(backend='ray').as_default():
            # test tensor task
            raw = np.random.rand(100, 100)
            t = mt.tensor(raw, chunk_size=30).sum().to_numpy()
            self.assertAlmostEqual(t, raw.sum())

            # test DataFrame task
            raw = pd.DataFrame(np.random.random((20, 4)), columns=list('abcd'))
            df = md.DataFrame(raw, chunk_size=5)
            r = df.describe().to_pandas()
            pd.testing.assert_frame_equal(r, raw.describe())

            # test update shape
            raw = np.random.rand(100)
            t = mt.tensor(raw, chunk_size=30)
            selected = t[t > 0.5].execute()
            r = selected.to_numpy()
            expected = raw[raw > 0.5]
            np.testing.assert_array_equal(r, expected)

    def testOperandSerialization(self):
        from mars.ray.core import operand_serializer, operand_deserializer

        df = md.DataFrame(mt.random.rand(10, 3), columns=list('abc'))
        r = df.sort_values(by='a')
        op = r.op

        new_op = operand_deserializer(operand_serializer(op))

        self.assertEqual(op.by, new_op.by)
        self.assertIsInstance(new_op, type(op))
        for c1, c2 in zip(op.inputs, new_op.inputs):
            self.assertEqual(c1.key, c2.key)

        for c1, c2 in zip(op.outputs, new_op.outputs):
            self.assertEqual(c1.key, c2.key)
