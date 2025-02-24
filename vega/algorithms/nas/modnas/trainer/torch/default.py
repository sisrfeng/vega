# -*- coding:utf-8 -*-

# Copyright (C) 2020. Huawei Technologies Co., Ltd. All rights reserved.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the MIT License.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# MIT License for more details.

"""Default Trainer."""
import torch
import torch.nn as nn
from modnas import backend
from ..base import TrainerBase
from modnas.registry.trainer import register
from modnas.estim.base import EstimBase
from torch import Tensor
from torch.nn.modules.module import Module
from typing import Dict, Optional, Any
from modnas.registry import SPEC_TYPE


@register
class DefaultTrainer(TrainerBase):
    """Default Trainer class."""

    def __init__(self,
                 writer: Optional[Any] = None,
                 expman: Optional[Any] = None,
                 data_provider: Optional[SPEC_TYPE] = None,
                 optimizer: Optional[SPEC_TYPE] = None,
                 lr_scheduler: Optional[SPEC_TYPE] = None,
                 criterion: Optional[SPEC_TYPE] = None,
                 w_grad_clip: int = 0) -> None:
        super().__init__(writer)
        self.w_grad_clip = w_grad_clip
        self.expman = expman
        self.optimizer = None
        self.lr_scheduler = None
        self.data_provider = None
        self.criterion = None
        self.config = {
            'optimizer': optimizer,
            'lr_scheduler': lr_scheduler,
            'data_provider': data_provider,
            'criterion': criterion,
        }

    def init(self, model: Module, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize trainer states."""
        self.config.update(config or {})
        if self.config['optimizer']:
            self.optimizer = backend.get_optimizer(model.parameters(), self.config['optimizer'], config)
        if self.config['lr_scheduler']:
            self.lr_scheduler = backend.get_lr_scheduler(self.optimizer, self.config['lr_scheduler'], config)
        if self.config['data_provider']:
            self.data_provider = backend.get_data_provider(self.config['data_provider'])
        if self.config['criterion']:
            self.criterion = backend.get_criterion(self.config['criterion'], getattr(model, 'device_ids', None))
        self.device = self.config.get('device', backend.get_device())

    def get_num_train_batch(self, epoch: int) -> int:
        """Return number of train batches in current epoch."""
        return 0 if self.data_provider is None else self.data_provider.get_num_train_batch(epoch=epoch)

    def get_num_valid_batch(self, epoch: int) -> int:
        """Return number of validate batches in current epoch."""
        return 0 if self.data_provider is None else self.data_provider.get_num_valid_batch(epoch=epoch)

    def get_next_train_batch(self) -> Any:
        """Return the next train batch."""
        return self.proc_batch(self.data_provider.get_next_train_batch())

    def get_next_valid_batch(self) -> Any:
        """Return the next validate batch."""
        return self.proc_batch(self.data_provider.get_next_valid_batch())

    def proc_batch(self, batch: Any) -> Any:
        """Process batch."""
        return tuple(v.to(device=self.device, non_blocking=True) for v in batch)

    def state_dict(self):
        """Return current states."""
        return {
            'optimizer': self.optimizer.state_dict(),
            'lr_scheduler': self.lr_scheduler.state_dict(),
        }

    def load_state_dict(self, sd):
        """Resume states."""
        if self.optimizer is not None:
            self.optimizer.load_state_dict(sd['optimizer'])
        if self.lr_scheduler is not None:
            self.lr_scheduler.load_state_dict(sd['lr_scheduler'])

    def get_lr(self) -> float:
        """Return current learning rate."""
        if self.lr_scheduler:
            if hasattr(self.lr_scheduler, 'get_last_lr'):
                return self.lr_scheduler.get_last_lr()[0]
            return self.lr_scheduler.get_lr()[0]
        return self.optimizer.param_groups[0]['lr']

    def get_optimizer(self):
        """Return optimizer."""
        return self.optimizer

    def loss(
        self, output: Optional[Any] = None, data: Optional[Any] = None, model: Optional[Module] = None
    ) -> Optional[Tensor]:
        """Return loss."""
        return None if self.criterion is None else self.criterion(None, None, output, *data)

    def train_epoch(self, estim: EstimBase, model: Module, tot_steps: int, epoch: int, tot_epochs: int) -> None:
        """Train for one epoch."""
        self.data_provider.reset_train_iter()
        for step in range(tot_steps):
            self.train_step(estim, model, epoch, tot_epochs, step, tot_steps)

    def train_step(
        self, estim: EstimBase, model: Module, epoch: int, tot_epochs: int, step: int, tot_steps: int
    ) -> Dict[str, Any]:
        """Train for one step."""
        optimizer = self.optimizer
        lr_scheduler = self.lr_scheduler
        lr = self.get_lr()
        model.train()
        batch = self.get_next_train_batch()
        optimizer.zero_grad()
        loss = estim.loss(batch, model=model, mode='train')
        loss.backward()
        # gradient clipping
        if self.w_grad_clip > 0:
            nn.utils.clip_grad_norm_(model.parameters(), self.w_grad_clip)
        optimizer.step()
        if step == tot_steps - 1:
            lr_scheduler.step()
        return {
            'loss': loss.item(),
            'LR': lr,
            'N': len(batch[-1]),
        }

    def valid_epoch(self, estim: EstimBase, model: Module, tot_steps: int, epoch: int = 0, tot_epochs: int = 1) -> None:
        """Validate for one epoch."""
        self.data_provider.reset_valid_iter()
        if not tot_steps:
            return None
        for step in range(tot_steps):
            self.valid_step(estim, model, epoch, tot_epochs, step, tot_steps)

    def valid_step(
        self, estim: EstimBase, model: Module, epoch: int, tot_epochs: int, step: int, tot_steps: int
    ) -> Dict[str, Any]:
        """Validate for one step."""
        model.eval()
        with torch.no_grad():
            batch = self.get_next_valid_batch()
            loss = estim.loss(batch, model=model, mode='eval')
        return {
            'loss': loss.item(),
            'N': len(batch[-1]),
        }
