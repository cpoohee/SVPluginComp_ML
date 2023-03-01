import torch
import torchaudio
import pandas as pd
from torch.utils.data import Dataset
from omegaconf import DictConfig
from torch_audiomentations import Compose, Identity, Gain, PolarityInversion, \
    Shift, AddColoredNoise, PitchShift
from src.datamodule.augmentations.custom_pitchshift import PitchShift_Slow
from src.datamodule.augmentations.random_crop import RandomCrop


class AudioDataset(Dataset):
    def __init__(self, df: pd.DataFrame, cfg: DictConfig, do_augmentation: bool = False):
        self.df = df
        self.sample_length = int(
            cfg.dataset.sample_rate * cfg.process_data.clip_interval_ms / 1000.0)
        self.block_size = cfg.dataset.block_size
        self.sample_rate = cfg.dataset.sample_rate

        # for cropping audio length
        self.do_random_block = cfg.augmentations.do_random_block
        self.sample_length = cfg.augmentations.sample_length

        # augmentations params
        self.do_augmentation = do_augmentation

        self.aug_pitchshift = cfg.augmentations.do_pitchshift
        self.min_transpose_semitones = cfg.augmentations.min_transpose_semitones
        self.max_transpose_semitones = cfg.augmentations.max_transpose_semitones
        self.pitchshift_p = cfg.augmentations.pitchshift_p

        self.aug_colored_noise = cfg.augmentations.do_colored_noise
        self.min_snr_in_db = cfg.augmentations.min_snr_in_db
        self.max_snr_in_db = cfg.augmentations.max_snr_in_db
        self.min_f_decay = cfg.augmentations.min_f_decay
        self.max_f_decay = cfg.augmentations.max_f_decay
        self.colored_noise_p = cfg.augmentations.colored_noise_p

        self.aug_polarity_inv = cfg.augmentations.do_polarity_inv
        self.polarity_p = cfg.augmentations.polarity_p

        self.aug_gain = cfg.augmentations.do_gain
        self.gain_p = cfg.augmentations.gain_p
        self.min_gain_in_db = cfg.augmentations.min_gain_in_db
        self.max_gain_in_db = cfg.augmentations.max_gain_in_db

        self.aug_gain_indep = cfg.augmentations.do_gain_indep
        self.gain_p_indep = cfg.augmentations.gain_p_indep
        self.min_gain_in_db_indep = cfg.augmentations.min_gain_in_db_indep
        self.max_gain_in_db_indep = cfg.augmentations.max_gain_in_db_indep

        self.aug_timeshift_indep = cfg.augmentations.do_timeshift_indep
        self.min_shift_indep = cfg.augmentations.min_shift_indep
        self.max_shift_indep = cfg.augmentations.max_shift_indep
        self.timeshift_p_indep = cfg.augmentations.timeshift_p_indep

        self.aug_pitchshift_indep = cfg.augmentations.do_pitchshift_indep
        self.min_transpose_semitones_indep = cfg.augmentations.min_transpose_semitones_indep
        self.max_transpose_semitones_indep = cfg.augmentations.max_transpose_semitones_indep
        self.pitchshift_p_indep = cfg.augmentations.pitchshift_p_indep

    def __len__(self):
        return len(self.df)

    def __process_augmenations_combo(self, waveform):
        # conduct more augmentations,
        # include Identity in case no augmentation done, and apply_augmentation will still be valid
        transforms = [Identity()]

        if self.aug_gain:
            transforms.append(Gain(min_gain_in_db=self.min_gain_in_db,
                                   max_gain_in_db=self.max_gain_in_db,
                                   p=self.gain_p,
                                   p_mode='per_batch'))

        if self.aug_polarity_inv:
            transforms.append(PolarityInversion(p=self.polarity_p,
                                                p_mode='per_batch'))

        if self.aug_pitchshift:
            transforms.append(PitchShift(min_transpose_semitones=self.min_transpose_semitones,
                                         max_transpose_semitones=self.max_transpose_semitones,
                                         p=self.pitchshift_p,
                                         sample_rate=self.sample_rate,
                                         p_mode='per_batch'))

        if self.aug_colored_noise:
            transforms.append(AddColoredNoise(min_snr_in_db=self.min_snr_in_db,
                                              max_snr_in_db=self.max_snr_in_db,
                                              min_f_decay=self.min_f_decay,
                                              max_f_decay=self.max_f_decay,
                                              p=self.colored_noise_p,
                                              p_mode='per_batch'))

        apply_augmentation = Compose(transforms)
        waveform = apply_augmentation(waveform, sample_rate=self.sample_rate)

        return waveform

    def __process_augmentations_independent(self, waveform):
        transforms = [Identity()]

        if self.aug_gain_indep:
            transforms.append(Gain(min_gain_in_db=self.min_gain_in_db_indep,
                                   max_gain_in_db=self.max_gain_in_db_indep,
                                   p=self.gain_p_indep,
                                   p_mode='per_example'))
        if self.aug_timeshift_indep:
            transforms.append(Shift(min_shift=self.min_shift_indep,
                                    max_shift=self.max_shift_indep,
                                    p=self.timeshift_p_indep,
                                    p_mode='per_example',
                                    shift_unit='seconds'))

        # micro pitch cannot be done on torch_audiomentation, revert to original audiomentation
        if self.aug_pitchshift_indep:
            transforms.append(
                PitchShift_Slow(min_transpose_semitones=self.min_transpose_semitones_indep,
                                max_transpose_semitones=self.max_transpose_semitones_indep,
                                p=self.pitchshift_p_indep,
                                sample_rate=self.sample_rate,
                                p_mode='per_example'))

        apply_augmentation = Compose(transforms)
        waveform = apply_augmentation(waveform, sample_rate=self.sample_rate)

        return waveform

    def __random_block(self, waveform):
        apply_augmentation = Compose([RandomCrop(max_length=self.sample_length,
                                                 sampling_rate=self.sample_rate,
                                                 max_length_unit='samples')])
        waveform = apply_augmentation(waveform, sample_rate=self.sample_rate)
        return waveform

    def __getitem__(self, idx):
        data = self.df.iloc[idx]
        x_path = data['x']
        y_path = data['y']

        waveform_x, _ = torchaudio.load(x_path)
        waveform_y, _ = torchaudio.load(y_path)

        # do padding if file is too small
        length_x = waveform_x.size(dim=1)
        if length_x < self.sample_length:
            waveform_x = torch.nn.functional.pad(waveform_x,
                                                 (1, self.sample_length - length_x - 1),
                                                 "constant", 0)

        length_y = waveform_y.size(dim=1)
        if length_y < self.sample_length:
            waveform_y = torch.nn.functional.pad(waveform_y,
                                                 (1, self.sample_length - length_y - 1),
                                                 "constant", 0)

        # 'batch' up waveforms x and y together
        waveform_x = torch.unsqueeze(waveform_x, dim=0)
        waveform_y = torch.unsqueeze(waveform_y, dim=0)
        waveform = torch.cat((waveform_x, waveform_y), 0)

        if self.do_augmentation:
            # do augmentations that we want to affect on both x and y
            waveform = self.__process_augmenations_combo(waveform)

            # do augmentations that we want to affect on x and y independently
            waveform = self.__process_augmentations_independent(waveform)

        # decided to do augmentations first then do block cropping due to some sample time shifts
        if self.do_random_block:
            waveform = self.__random_block(waveform)

        waveform_x = waveform[0]
        waveform_y = waveform[1]

        return waveform_x, waveform_y
