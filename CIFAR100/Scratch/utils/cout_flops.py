from __future__ import print_function
import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import network


def count_model_flops(model=None, input_channels=3, input_res=32, multiply_adds=False):

    prods = {}
    def save_hook(name):
        def hook_per(self, inputs, outputs):
            prods[name] = np.prod(inputs[0].shape)
        return hook_per

    list_1 = []
    def simple_hook(self, inputs, outputs):
        list_1.append(np.prod(inputs[0].shape))

    list_2 = {}
    def simple_hook2(self, inputs, outputs):
        list_2['names'] = np.prod(inputs[0].shape)

    list_conv = []
    def conv_hook(self, input, output):
        batch_size, input_channels, input_height, input_width = input[0].size()
        output_channels, output_height, output_width = output[0].size()

        kernel_ops = self.kernel_size[0] * self.kernel_size[1] * (self.in_channels / self.groups)
        bias_ops = 1 if self.bias is not None else 0

        params = output_channels * (kernel_ops + bias_ops)
        # flops = (kernel_ops * (2 if multiply_adds else 1) + bias_ops) * output_channels * output_height * output_width * batch_size

        num_weight_params = (self.weight.data != 0).float().sum()
        flops = (num_weight_params * (2 if multiply_adds else 1) + bias_ops * output_channels) * output_height * output_width * batch_size

        list_conv.append(flops)

    list_linear = []
    def linear_hook(self, input, output):
        batch_size = input[0].size(0) if input[0].dim() == 2 else 1

        weight_ops = self.weight.nelement() * (2 if multiply_adds else 1)
        bias_ops = self.bias.nelement()

        flops = batch_size * (weight_ops + bias_ops)
        list_linear.append(flops)

    list_bn = []
    def bn_hook(self, input, output):
        list_bn.append(input[0].nelement() * 2)

    list_relu = []
    def relu_hook(self, input, output):
        list_relu.append(input[0].nelement())

    list_pooling = []
    def pooling_hook(self, input, output):
        batch_size, input_channels, input_height, input_width = input[0].size()
        output_channels, output_height, output_width = output[0].size()

        kernel_ops = self.kernel_size * self.kernel_size
        bias_ops = 0
        params = 0
        flops = (kernel_ops + bias_ops) * output_channels * output_height * output_width * batch_size

        list_pooling.append(flops)

    list_upsample = []

    # For bilinear upsample
    def upsample_hook(self, input, output):
        batch_size, input_channels, input_height, input_width = input[0].size()
        output_channels, output_height, output_width = output[0].size()

        flops = output_height * output_width * output_channels * batch_size * 12
        list_upsample.append(flops)

    def foo(net):
        childrens = list(net.children())
        if not childrens:
            if isinstance(net, torch.nn.Conv2d):
                net.register_forward_hook(conv_hook)
            if isinstance(net, torch.nn.Linear):
                net.register_forward_hook(linear_hook)
            if isinstance(net, torch.nn.BatchNorm2d):
                net.register_forward_hook(bn_hook)
            if isinstance(net, torch.nn.ReLU):
                net.register_forward_hook(relu_hook)
            if isinstance(net, torch.nn.MaxPool2d) or isinstance(net, torch.nn.AvgPool2d):
                net.register_forward_hook(pooling_hook)
            if isinstance(net, torch.nn.Upsample):
                net.register_forward_hook(upsample_hook)
            return
        for c in childrens:
            foo(c)


    foo(model)
    inputs = torch.rand(input_channels, input_res, input_res).unsqueeze(0)
    inputs.requires_grad = True
    inputs = inputs.cuda() if torch.cuda.is_available() else inputs.cpu()
    out = model(inputs)

    flops_ = (sum(list_conv) + sum(list_linear) + sum(list_bn) + sum(list_relu) + sum(list_pooling) + sum(list_upsample))

    return flops_


def total_flops(model_MQ):
    flops = count_model_flops(model_MQ.library)

    for expert in model_MQ.experts:
        flops += count_model_flops(expert, 32, 16)
    return flops