import torch.utils.data as data
import numpy as np
import torch
from .preprocess import process_feat

class Dataset(data.Dataset):
    def __init__(self, args, rgb_list_file, audio_list_file, labels=None, transform=None, test_mode=False):
        self.modality = args.modality

        if test_mode:
            # self.rgb_list_file = args.test_rgb_list
            # self.flow_list_file = args.test_flow_list
            # self.audio_list_file = args.test_audio_list
            self.rgb_list_file = rgb_list_file
            self.audio_list_file = audio_list_file
        else:
            self.rgb_list_file = rgb_list_file
            #self.flow_list_file = args.flow_list
            self.audio_list_file = audio_list_file
            self.labels = labels
        self.max_seqlen = args.max_seqlen
        self.tranform = transform
        self.test_mode = test_mode
        self.normal_flag = '_label_A'
        self._parse_list()

    def _parse_list(self):
        if self.modality == 'AUDIO':
            self.list = self.audio_list_file
        elif self.modality == 'RGB':
            self.list = self.rgb_list_file
        elif self.modality == 'FLOW':
            self.list = self.flow_list_file
        elif self.modality == 'MIX':
            self.list = self.rgb_list_file
            self.flow_list = self.flow_list_file
        elif self.modality == 'MIX2':
            self.list = self.rgb_list_file
            self.audio_list = self.audio_list_file
        elif self.modality == 'MIX3':
            self.list = self.flow_list_file
            self.audio_list = self.audio_list_file
        elif self.modality == 'MIX_ALL':
            self.list = self.rgb_list_file
            self.flow_list = self.flow_list_file
            self.audio_list = self.audio_list_file
        else:
            assert 1 > 2, 'Modality is wrong!'

    def __getitem__(self, index):
        if self.test_mode:
            label = 0
        else:
            label = self.labels[index]

        if self.modality == 'AUDIO':
            features = np.array(np.load(self.list[index]), dtype=np.float32)
        elif self.modality == 'RGB':
            features = np.array(np.load(self.list[index]),dtype=np.float32)
        elif self.modality == 'FLOW':
            features = np.array(np.load(self.list[index]), dtype=np.float32)
        elif self.modality == 'MIX':
            features1 = np.array(np.load(self.list[index]), dtype=np.float32)
            features2 = np.array(np.load(self.flow_list[index]), dtype=np.float32)
            if features1.shape[0] == features2.shape[0]:
                features = np.concatenate((features1, features2),axis=1)
            else:# because the frames of flow is one less than that of rgb
                features = np.concatenate((features1[:-1], features2), axis=1)
        elif self.modality == 'MIX2':
            features1 = np.array(np.load(self.list[index]), dtype=np.float32)
            features2 = np.array(np.load(self.audio_list[index//5]), dtype=np.float32)
            if features1.shape[0] == features2.shape[0]:
                features = np.concatenate((features1, features2),axis=1)
            elif features1.shape[0] > features2.shape[0]:
                features = np.concatenate((features1[:features2.shape[0]], features2), axis=1)
            else:
                features = np.concatenate((features1, features2[:features1.shape[0]]), axis=1)
        elif self.modality == 'MIX3':
            features1 = np.array(np.load(self.list[index]), dtype=np.float32)
            features2 = np.array(np.load(self.audio_list[index//5]), dtype=np.float32)
            if features1.shape[0] == features2.shape[0]:
                features = np.concatenate((features1, features2),axis=1)
            else:# because the frames of flow is one less than that of rgb
                features = np.concatenate((features1[:-1], features2), axis=1)
        elif self.modality == 'MIX_ALL':
            features1 = np.array(np.load(self.list[index]), dtype=np.float32)
            features2 = np.array(np.load(self.flow_list[index]), dtype=np.float32)
            features3 = np.array(np.load(self.audio_list[index//5]), dtype=np.float32)
            if features1.shape[0] == features2.shape[0]:
                features = np.concatenate((features1, features2, features3),axis=1)
            else:# because the frames of flow is one less than that of rgb
                features = np.concatenate((features1[:-1], features2, features3[:-1]), axis=1)
        else:
            assert 1>2, 'Modality is wrong!'
        if self.tranform is not None:
            features = self.tranform(features)
        if self.test_mode:
            return features

        else:
            features = process_feat(features, self.max_seqlen, is_random=False)
            return features, label

    def __len__(self):
        return len(self.list)