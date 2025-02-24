# -*- coding:utf-8 -*-

# Copyright (C) 2020. Huawei Technologies Co., Ltd. All rights reserved.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the MIT License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# MIT License for more details.

"""Lazy import mindspore network."""

from vega.common.class_factory import ClassFactory


ClassFactory.lazy_register("vega.networks.mindspore", {
    "dnet": ["DNet"],
    "super_network": ["DartsNetwork", "CARSDartsNetwork", "GDASDartsNetwork"],
    "backbones.load_official_model": ["OffcialModelLoader"],
    "backbones.resnet_ms": ["ResNetMs"],
    "losses.mix_auxiliary_loss": ["MixAuxiliaryLoss"],
    "faster_rcnn.faster_rcnn_resnet": ["Faster_Rcnn_MD"]
})
