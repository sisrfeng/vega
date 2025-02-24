# -*- coding:utf-8 -*-

# Copyright (C) 2020. Huawei Technologies Co., Ltd. All rights reserved.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the MIT License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# MIT License for more details.

"""Metric of classifier task."""
from functools import partial
from inspect import isfunction
from vega.common import Config
from vega.common import ClassFactory, ClassType
from vega.trainer.conf import MetricsConfig
from copy import deepcopy


class MetricBase(object):
    """Provide base metrics class for all custom metric to implement."""

    def __call__(self, output, target, *args, **kwargs):
        """Perform top k accuracy. called in train and valid step.

        :param output: output of classification network
        :param target: ground truth from dataset
        """
        raise NotImplementedError

    def reset(self):
        """Reset states for new evaluation after each epoch."""
        raise NotImplementedError

    @property
    def objective(self):
        """Define reward mode, default is max."""
        return 'MAX'

    def summary(self):
        """Summary all cached records, called after valid."""
        raise NotImplementedError


class Metrics(object):
    """Metrics class of all metrics defined in cfg.

    :param metric_cfg: metric part of config
    :type metric_cfg: dict or Config
    """

    config = MetricsConfig()

    def __init__(self, metric_cfg=None):
        """Init Metrics."""
        self.mdict = {}
        metric_config = self.config.to_dict()
        if not isinstance(metric_config, list):
            metric_config = [metric_config]
        for metric_item in metric_config:
            ClassFactory.get_cls(ClassType.METRIC, self.config.type)
            metric_name = metric_item.pop('type')
            metric_class = ClassFactory.get_cls(ClassType.METRIC, metric_name)
            if isfunction(metric_class):
                metric_class = partial(metric_class, **metric_item.get("params", {}))
            else:
                metric_class = metric_class(**metric_item.get("params", {}))
            self.mdict[metric_name] = metric_class
        self.mdict = Config(self.mdict)
        self.metric_results = dict()

    def __call__(self, output=None, target=None, *args, **kwargs):
        """Calculate all supported metrics by using output and target.

        :param output: predicted output by networks
        :type output: mindspore tensor
        :param target: target label data
        :type target: mindspore tensor
        :return: performance of metrics
        :rtype: list
        """
        for key in self.mdict:
            metric = self.mdict[key]
        res = metric(output, target, *args, **kwargs)
        return res

    def reset(self):
        """Reset states for new evaluation after each epoch."""
        self.metric_results = dict()

    @property
    def results(self):
        """Return metrics results."""
        return deepcopy(self.metric_results)

    @property
    def objectives(self):
        """Return objectives results."""
        return {name: self.mdict.get(name).objective for name in self.mdict}

    def update(self, metrics):
        """Update the metrics results.

        :param metrics: outside metrics
        :type metrics: dict
        """
        for key in metrics:
            if not isinstance(metrics[key], (int, float)):
                value = metrics[key].item()
            else:
                value = metrics[key]
            self.metric_results[key] = value
