import torch
import torchvision
import torch.nn as nn
import torchvision.transforms as transforms
from data_loader import LvoMTDataLoader
import numpy as np
import tqdm
from tqdm import tqdm
import pandas as pd
import os
from utils import AverageMeter
from models import resnet

norm = False
num_channels=40
data_to_load = 'csv/dataset.csv'
best_model_dir = 'results/resnet_mt_2fc_reg_for_test_1/models/best_model.pth'
test_result_dir = 'results/resnet_mt_2fc_reg_for_test_1'


def main():
    transform = transforms.Compose([transforms.ToTensor()])

    test_set = LvoMTDataLoader(csv_file=data_to_load, transform=transform, mode='test', augment=False)
    test_loader = torch.utils.data.DataLoader(test_set, batch_size=4, shuffle=False, num_workers=4)

    model = get_model(image_channels=num_channels).cuda()
    model.load_state_dict(torch.load(best_model_dir))

    model.eval()
    criterion = nn.MSELoss()
    losses = AverageMeter()
    tbar = tqdm(test_loader, desc='\r')
    with torch.no_grad():
        name_history = []
        pred_level_history = []
        pred_width_history = []
        target_level_history = []
        target_width_history = []
        for batch_idx, (names, inputs, targets) in enumerate(tbar):

            inputs = inputs.float()
            targets = torch.stack((targets[0], targets[1])).float()
            inputs, targets = inputs.cuda(), targets.cuda(non_blocking=True)
            # compute output
            outputs = model(inputs).float()

            output_a = outputs[0]
            output_b = outputs[1]
            target_a = targets[0]
            target_b = targets[1]
            loss = criterion(output_a, target_a) + criterion(output_b, target_b)

            losses.update(loss.item(), inputs.size(0))

            pred = outputs.cpu().numpy()
            pred_level = pred[0]
            pred_width = pred[1]
            targets = targets.cpu().numpy()
            target_level = targets[0]
            target_width = targets[1]

            name_history = np.concatenate((name_history, names), axis=0)
            pred_level_history = np.concatenate((pred_level_history, pred_level), axis=0)
            pred_width_history = np.concatenate((pred_width_history, pred_width), axis=0)
            target_level_history = np.concatenate((target_level_history, target_level), axis=0)
            target_width_history = np.concatenate((target_width_history, target_width), axis=0)

            tbar.set_description('\r %s Loss: %.3f' % ('Test', losses.avg))

        df = pd.DataFrame()
        df['subj'] = name_history
        df['prediction_level'] = pred_level_history * 4096 - 1024 if norm else pred_level_history
        df['prediction_width'] = pred_width_history * 4096 - 1024 if norm else pred_width_history
        df['target_level'] = target_level_history * 4096 - 1024 if norm else target_level_history
        df['target_width'] = target_width_history * 4096 - 1024 if norm else target_width_history
        df.to_csv(os.path.join(test_result_dir, 'test.csv'))


def get_model(image_channels=40):
    model = resnet.mt_resnet18()
    for p in model.parameters():
        p.requires_grad = True

    model.conv1 = nn.Conv2d(image_channels, 64, kernel_size=(7, 7), stride=2, padding=3, bias=False)
    return model


if __name__ == '__main__':
    main()
