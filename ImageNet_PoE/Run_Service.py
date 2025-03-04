from __future__ import print_function
import argparse
import torch
from utils.envset import set_seed
from Service.test_Model import test_MQ


def main():
    # Service settings
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', type=str, default='cpu', required=False)
    parser.add_argument('--batch_size', type=int, default=128, metavar='N')
    parser.add_argument('--data_root', type=str, default='data')
    parser.add_argument('--momentum', type=float, default=0.9, metavar='M', help='SGD momentum (default: 0.9)')
    parser.add_argument('--seed', type=int, default=1, metavar='S', help='random seed (default: 1)')
    parser.add_argument('--queriedTask', required=True, nargs='+', type=str)

    args = parser.parse_args()

    use_cuda = torch.cuda.is_available()
    set_seed(args)

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    args.device = torch.device("cuda" if use_cuda else "cpu")

    print(args)

    # get specialised Model
    print('\nQueried Task:', args.queriedTask)
    test_MQ(args)


if __name__ == '__main__':
    main()
