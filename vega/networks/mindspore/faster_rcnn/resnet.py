# -*- coding:utf-8 -*-

# Copyright (C) 2020. Huawei Technologies Co., Ltd. All rights reserved.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the MIT License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# MIT License for more details.
"""Resnet backbone."""

import numpy as np
import mindspore.nn as nn
from mindspore.ops import operations as P
from mindspore.common.tensor import Tensor
from mindspore.ops import functional as F


def weight_init_ones(shape):
    """Weight init."""
    return Tensor(np.full(shape, 0.01).astype(np.float32))


def _conv(in_channels, out_channels, kernel_size=3, stride=1, padding=0, pad_mode='pad'):
    """Conv2D wrapper."""
    shape = (out_channels, in_channels, kernel_size, kernel_size)
    weights = weight_init_ones(shape)
    return nn.Conv2d(in_channels, out_channels,
                     kernel_size=kernel_size, stride=stride, padding=padding,
                     pad_mode=pad_mode, weight_init=weights, has_bias=False)


def _BatchNorm2dInit(out_chls, momentum=0.1, affine=True, use_batch_statistics=True):
    """Batchnorm2D wrapper."""
    dtype = np.float32
    gamma_init = Tensor(np.array(np.ones(out_chls)).astype(dtype))
    beta_init = Tensor(np.array(np.ones(out_chls) * 0).astype(dtype))
    moving_mean_init = Tensor(np.array(np.ones(out_chls) * 0).astype(dtype))
    moving_var_init = Tensor(np.array(np.ones(out_chls)).astype(dtype))
    return nn.BatchNorm2d(out_chls, momentum=momentum, affine=affine, gamma_init=gamma_init,
                          beta_init=beta_init, moving_mean_init=moving_mean_init,
                          moving_var_init=moving_var_init, use_batch_statistics=use_batch_statistics)


class ResidualBlockUsing(nn.Cell):
    """
    ResNet V1 residual block definition.

    Args:
        in_channels (int) - Input channel.
        out_channels (int) - Output channel.
        stride (int) - Stride size for the initial convolutional layer. Default: 1.
        down_sample (bool) - If to do the downsample in block. Default: False.
        momentum (float) - Momentum for batchnorm layer. Default: 0.1.
        training (bool) - Training flag. Default: False.
        weights_updata (bool) - Weights update flag. Default: False.

    Returns:
        Tensor, output tensor.

    Examples:
        ResidualBlock(3,256,stride=2,down_sample=True)
    """

    expansion = 4

    def __init__(self,
                 in_channels,
                 out_channels,
                 stride=1,
                 down_sample=False,
                 momentum=0.1,
                 training=False,
                 weights_update=False):
        super(ResidualBlockUsing, self).__init__()

        self.affine = weights_update

        out_chls = out_channels // self.expansion
        self.conv1 = _conv(in_channels, out_chls, kernel_size=1, stride=1, padding=0)
        self.bn1 = _BatchNorm2dInit(out_chls, momentum=momentum, affine=self.affine, use_batch_statistics=training)

        self.conv2 = _conv(out_chls, out_chls, kernel_size=3, stride=stride, padding=1)
        self.bn2 = _BatchNorm2dInit(out_chls, momentum=momentum, affine=self.affine, use_batch_statistics=training)

        self.conv3 = _conv(out_chls, out_channels, kernel_size=1, stride=1, padding=0)
        self.bn3 = _BatchNorm2dInit(out_channels, momentum=momentum, affine=self.affine, use_batch_statistics=training)

        if training:
            self.bn1 = self.bn1.set_train()
            self.bn2 = self.bn2.set_train()
            self.bn3 = self.bn3.set_train()

        if not weights_update:
            self.conv1.weight.requires_grad = False
            self.conv2.weight.requires_grad = False
            self.conv3.weight.requires_grad = False

        self.relu = P.ReLU()
        self.downsample = down_sample
        if self.downsample:
            self.conv_down_sample = _conv(in_channels, out_channels, kernel_size=1, stride=stride, padding=0)
            self.bn_down_sample = _BatchNorm2dInit(out_channels, momentum=momentum, affine=self.affine,
                                                   use_batch_statistics=training)
            if training:
                self.bn_down_sample = self.bn_down_sample.set_train()
            if not weights_update:
                self.conv_down_sample.weight.requires_grad = False
        self.add = P.Add()

    def construct(self, x):
        """
        Construct the ResNet V1 residual block.

        Args:
            x: input feature data.

        Returns:
        Tensor, output tensor.
        """
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample:
            identity = self.conv_down_sample(identity)
            identity = self.bn_down_sample(identity)

        out = self.add(out, identity)
        out = self.relu(out)

        return out


class ResNetFea(nn.Cell):
    """
    ResNet architecture.

    Args:
        block (Cell): Block for network.
        layer_nums (list): Numbers of block in different layers.
        in_channels (list): Input channel in each layer.
        out_channels (list): Output channel in each layer.
        weights_update (bool): Weight update flag.
    Returns:
        Tensor, output tensor.
    """

    def __init__(self,
                 block=ResidualBlockUsing,
                 in_channels=64,
                 code='111-2111-211111-211',
                 weights_update=False):
        super(ResNetFea, self).__init__()

        bn_training = False
        self.inplanes = in_channels
        self.planes = self.inplanes
        self.conv1 = _conv(3, 64, kernel_size=7, stride=2, padding=3, pad_mode='pad')
        self.bn1 = _BatchNorm2dInit(64, affine=bn_training, use_batch_statistics=bn_training)
        self.relu = P.ReLU()
        self.maxpool = P.MaxPool(kernel_size=3, strides=2, pad_mode="SAME")
        self.weights_update = weights_update
        code = code.split('-')

        if not self.weights_update:
            self.conv1.weight.requires_grad = False
        self.channels = []
        self.channels.append(self.planes)

        self.layer1, in_channels = self._make_layer(block,
                                                    code[0],
                                                    in_channel=self.inplanes,
                                                    out_channel=self.planes,
                                                    training=bn_training,
                                                    weights_update=self.weights_update)
        out_channels = in_channels * 2
        self.channels.append(out_channels)
        self.layer2, in_channels = self._make_layer(block,
                                                    code[1],
                                                    in_channel=in_channels,
                                                    out_channel=out_channels,
                                                    training=bn_training,
                                                    weights_update=True)
        out_channels = in_channels * 2
        self.channels.append(out_channels)
        self.layer3, in_channels = self._make_layer(block,
                                                    code[2],
                                                    in_channel=in_channels,
                                                    out_channel=out_channels,
                                                    training=bn_training,
                                                    weights_update=True)
        out_channels = in_channels * 2
        self.channels.append(out_channels)
        self.layer4, in_channels = self._make_layer(block,
                                                    code[3],
                                                    in_channel=in_channels,
                                                    out_channel=out_channels,
                                                    training=bn_training,
                                                    weights_update=True)

    def _make_layer(self, block, code, in_channel, out_channel, training=False, weights_update=False):
        """Make block layer."""
        strides = list(map(int, code))
        layers = []
        down_sample = False
        if strides[0] != 1 or in_channel != out_channel:
            down_sample = True
        resblk = block(in_channel,
                       out_channel,
                       stride=strides[0],
                       down_sample=down_sample,
                       training=training,
                       weights_update=weights_update)
        layers.append(resblk)

        for stride in strides[1:]:
            resblk = block(out_channel, out_channel, stride=stride, training=training, weights_update=weights_update)
            layers.append(resblk)

        return nn.SequentialCell(layers), out_channel

    def construct(self, x):
        """
        Construct the ResNet Network.

        Args:
            x: input feature data.

        Returns:
        Tensor, output tensor.
        """
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        c1 = self.maxpool(x)

        c2 = self.layer1(c1)
        identity = c2
        if not self.weights_update:
            identity = F.stop_gradient(c2)
        c3 = self.layer2(identity)
        c4 = self.layer3(c3)
        c5 = self.layer4(c4)

        return identity, c3, c4, c5
