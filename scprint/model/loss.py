import torch.nn.functional as F
import torch
from torch import nn, Tensor
from torch.autograd import Function


def mse(input: Tensor, target: Tensor) -> Tensor:
    """
    Compute the MSE loss between input and target.
    """
    input = torch.log2(input + 1)
    input = (input / torch.sum(input, dim=1, keepdim=True)) * 10000
    target = torch.log2(target + 1)
    target = target / torch.sum(target, dim=1, keepdim=True) * 10000
    return F.mse_loss(input, target, reduction="mean")


def masked_mse(input: Tensor, target: Tensor, mask: Tensor) -> Tensor:
    """
    Compute the masked MSE loss between input and target.
    """
    mask = mask.float()
    loss = F.mse_loss(input * mask, target * mask, reduction="sum")
    return loss / mask.sum()


def masked_mae(input: Tensor, target: Tensor, mask: Tensor) -> Tensor:
    """
    Compute the masked MAE loss between input and target.
    MAE = mean absolute error
    """
    mask = mask.float()
    loss = F.l1_loss(input * mask, target * mask, reduction="sum")
    return loss / mask.sum()


def masked_nb(input: Tensor, target: Tensor, mask: Tensor) -> Tensor:
    """
    Compute the masked negative binomial loss between input and target.
    """
    mask = mask.float()
    nb = torch.distributions.NegativeBinomial(total_count=target, probs=input)
    masked_log_probs = nb.log_prob(target) * mask
    return -masked_log_probs.sum() / mask.sum()


# FROM SCVI
def nb(target: Tensor, mu: Tensor, theta: Tensor, eps=1e-8):
    """
    This negative binomial function was taken from:
    Title: scvi-tools
    Authors: Romain Lopez <romain_lopez@gmail.com>,
             Adam Gayoso <adamgayoso@berkeley.edu>,
             Galen Xing <gx2113@columbia.edu>
    Date: 16th November 2020
    Code version: 0.8.1
    Availability: https://github.com/YosefLab/scvi-tools/blob/8f5a9cc362325abbb7be1e07f9523cfcf7e55ec0/scvi/core/distributions/_negative_binomial.py

    Computes negative binomial loss.
    Parameters
    ----------
    target: Tensor
         Torch Tensor of ground truth data.
    mu: Tensor
         Torch Tensor of means of the negative binomial (has to be positive support).
    theta: Tensor
         Torch Tensor of inverse dispersion parameter (has to be positive support).
    eps: Float
         numerical stability constant.

    Returns
    -------
    If 'mean' is 'True' NB loss value gets returned, otherwise Torch tensor of losses gets returned.
    """
    if theta.ndimension() == 1:
        theta = theta.view(1, theta.size(0))

    log_theta_mu_eps = torch.log(theta + mu + eps)
    res = (
        theta * (torch.log(theta + eps) - log_theta_mu_eps)
        + target * (torch.log(mu + eps) - log_theta_mu_eps)
        + torch.lgamma(target + theta)
        - torch.lgamma(theta)
        - torch.lgamma(target + 1)
    )

    return -res.mean()


def nb_dist(x: Tensor, mu: Tensor, theta: Tensor, eps=1e-8):
    loss = -NegativeBinomial(mu=mu, theta=theta).log_prob(x)
    return loss


def zinb(
    target: Tensor,
    mu: Tensor,
    theta: Tensor,
    pi: Tensor,
    eps=1e-8,
):
    """
    This zero-inflated negative binomial function was taken from:
    modified from scvi-tools

    Computes zero inflated negative binomial loss.
    Parameters
    ----------
    x: Tensor
            Torch Tensor of ground truth data.
    mu: Tensor
            Torch Tensor of means of the negative binomial (has to be positive support).
    theta: Tensor
            Torch Tensor of inverses dispersion parameter (has to be positive support).
    pi: Tensor
            Torch Tensor of logits of the dropout parameter (real support)
    eps: Float
        numerical stability constant.

    Returns
    -------
    ZINB loss value
    """
    #  uses log(sigmoid(x)) = -softplus(-x)
    softplus_pi = F.softplus(-pi)
    # eps to make it positive support and taking the log
    log_theta_mu_eps = torch.log(theta + mu + eps)
    pi_theta_log = -pi + theta * (torch.log(theta + eps) - log_theta_mu_eps)

    case_zero = F.softplus(pi_theta_log) - softplus_pi
    mul_case_zero = torch.mul((target < eps).type(torch.float32), case_zero)

    case_non_zero = (
        -softplus_pi
        + pi_theta_log
        + target * (torch.log(mu + eps) - log_theta_mu_eps)
        + torch.lgamma(target + theta)
        - torch.lgamma(theta)
        - torch.lgamma(target + 1)
    )
    mul_case_non_zero = torch.mul((target > eps).type(torch.float32), case_non_zero)

    res = mul_case_zero + mul_case_non_zero
    # we want to minize the loss but maximize the log likelyhood
    return -res.mean()


def criterion_neg_log_bernoulli(input: Tensor, target: Tensor, mask: Tensor) -> Tensor:
    """
    Compute the negative log-likelihood of Bernoulli distribution
    """
    mask = mask.float()
    bernoulli = torch.distributions.Bernoulli(probs=input)
    masked_log_probs = bernoulli.log_prob((target > 0).float()) * mask
    return -masked_log_probs.sum() / mask.sum()


def masked_relative_error(
    input: Tensor, target: Tensor, mask: torch.LongTensor
) -> Tensor:
    """
    Compute the masked relative error between input and target.
    """
    assert mask.any()
    loss = torch.abs(input[mask] - target[mask]) / (target[mask] + 1e-6)
    return loss.mean()


def graph_similarity(input1: Tensor, input2: Tensor, mask: Tensor) -> Tensor:
    """
    Compute the similarity of 2 generated graphs.
    """
    mask = mask.float()
    loss = F.mse_loss(input1 * mask, input2 * mask, reduction="sum")
    return loss / mask.sum()


def graph_sparsity(input: Tensor, mask: Tensor) -> Tensor:
    """
    Compute the sparsity of generated graphs.
    """
    mask = mask.float()
    loss = F.mse_loss(input * mask, torch.zeros_like(input) * mask, reduction="sum")
    return loss / mask.sum()


def similarity(x, y, temp):
    """
    Dot product or cosine similarity
    """
    res = F.cosine_similarity(x.unsqueeze(1), y.unsqueeze(0)) / temp
    labels = torch.arange(res.size(0)).long().to(device=res.device)
    return F.cross_entropy(res, labels)


def ecs(cell_emb, ecs_threshold=0.5):
    """
    ecs Computes the similarity of cell embeddings based on a threshold.

    Args:
        cell_emb (Tensor): A tensor representing cell embeddings.
        ecs_threshold (float, optional): A threshold for determining similarity. Defaults to 0.5.

    Returns:
        Tensor: A tensor representing the mean of 1 minus the square of the difference between the cosine similarity and the threshold.
    """
    # Here using customized cosine similarity instead of F.cosine_similarity
    # to avoid the pytorch issue of similarity larger than 1.0, pytorch # 78064
    # normalize the embedding
    cell_emb_normed = F.normalize(cell_emb, p=2, dim=1)
    cos_sim = torch.mm(cell_emb_normed, cell_emb_normed.t())

    # mask out diagnal elements
    mask = torch.eye(cos_sim.size(0)).bool().to(cos_sim.device)
    cos_sim = cos_sim.masked_fill(mask, 0.0)
    # only optimize positive similarities
    cos_sim = F.relu(cos_sim)
    return torch.mean(1 - (cos_sim - ecs_threshold) ** 2)


def classification(clsname, pred, cl, maxsize, labels_hierarchy={}):
    """
    Computes the classification loss for a given batch of predictions and ground truth labels.

    Args:
        clsname (str): The name of the label.
        pred (Tensor): The predicted logits for the batch.
        cl (Tensor): The ground truth labels for the batch.
        maxsize (int): The number of possible labels.
        labels_hierarchy (dict, optional): The hierarchical structure of the labels. Defaults to {}.

    Raises:
        ValueError: If the clsname is not found in the labels_hierarchy dictionary.

    Returns:
        Tensor: The computed binary cross entropy loss for the given batch.
    """
    newcl = torch.zeros(
        (cl.shape[0], maxsize), device=cl.device
    )  # batchsize * n_labels
    # if we don't know the label we set the weight to 0 else to 1
    valid_indices = (cl != -1) & (cl < maxsize)
    valid_cl = cl[valid_indices]
    newcl[valid_indices, valid_cl] = 1

    weight = torch.ones_like(newcl, device=cl.device)
    weight[cl == -1, :] = 0
    inv = cl >= maxsize
    # if we have non leaf values, we don't know so we don't compute grad and set weight to 0
    # and add labels that won't be counted but so that we can still use them
    if inv.any():
        if clsname in labels_hierarchy.keys():
            clhier = labels_hierarchy[clsname]

            inv_weight = weight[inv]
            # we set the weight of the elements that are not leaf to 0
            # i.e. the elements where we will compute the max
            inv_weight[clhier[cl[inv] - maxsize]] = 0
            weight[inv] = inv_weight

            addnewcl = torch.ones(
                weight.shape[0], device=pred.device
            )  # no need to set the other to 0 as the weight of the loss is set to 0
            addweight = torch.zeros(weight.shape[0], device=pred.device)
            addweight[inv] = 1
            # computing hierarchical labels and adding them to cl
            addpred = pred.clone()
            # we only keep the elements where we need to compute the max,
            # for the rest we set them to -inf, so that they won't have any impact on the max()
            inv_addpred = addpred[inv]
            inv_addpred[inv_weight.to(bool)] = torch.finfo(pred.dtype).min
            addpred[inv] = inv_addpred

            # differentiable max
            addpred = torch.logsumexp(addpred, dim=-1)

            # we add the new labels to the cl
            newcl = torch.cat([newcl, addnewcl.unsqueeze(1)], dim=1)
            pred = torch.cat([pred, addpred.unsqueeze(1)], dim=1)
            weight = torch.cat([weight, addweight.unsqueeze(1)], dim=1)
        else:
            raise ValueError("need to use labels_hierarchy for this usecase")

    myloss = torch.nn.functional.binary_cross_entropy_with_logits(
        pred, target=newcl, weight=weight
    )
    return myloss


class AdversarialDiscriminatorLoss(nn.Module):
    """
    Discriminator for the adversarial training for batch correction.
    """

    def __init__(
        self,
        d_model: int,
        n_cls: int,
        nlayers: int = 3,
        activation: callable = nn.LeakyReLU,
        reverse_grad: bool = True,
    ):
        super().__init__()
        # module list
        self.decoder = nn.ModuleList()
        for _ in range(nlayers - 1):
            self.decoder.append(nn.Linear(d_model, d_model))
            self.decoder.append(nn.LayerNorm(d_model))
            self.decoder.append(activation())
        self.out_layer = nn.Linear(d_model, n_cls)
        self.reverse_grad = reverse_grad

    def forward(self, x: Tensor, batch_labels: Tensor) -> Tensor:
        """
        Args:
            x: Tensor, shape [batch_size, embsize]
        """
        if self.reverse_grad:
            x = grad_reverse(x, lambd=1.0)
        for layer in self.decoder:
            x = layer(x)
        x = self.out_layer(x)
        return F.cross_entropy(x, batch_labels)


class GradReverse(Function):
    @staticmethod
    def forward(ctx, x: Tensor, lambd: float) -> Tensor:
        ctx.lambd = lambd
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output: Tensor) -> Tensor:
        return grad_output.neg() * ctx.lambd, None


def grad_reverse(x: Tensor, lambd: float = 1.0) -> Tensor:
    return GradReverse.apply(x, lambd)
