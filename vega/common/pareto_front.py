# -*- coding: utf-8 -*-

# Copyright (C) 2020. Huawei Technologies Co., Ltd. All rights reserved.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the MIT License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# MIT License for more details.

"""Pareto front."""

import numpy as np


def get_pareto(scores, index=False, max_nums=-1, choice_column=0, choice='normal', seed=None):
    """Get pareto front."""
    # TODO Get a specified number of samples
    data = scores
    if index:
        data = scores[:, 1:]
    pareto_indexes = get_pareto_index(data)
    res = scores[pareto_indexes]
    if max_nums == -1 or len(res) <= max_nums:
        return res
    if choice == 'normal':
        return normal_selection(res, max_nums, choice_column, seed)


def get_pareto_index(scores):
    """Get pareto front."""
    _size = scores.shape[0]
    pareto_indexes = np.ones(_size, dtype=bool)
    for i in range(_size):
        for j in range(_size):
            if all(scores[j] >= scores[i]) and any(scores[j] > scores[i]):
                pareto_indexes[i] = False
                break
    return pareto_indexes


def normal_selection(outs, max_nums, choice_column=0, seed=None):
    """Select one record."""
    if seed:
        np.random.seed(seed)
    data = outs[:, choice_column].tolist()
    prob = [round(np.log(i + 1e-2), 2) for i in range(1, len(data) + 1)]
    prob_temp = prob
    for idx, out in enumerate(data):
        sorted_ind = np.argsort(out)
        for idx, ind in enumerate(sorted_ind):
            prob[ind] += prob_temp[idx]
    normalization = [float(i) / float(sum(prob)) for i in prob]
    idx = [np.random.choice(len(data), max_nums, replace=False, p=normalization)]
    return outs[idx]
