#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Name    : federated_learning.py
# Time    : 3/5/2020 8:11 PM
# Author  : Fu Yao
# Mail    : fy38607203@163.com

import torch
import numpy as np
from torch import optim, nn


class FederatedLearning():

    def __init__(self, Model, device):
        self.Model = Model
        self.device = device

    def _fed_avg(self, clients_updates, weights):
        """Execute FedAvg algorithm"""
        with torch.no_grad():
            new_parameters = clients_updates[0].copy()
            weights = np.array(weights) / sum(weights)
            for name in new_parameters:
                new_parameters[name] = torch.zeros(new_parameters[name].shape).to(self.device)
            for idx, parameter in enumerate(clients_updates):
                for name in new_parameters:
                    new_parameters[name] += parameter[name] * weights[idx]
        return new_parameters.copy()

    def _client_update(self, model, client_dataset, lr, E):
        """Update the model on client"""
        optimizer = optim.SGD(model.parameters(), lr=lr)
        criterion = nn.MSELoss(reduction="sum")
        weight = 0
        losses = 0
        for e in range(E):
            for data, target in client_dataset:
                optimizer.zero_grad()
                output = model(data).flatten()
                loss = criterion(output, target)
                loss.backward()
                # Record loss
                losses += loss.item()
                weight += len(data)
                optimizer.step()
        try:
            return model, losses / E / weight, weight / E
        except:
            print(weight, losses, client_dataset)
            return None

    def _send(self, state):
        """Duplicate the central model to the client"""
        model = self.Model().to(self.device)
        with torch.no_grad():
            for name, parameter in model.named_parameters():
                parameter.data = state[name].clone()
        return model

    def global_update_single_process(self, clients_data, state, lr, E=1):
        """Execute one round of global update (serially)"""
        client_count = len(clients_data)
        parameters = []
        weights = []
        losses = 0

        for i in range(client_count):
            model, loss, data_count = self._client_update(self._send(state), clients_data[i], lr, E)
            parameters.append(model.state_dict().copy())
            weights.append(data_count)
            losses += loss

        return self._fed_avg(parameters, weights), losses / client_count
