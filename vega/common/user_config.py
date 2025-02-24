# -*- coding:utf-8 -*-

# Copyright (C) 2020. Huawei Technologies Co., Ltd. All rights reserved.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the MIT License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# MIT License for more details.

"""Contains Default and User configuration."""
from copy import deepcopy
from .config import Config
from .utils import singleton, update_dict
from vega.common.check import valid_rule


@singleton
class UserConfig(object):
    """Load user config from user file and merge config with default config."""

    __data__ = None

    def load(self, cfg_path):
        """Load config from file and merge config dict with default config.

        :param cfg_path: user config file path
        """
        if cfg_path is None:
            raise ValueError("config path can't be None or empty")
        self.__data__ = Config(cfg_path)
        self.check_config(self.__data__)
        for pipe_name, child in self.__data__.items():
            if isinstance(child, dict):
                if pipe_name in ['pipeline', 'general']:
                    continue
                for _, step_item in child.items():
                    UserConfig().merge_reference(step_item)

    @classmethod
    def check_config(cls, config):
        """Check config."""
        check_rules_user = {"general": {"type": dict},
                            "pipeline": {"required": True, "type": list}
                            }
        valid_rule(cls, config, check_rules_user)
        for pipe_step in config["pipeline"]:
            if pipe_step not in config:
                raise Exception(
                    "{} is required in {}".format(pipe_step, cls.__name__))

    @property
    def data(self):
        """Return cfg dict."""
        return self.__data__

    @data.setter
    def data(self, value):
        if not isinstance(value, dict):
            raise ValueError('data must be type dict.')
        self.__data__ = value

    @staticmethod
    def merge_reference(child):
        """Merge config with reference the specified config with ref item."""
        if not isinstance(child, dict):
            return
        ref = child.get('ref')
        if not ref:
            return
        ref_dict = deepcopy(UserConfig().data)
        for key in ref.split('.'):
            ref_dict = ref_dict.get(key)
        not_merge_keys = ['callbacks', 'lazy_built', 'max_train_steps', 'with_train', 'with_vaild']
        for key in not_merge_keys:
            if key in ref_dict:
                ref_dict.pop(key)
        ref_dict = update_dict(child, ref_dict)
        child = update_dict(ref_dict, child)
