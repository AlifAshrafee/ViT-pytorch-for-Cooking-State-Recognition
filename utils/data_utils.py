import logging
import albumentations as A

import torch

from torchvision import transforms, datasets
from torch.utils.data import DataLoader, RandomSampler, DistributedSampler, SequentialSampler


logger = logging.getLogger(__name__)


def get_loader(args):
    if args.local_rank not in [-1, 0]:
        torch.distributed.barrier()

    transform_train = transforms.Compose([
        transforms.RandomResizedCrop((args.img_size, args.img_size), scale=(0.05, 1.0)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])
    transform_train_aug = transforms.Compose([
        transforms.RandomResizedCrop((args.img_size, args.img_size), scale=(0.05, 1.0)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
        transforms.RandomHorizontalFlip(p=0.2),
        transforms.RandomApply([transforms.RandomChoice([transforms.RandomAffine(degrees=20, translate=(0.1,0.3), scale=(0.05, 0.75)),transforms.RandomRotation(50)])],p=0.2),
        transforms.RandomApply([transforms.RandomAdjustSharpness(sharpness_factor=2)],p=0.1),
        transforms.RandomApply([transforms.GaussianBlur(kernel_size=(3, 5), sigma=(0.1, 5))],p=0.1),
        transforms.RandomApply([transforms.RandomChoice([transforms.RandomAutocontrast(),transforms.ColorJitter(brightness=0.5, hue=0.3)])],p=0.2)
    ])

    transform_test = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    if args.dataset == "cifar10":
        trainset = datasets.CIFAR10(root="./data",
                                    train=True,
                                    download=True,
                                    transform=transform_train)
        testset = datasets.CIFAR10(root="./data",
                                   train=False,
                                   download=True,
                                   transform=transform_test) if args.local_rank in [-1, 0] else None

    else:
        if args.augmentation == True:
            trainset = datasets.ImageFolder(root="./data/DatasetV2/train",
                                     transform=transform_train_aug)
        else :
            trainset = datasets.ImageFolder(root="./data/DatasetV2/train",
                                     transform=transform_train)
        validset = datasets.ImageFolder(root="./data/DatasetV2/valid",
                                    transform=transform_test) if args.local_rank in [-1, 0] else None
        testset = datasets.ImageFolder(root="./data/DatasetV2/test",
                                    transform=transform_test) if args.local_rank in [-1, 0] else None
    if args.local_rank == 0:
        torch.distributed.barrier()

    train_sampler = RandomSampler(trainset) if args.local_rank == -1 else DistributedSampler(trainset)
    valid_sampler = SequentialSampler(validset)
    test_sampler = SequentialSampler(testset)
    train_loader = DataLoader(trainset,
                              sampler=train_sampler,
                              batch_size=args.train_batch_size,
                              num_workers=4,
                              pin_memory=True)
    valid_loader = DataLoader(validset,
                             sampler=valid_sampler,
                             batch_size=args.eval_batch_size,
                             num_workers=4,
                             pin_memory=True) if validset is not None else None
    test_loader = DataLoader(testset,
                             sampler=test_sampler,
                             batch_size=args.eval_batch_size,
                             num_workers=4,
                             pin_memory=True) if testset is not None else None

    return train_loader, valid_loader, test_loader
