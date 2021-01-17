"""Neural style transfer in PyTorch. Implements A Neural Algorithm of Artistic
Style (http://arxiv.org/abs/1508.06576)."""

import copy
import warnings

from PIL import Image
import torch
from torch import optim, nn
from torch.nn import functional as F
from torchvision import models, transforms
from torchvision.transforms import functional as TF
from tqdm import tqdm, trange


class VGGFeatures(nn.Module):
    def __init__(self, layers):
        super().__init__()
        self.layers = sorted(set(layers))
        self.normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                              std=[0.229, 0.224, 0.225])
        self.model = models.vgg19(pretrained=True).features[:self.layers[-1] + 1]
        for i, layer in enumerate(self.model):
            if isinstance(layer, nn.MaxPool2d):
                self.model[i] = nn.MaxPool2d(2, ceil_mode=True)
        self.model.eval()
        self.model.requires_grad_(False)

    def forward(self, input, layers=None):
        layers = self.layers if layers is None else sorted(set(layers))
        feats = {}
        cur = 0
        for layer in layers:
            input = self.model[cur:layer+1](input)
            feats[layer] = input
            cur = layer + 1
        return feats


class ContentLoss(nn.Module):
    def __init__(self, target):
        super().__init__()
        self.register_buffer('target', target)

    def forward(self, input):
        return F.mse_loss(input, self.target, reduction='sum')


class StyleLoss(nn.Module):
    def __init__(self, target):
        super().__init__()
        self.register_buffer('target', target)

    @staticmethod
    def get_target(target):
        mat = target.flatten(-2)
        return mat @ mat.transpose(-2, -1) / mat.shape[-1]

    def forward(self, input):
        return F.mse_loss(self.get_target(input), self.target, reduction='sum')


class TVLoss(nn.Module):
    def forward(self, input):
        x_diff = input[..., :-1, :-1] - input[..., :-1, 1:]
        y_diff = input[..., :-1, :-1] - input[..., 1:, :-1]
        diff = x_diff**2 + y_diff**2
        return torch.sum(diff)


class WeightedLoss(nn.ModuleList):
    def __init__(self, losses, weights, verbose=False):
        super().__init__(losses)
        self.weights = weights
        self.verbose = verbose

    def _print_losses(self, losses):
        for i, loss in enumerate(losses):
            print(f'({i}) {self[i]!r}: {loss.item():g}')

    def forward(self, *args, **kwargs):
        losses = []
        for loss, weight in zip(self, self.weights):
            losses.append(loss(*args, **kwargs) * weight)
        if self.verbose:
            self._print_losses(losses)
        return sum(losses)


class Normalize(nn.Module):
    def __init__(self, module, scale=1, eps=1e-8):
        super().__init__()
        self.module = module
        self.module.register_backward_hook(self._hook)
        self.scale = scale
        self.eps = eps

    def _hook(self, module, grad_input, grad_output):
        i, *rest = grad_input
        dims = list(range(1, i.ndim))
        norm = abs(i).sum(dim=dims, keepdims=True)
        return i * self.scale / (norm + self.eps), *rest

    def extra_repr(self):
        return f'scale={self.scale!r}'

    def forward(self, *args, **kwargs):
        return self.module(*args, **kwargs)


class LayerApply(nn.Module):
    def __init__(self, module, layer):
        super().__init__()
        self.module = module
        self.layer = layer

    def extra_repr(self):
        return f'layer={self.layer!r}'

    def forward(self, input):
        return self.module(input[self.layer])


def size_to_fit(size, max_dim, scale_up=False):
    w, h = size
    if not scale_up and max(h, w) <= max_dim:
        return w, h
    new_w, new_h = max_dim, max_dim
    if h > w:
        new_w = round(max_dim * w / h)
    else:
        new_h = round(max_dim * h / w)
    return new_w, new_h


def gen_scales(start, n):
    for i in range(n):
        yield round(start * pow(2, i/2))


def interpolate(*args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        return F.interpolate(*args, **kwargs)


def scale_adam(state, shape):
    state = copy.deepcopy(state)
    for group in state['state'].values():
        exp_avg = group['exp_avg']
        exp_avg_sq = group['exp_avg_sq']
        group['exp_avg'] = interpolate(exp_avg, shape, mode='bicubic')
        group['exp_avg_sq'] = interpolate(exp_avg_sq, shape, mode='bilinear')
        group['exp_avg_sq'].relu_()
    return state


class StyleTransfer:
    def __init__(self, device='cpu'):
        self.device = torch.device(device)
        self.image = None

        self.content_layers = [22]

        self.style_layers = [1, 6, 11, 20, 29]
        style_weights = [256, 64, 16, 4, 1]
        weight_sum = sum(abs(w) for w in style_weights)
        self.style_weights = [w / weight_sum for w in style_weights]

        self.model = VGGFeatures(self.style_layers + self.content_layers).to(self.device)

    def get_image(self):
        if self.image is not None:
            return TF.to_pil_image(self.image[0])

    def stylize(self, content_img: Image.Image,
                style_img: Image.Image, *,
                content_weight: float = 0.01,
                tv_weight: float = 2e-7,
                initial_scale: int = 64,
                scales: int = 7,
                iterations: int = 500,
                step_size: float = 0.02):

        content_weights = [content_weight / len(self.content_layers)] * len(self.content_layers)

        tv_loss = LayerApply(TVLoss(), 'input')

        init_with_content = True

        cw, ch = size_to_fit(content_img.size, initial_scale, scale_up=True)
        if init_with_content:
            self.image = TF.to_tensor(content_img.resize((cw, ch), Image.LANCZOS))[None]
        else:
            self.image = torch.rand([1, 3, ch, cw]) / 255 + 0.5
        self.image = self.image.to(self.device)

        opt = None

        for scale in gen_scales(initial_scale, scales):
            cw, ch = size_to_fit(content_img.size, scale, scale_up=True)
            sw, sh = size_to_fit(style_img.size, scale)

            content = TF.to_tensor(content_img.resize((cw, ch), Image.LANCZOS))[None]
            style = TF.to_tensor(style_img.resize((sw, sh), Image.LANCZOS))[None]
            content, style = content.to(self.device), style.to(self.device)

            self.image = interpolate(self.image.detach(), (ch, cw), mode='bicubic').clamp(0, 1)
            self.image.requires_grad_()

            print(f'Processing content image ({cw}x{ch})...')
            content_feats = self.model(content, layers=self.content_layers)
            content_losses = []
            for i, layer in enumerate(self.content_layers):
                weight = content_weights[i]
                target = content_feats[layer]
                loss = LayerApply(Normalize(ContentLoss(target), weight), layer)
                content_losses.append(loss)

            print(f'Processing style image ({sw}x{sh})...')
            style_feats = self.model(style, layers=self.style_layers)
            style_losses = []
            for i, layer in enumerate(self.style_layers):
                weight = self.style_weights[i]
                target = StyleLoss.get_target(style_feats[layer])
                loss = LayerApply(Normalize(StyleLoss(target), weight), layer)
                style_losses.append(loss)

            crit = WeightedLoss([*content_losses, *style_losses, tv_loss],
                                [*content_weights, *self.style_weights, tv_weight])

            opt2 = optim.Adam([self.image], lr=step_size)
            if scale != initial_scale:
                opt_state = scale_adam(opt.state_dict(), (ch, cw))
                opt2.load_state_dict(opt_state)
            opt = opt2

            for i in trange(1, iterations + 1):
                feats = self.model(self.image)
                feats['input'] = self.image
                loss = crit(feats)
                tqdm.write(f'{i} {loss.item() / self.image.numel():g}')
                opt.zero_grad()
                loss.backward()
                opt.step()
                with torch.no_grad():
                    self.image.clamp_(0, 1)

        return self.get_image()
