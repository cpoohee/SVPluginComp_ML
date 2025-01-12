import hydra
import os
import torch
import mlflow
import simpleaudio as sa
import pytorch_lightning as pl
from pathlib import Path
from omegaconf import DictConfig
from src.datamodule.audio_datamodule import AudioDataModule
from src.model.wavenet import WaveNet_PL
from src.model.waveUnet import WaveUNet_PL
from src.model.autoencoder import AutoEncoder_PL
from src.model.autoencoder_speaker import AutoEncoder_Speaker_PL
from src.model.autoencoder_speaker2 import AutoEncoder_Speaker_PL2
from tqdm import tqdm
from src.utils.losses import Losses


@hydra.main(config_path="../conf", config_name="config")
def main(cfg: DictConfig):
    cur_path = Path(os.path.abspath(hydra.utils.get_original_cwd()))
    data_path = cfg.dataset.data_path

    batch_size = cfg.training.batch_size

    cfg.training.accelerator = cfg.testing.accelerator

    dm_test = AudioDataModule(data_dir=(cur_path / data_path),
                              cfg=cfg,
                              batch_size=batch_size,
                              do_aug_in_test=cfg.testing.do_aug_in_test)
    dm_pred = AudioDataModule(data_dir=(cur_path / data_path),
                              cfg=cfg,
                              do_aug_in_predict=cfg.testing.do_aug_in_predict,
                              batch_size=1)

    mlflow.pytorch.autolog()

    ckpt_path = cfg.testing.checkpoint_file
    assert (ckpt_path is not None)

    if cfg.model.model_name == 'WaveNet_PL':
        model = WaveNet_PL.load_from_checkpoint(cur_path / Path(ckpt_path))
    elif cfg.model.model_name == 'WaveUNet_PL':
        model = WaveUNet_PL.load_from_checkpoint(cur_path / Path(ckpt_path))
    elif cfg.model.model_name == 'AutoEncoder_PL':
        model = AutoEncoder_PL.load_from_checkpoint(cur_path / Path(ckpt_path))
    elif cfg.model.model_name == 'AutoEncoder_Speaker_PL':
        cfg.model.embedder_path = cur_path / Path(cfg.model.embedder_path)
        cfg.model.ae_path = cur_path / Path(cfg.model.ae_path)
        model = AutoEncoder_Speaker_PL.load_from_checkpoint(cur_path / Path(ckpt_path), cfg=cfg)
    elif cfg.model.model_name == 'AutoEncoder_Speaker_PL2':
        cfg.model.embedder_path = cur_path / Path(cfg.model.embedder_path)
        cfg.model.ae_path = cur_path / Path(cfg.model.ae_path)
        model = AutoEncoder_Speaker_PL2.load_from_checkpoint(cur_path / Path(ckpt_path), cfg=cfg)
    else:
        assert False, " model name is invalid!"

    # module reads training loss, override loss with test loss fn
    cfg.training.loss = cfg.testing.loss
    model.loss_type = cfg.testing.lossfn
    model.loss = Losses(loss_type=cfg.testing.lossfn, sample_rate=cfg.dataset.sample_rate, cfg=cfg)

    trainer = pl.Trainer(accelerator=cfg.testing.accelerator)  # pl takes care of device
    trainer.test(model, dataloaders=dm_test)

    dm_pred.setup('predict')
    dm_pred = dm_pred.predict_dataloader()

    dev = torch.device(cfg.testing.accelerator)

    # manually place device, because we are doing prediction manually
    if model.device != dev:
        model = model.to(dev)

    pred_with_dvec = False
    if cfg.model.model_name == 'AutoEncoder_Speaker_PL' or \
            cfg.model.model_name == 'AutoEncoder_Speaker_PL2':
        pred_with_dvec = True

    with torch.no_grad():
        for batch in tqdm(dm_pred, desc=" predict progress", position=0):
            x, y, (dvec, dvec_unrelated), (name, name_unrelated) = batch

            if x.device != dev:
                x = x.to(dev)
            if y.device != dev:
                y = y.to(dev)

            if pred_with_dvec:
                if dvec.device != dev:
                    dvec = dvec.to(dev)
                if isinstance(dvec_unrelated, torch.Tensor) and dvec_unrelated.device != dev:
                    dvec_unrelated = dvec_unrelated.to(dev)

            segments = x.size()[2] // cfg.dataset.block_size
            resized_samples = segments * cfg.dataset.block_size
            x = x[:, :, 0:resized_samples]
            y = y[:, :, 0:resized_samples]

            if not pred_with_dvec:
                # do predict without dvec
                y_pred = torch.zeros_like(y)
                for i in tqdm(range(0, segments), desc=" sample progress", position=1, leave=False):
                    offsets = i * cfg.dataset.block_size
                    x_segment = x[:, :, offsets: (offsets + cfg.dataset.block_size)]
                    y_pred_segment = model(x_segment)
                    if y_pred_segment.size()[1] == 2:
                        y_pred_segment = y_pred_segment[:, 0, :]
                    y_pred[:, :, offsets: (offsets + cfg.dataset.block_size)] = y_pred_segment

                print('pred:', name)
                play_tensor(y_pred[0])

            else:
                # predict with its own dvec
                y_pred = torch.zeros_like(y)
                for i in tqdm(range(0, segments), desc=" sample progress", position=1, leave=False):
                    offsets = i * cfg.dataset.block_size
                    x_segment = x[:, :, offsets: (offsets + cfg.dataset.block_size)]
                    y_pred_segment = model(x_segment, dvec)
                    if y_pred_segment.size()[1] == 2:
                        y_pred_segment = y_pred_segment[:, 0, :]
                    y_pred[:, :, offsets: (offsets + cfg.dataset.block_size)] = y_pred_segment

                print('pred with own embedding:', name)
                play_tensor(y_pred[0])

                # predict with other's dvec
                y_pred = torch.zeros_like(y)
                for i in tqdm(range(0, segments), desc=" sample progress", position=1, leave=False):
                    offsets = i * cfg.dataset.block_size
                    x_segment = x[:, :, offsets: (offsets + cfg.dataset.block_size)]
                    y_pred_segment = model(x_segment, dvec_unrelated)
                    if y_pred_segment.size()[1] == 2:
                        y_pred_segment = y_pred_segment[:, 0, :]
                    y_pred[:, :, offsets: (offsets + cfg.dataset.block_size)] = y_pred_segment

                print('pred with other embedding:', name_unrelated)
                play_tensor(y_pred[0])

            print('original input')
            play_tensor(x[0])
            print('original target')
            play_tensor(y[0])


def play_tensor(tensor_sample, sample_rate=44100):
    try:
        numpy_sample = tensor_sample.cpu().numpy()
        play_obj = sa.play_buffer(numpy_sample, 1, 4, sample_rate=sample_rate)
        play_obj.wait_done()
    except KeyboardInterrupt:
        print("next")
        sa.stop_all()


if __name__ == "__main__":
    main()
