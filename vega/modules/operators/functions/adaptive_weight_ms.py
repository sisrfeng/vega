# -*- coding: utf-8 -*-

# Copyright (C) 2020. Huawei Technologies Co., Ltd. All rights reserved.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the MIT License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# MIT License for more details.
"""Adaptive weight."""
import os
import logging
from mindspore.train.serialization import save_checkpoint, load_checkpoint
from mindspore import Tensor
import numpy as np
import uuid


def adaptive_weight(ckpt_file, ms_model):
    """Adapte the weight shape."""
    parameter_dict = load_checkpoint(ckpt_file)
    net_parameter = ms_model.parameters_and_names()
    new_ms_params_list = []
    for index, paras in enumerate(net_parameter):
        net_para_name = paras[0]
        net_para_shape = paras[1].data.shape

        if net_para_name in parameter_dict:
            init_weight = parameter_dict[net_para_name].data
            init_para_shape = init_weight.shape

            if net_para_shape != init_para_shape:
                if "conv" in net_para_name:
                    new_weight = _adaptive_conv(init_weight, net_para_shape)
                elif "batch_norm" in net_para_name:
                    new_weight = _adaptive_bn(init_weight, net_para_shape)
                else:
                    continue
                logging.debug("parameter shape not match,para name: {}, init_shape:{}, net_para_shape:{}".
                              format(net_para_name, init_para_shape, net_para_shape))
            param_dict = {}
            param_dict['name'] = net_para_name
            param_dict['data'] = init_weight if net_para_shape == init_para_shape else new_weight
            new_ms_params_list.append(param_dict)
            # parameter_dict[net_para_name].data = new_weight
    save_path = os.path.dirname(ckpt_file)
    save_file_name = os.path.join(save_path, "adaptive_" + uuid.uuid1().hex[:8] + ".ckpt")
    save_checkpoint(new_ms_params_list, save_file_name)
    if ckpt_file.startswith("torch2ms_"):
        os.remove(ckpt_file)
    return save_file_name


def _adaptive_conv(init_weight, new_shape):
    new_weight = init_weight.asnumpy()
    init_shape = init_weight.shape
    if init_shape[0] >= new_shape[0]:
        new_weight = new_weight[0:new_shape[0]]
    else:
        new_weight = np.tile(new_weight, (int(new_shape[0] / init_shape[0]), 1, 1, 1))

    if init_shape[1] >= new_shape[1]:
        new_weight = new_weight[:, 0:new_shape[1]]
    else:
        new_weight = np.tile(new_weight, (1, int(new_shape[1] / init_shape[1]), 1, 1))
    return Tensor(new_weight)


def _adaptive_bn(init_weight, new_shape):
    new_weight = init_weight.asnumpy()
    init_shape = init_weight.shape
    if init_shape[0] >= new_shape[0]:
        new_weight = new_weight[0:new_shape[0]]
    else:
        new_weight = np.tile(new_weight, int(new_shape[0] / init_shape[0]))
    return Tensor(new_weight)
