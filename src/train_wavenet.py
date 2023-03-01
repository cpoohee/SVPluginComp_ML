import hydra
import os
import pytorch_lightning as pl
from pathlib import Path
from omegaconf import DictConfig
from src.datamodule.audio_datamodule import AudioDataModule
from src.model.wavenet import WaveNet_PL


@hydra.main(config_path="../conf", config_name="config")
def main(cfg: DictConfig):
    cur_path = Path(os.path.abspath(hydra.utils.get_original_cwd()))
    data_path = cfg.dataset.data_path

    batch_size = cfg.training.batch_size
    dm_train = AudioDataModule(data_dir=(cur_path / data_path),
                               cfg=cfg,
                               batch_size=batch_size)

    wavenet_model = WaveNet_PL(cfg)

    trainer = pl.Trainer(
        max_epochs=cfg.training.max_epochs,
        accelerator=cfg.training.accelerator,
    )

    if cfg.training.resume_checkpoint:
        ckpt_path = cfg.training.checkpoint_file
    else:
        ckpt_path = None

    trainer.fit(wavenet_model, train_dataloaders=dm_train, ckpt_path=ckpt_path)
    trainer.save_checkpoint(cfg.training.experiment_ckpt_name)


if __name__ == "__main__":
    main()
