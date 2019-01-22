import torch
import torch.autograd as autograd
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable

import scipy.io as sio
from scipy.signal import resample
import os

import csv

import numpy as np
import random

from multilabel_rbm import RBM as MRBM
from rbm import RBM
from class_rbm import ClassRBM

from sklearn import preprocessing

# %matplotlib inline
import matplotlib.pyplot as plt

from scipy.signal import correlate

experiments = os.listdir('../datasets/sample_experiments/')

scaler = preprocessing.MinMaxScaler(feature_range=[-1,1])
all_data = []

for experiment in experiments:
    data = sio.loadmat('../datasets/sample_experiments/' + experiment)
    data = data['Data_dq'][0][0][1][0][0][0]
    downsample_data = []
    for i in range(0,data.shape[0],200):
        downsample_data.append(data[i])
    downsample_data = np.asarray(downsample_data)
    all_data += list(downsample_data)

scaler.fit(all_data)
del all_data

experiment_samples = {}

for experiment in experiments:
    data = sio.loadmat('../datasets/sample_experiments/' + experiment)
    data = data['Data_dq'][0][0][1][0][0][0]
    downsample_data = []
    for i in range(0,data.shape[0],200):
        downsample_data.append(data[i])
    downsample_data = np.asarray(downsample_data)
    #all_data += list(downsample_data)
    experiment_samples[experiment[:-4]] = scaler.transform(downsample_data)

train = []
test = []

stride = 10
window = 30
for exp in experiment_samples.keys()[:14]:
    experiment_sample = experiment_samples[exp]

    samples = []
    for i in range(0, experiment_sample.shape[0], stride):
        if experiment_sample[i:i+window,:].shape[0] == window:
            samples.append(experiment_sample[i:i+window,:])

    random.shuffle(samples)
    train += samples

for exp in experiment_samples.keys()[14:]:
    print (exp)
    experiment_sample = experiment_samples[exp]

    samples = []
    for i in range(0, experiment_sample.shape[0], stride):
        if experiment_sample[i:i+window,:].shape[0] == window:
            samples.append(experiment_sample[i:i+window,:])

    random.shuffle(samples)
    test += samples

train = np.asarray(train)
test = np.asarray(test)


class FFNet(nn.Module):
    def __init__(self, input_dim):
        super(FFNet, self).__init__()
        self.linear1 = nn.Linear(input_dim, 360)
        self.linear2 = nn.Linear(360, 120)
        self.linear4 = nn.Linear(120, 30)

    def forward(self, seq):
        x = seq.view(seq.size()[0], -1)
        out = F.tanh(self.linear1(x))
        out = F.tanh(self.linear2(out))
#         out = self.linear3(out)
        out = self.linear4(out)
        #print (out.size())
        #base_out = out.view(seq.size()[0], seq.size()[1], seq.size()[2])
        return out


model = FFNet(90).cuda()
loss_function = nn.MSELoss()
lr = 0.1
optimizer = optim.SGD(model.parameters(), lr=lr)

w = csv.writer(open('../datasets/ann30_curr2.log','wb'))

for epoch in range(200):
    train = np.random.permutation(train)
    epoch_loss = 0
    for i in range(0, train.shape[0], 256):
        inp = np.concatenate((train[i:i+256, :, 0:2], train[i:i+256, :, 5:6]), axis=2)
        #out_true = np.concatenate((train[i:i+256, :, 3:5], train[i:i+256, :, 6:]), axis=2)
        out_true = train[i:i+256, :, 4]
        inp = Variable(torch.from_numpy(inp).type(torch.FloatTensor).cuda())
        out_true = Variable(torch.from_numpy(out_true).type(torch.FloatTensor).cuda())
        model.zero_grad()
        out_pred = model(inp)
        loss = loss_function(out_pred, out_true)
        loss.backward()
        optimizer.step()

        #print (loss.data[0])
        epoch_loss += loss.data[0]

    test_loss = 0
    for i in range(0, test.shape[0], 256):
        inp = np.concatenate((test[i:i+256, :, 0:2], test[i:i+256, :, 5:6]), axis=2)
        #out_true = np.concatenate((test[i:i+256, :, 3:5], test[i:i+256, :, 6:]), axis=2)
        out_true = test[i:i+256, :, 4]
        out_true = Variable(torch.from_numpy(out_true).type(torch.FloatTensor).cuda())
        inp = Variable(torch.from_numpy(inp).type(torch.FloatTensor).cuda())
        out_pred = model(inp)
        loss = loss_function(out_pred, out_true)

        test_loss += loss.data[0]

    print ("Epoch " + str(epoch) +  ": Train loss = " + str(epoch_loss.item()) + ", Test loss = " + str(test_loss.item()))
    w.writerow([epoch,epoch_loss.item(),test_loss.item()])

    if epoch % 10 == 0:
        for exp in experiment_samples.keys()[14:]:
            pred_curr1 = []
            pred_curr2 = []
            pred_torque = []
            for i in range(0, experiment_samples[exp].shape[0], 1):
                inp = np.concatenate((experiment_samples[exp][i:i+window, 0:2], experiment_samples[exp][i:i+window, 5:6]), axis=1)
                if inp.shape[0] == window:
                    inp = np.asarray([inp])
                    inp = Variable(torch.from_numpy(inp).type(torch.FloatTensor).cuda())
                    out_pred = model(inp)
                    #print (out_pred.size())
                    out_pred = out_pred.data.cpu().numpy()

                    pred_curr1 += list(out_pred[:, 0])
                    #pred_curr2 += list(out_pred[:, 1])
                    #pred_torque += list(out_pred[:, 2])

            # print (len(pred_curr1), experiment_samples['exp10'].shape)
            plt.plot(experiment_samples[exp][:,4])
            plt.savefig('../datasets/results_ann30/curr2_' + exp + '_epoch' + str(epoch) + '_true.png')
            plt.close()
            plt.plot(pred_curr1)
            plt.savefig('../datasets/results_ann30/curr2_' + exp + '_epoch' + str(epoch) + '_pred.png')
            plt.close()
