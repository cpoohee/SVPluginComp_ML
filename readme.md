# Introduction
This project investigates the use of AI generative models create vocal doubles for mixing from a single vocal take.
This is intended to be a short project aimed for submission for [Neural Audio Plugin Competition](https://www.theaudioprogrammer.com/neural-audio).

There are 2 separate git repository for this plugin competition. 
The first is for the machine learning code. The second is for the plugin code for running the trained model.

- https://github.com/cpoohee/SVPluginComp_ML (this repo, the ML code base)
- https://github.com/cpoohee/NeuralDoubler (Plugin code)

# Quick Installation Instructions

- For those who just want to get the plugin running, go to our plugin repo https://github.com/cpoohee/NeuralDoubler, and follow the instructions there.
- For those who wants to run the machine learning code, do follow the subsequent instructions in this repo.

# Replication Instructions

## Pre-requisites

- The ML code is created to run with Nvidia GPU (cuda) on Ubuntu 20.04 or Apple Silicon hardware (mps) in mind.
  - For installing cuda 11.8 drivers (https://cloud.google.com/compute/docs/gpus/install-drivers-gpu)
- The dataset and cached dataset size used are about 50 GB. Prepare at least 150GB of free hdd space. 

- Install Miniconda. [See guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html)
- For Apple Silicon, you will need to use Miniconda for mps acceleration. Anaconda is not recommended.

- [install git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

- Install system libraries
  - for ubuntu
    - `sudo apt-get update`
    - `sudo apt-get install libsndfile1`
  - for mac
    - install brew. See https://brew.sh/
    - `brew install libsndfile`

## Platforms used for development
- Pytorch with pytorch lightning for machine learning
- Hydra, for configurations
- MLFlow, for experiment tracking
- ONNX, for porting model to C++ runtime

## Clone the repository

Go to your terminal, create a folder that you would like to clone the repo. 

Run the following command in your terminal to clone this repo. 

`git clone https://github.com/cpoohee/SVPluginComp_ML`

## Create conda environment
Assuming, miniconda is properly installed, run the following to create the environment  
`conda env create -f environment.yml`

Activate the environment

`conda activate wave`

## Download Dataset

A script is created for downloading the following datasets
- NUS-48E
- VocalSet
- VCTK

Go to the project root folder

`cd SVPluginComp_ML`

Run the download script

`python src/download_data.py` 

* in case of failed downloads especially from gdrive, you may need try again later. 

The script will download the raw datasets and saves it onto `/data/raw` folder.
It also transcodes and transfers useful audio files to wav into the `/data/interim` folder.

## Download Pre-trained Models
Run the download script

`python src/download_pre-trained_models.py` 

It will download models into the `/models/pre-trained` folder

## Pre-process Dataset
Continue running from the same project root folder,

`python src/process_data.py process_data/dataset=nus_vocalset_vctk`

The above command will pre-process NUS-48E, VCTK and vocalset datasets.

Pre-processing will split the dataset into train/validation/test/prediction splits as stored into the `./data/processed` folder.
It also slices the audio into 5 sec long clips.

### (Optional) replace it with options:

* `process_data/dataset=nus` for pre-processing just the NUS-48E dataset
* `process_data/dataset=vctk` for pre-processing just the VCTK dataset

* Edit the `conf/process_data/process_root.yaml` for more detailed configurations.

## Cache speech encodings
Run the following 

`python src/cache_dataset.py model=autoencoder_speaker dataset=nus_vocalset_vctk`

It will cache the downloaded pre-trained speaker encoder's embeddings.

### (Optional)
To use cuda (Nvidia)
`python src/cache_dataset.py model=autoencoder_speaker dataset=nus_vocalset_vctk process_data.accelerator=cuda`.

or mps (Apple silicon)
`python src/cache_dataset.py model=autoencoder_speaker dataset=nus_vocalset_vctk process_data.accelerator=mps`.

## Train model 

`python src/train_model.py augmentations=augmentation_enable model=autoencoder_speaker dataset=nus_vocalset_vctk`

* See the `conf/training/train.yaml` for more training options to override.
  * for example, append the parameter `training.batch_size=8` to change batch size
  * `training.learning_rate=0.0001` to change the learning rate
  * `training.experiment_name=experiment1` to change the model's ckpt filename.
  * `training.max_epochs=30` to change the number of epochs to train.
  * `training.accelerator=mps` for Apple Silicon hardware

* See `conf/model/autoencoder_speaker.yaml` for model specifications to override

## Experiment Tracking
Under the `./outputs/` folder, look for the current experiment's `mlruns` folder.

e.g. `outputs/2023-03-20/20-11-30/mlruns`

In your terminal, replace the `$PROJECT_ROOT` and outputs to your full project path and run the following.

`mlflow server --backend-store-uri file:'$PROJECT_ROOT/outputs/2023-03-20/20-11-30/mlruns'`

By default, you will be able to view the experiment tracking under `http://127.0.0.1:5000/` on your browser.

Models will be saved into the folders as `.ckpt` under

`$PROJECT_ROOT/outputs/YYYY-MM-DD/HH-MM-SS/models`

By default, the model will save a checkpoint every end of epoch.

## Test and Predict the model

Replace `$PATH/TO/MODEL/model.ckpt` to the saved model file, and run

`python src/test_model.py  model=autoencoder_speaker dataset=nus_vocalset_vctk testing.checkpoint_file="$PATH/TO/MODEL/model.ckpt"`

## Export trained model into ONNX format.
The script will convert the pytorch model into ONNX format, which will be needed for the plugin code.

Replace `$PATH/TO/MODEL/model.ckpt` to the saved model file,
Replace `"./models/onnx/my_model.onnx"` to specify the ONNX file path to be saved file, and run

`python src/export_model_to_onnx.py export_to_onnx.checkpoint_file="$PATH/TO/MODEL/model.ckpt" export_to_onnx.export_filename="./models/onnx/my_model.onnx"`

Copy the ONNX file to the C++ plugin code.

# ---End of Instructions---


# Background
With some literature review, some possibilities in audio AI that are suitable for music production are:

- Singing/Speech Voice Conversion (VC)
- Singing/Speech Style Conversion
- Text to Speech (TTS)
- Singing Voice Synthesis
- Audio source separation

There are definitely more AI applications than listed above.

However, most of the demos are lacking in fidelity with audio downsampled to 20khz or less. 
Ideally it should be is at least 44100Hz.
The resultant generated audio are therefore missing high-end frequencies 10khz and more.
Our plugin should avoid not sacrifice fidelity. 

In a typical highly produced multitrack for mixing, the vocal double/triples or more could be recorded for mixing. 
An experienced mixer will be able to utilise the doubling effect to enhance the performance by adding the double track balanced just below the lead vocal track.
The resulting vocal performance will cut through the mix and sound thicker.

A simple copy of the same track does not work as doubling as the sum of two identical track just results in a 3db louder audio. 
Therefore, a double track is always taken from a different take. 
The differences in (and not limited to) phase, pitch, timing, timbre of a fresh take all contributes to the doubling effect.

It is even more so for background vocals which are usually produced with more than 2 takes of the same parts, multiplied by the harmony lines.

Without double tracks, a mixer do make use of some existing artificial techniques that mimic doubling. 
For example, de-tuning, delaying, chorusing a copy the same track. See Waves's doubler.
Given an option to a mixer however, it is likely we will choose the real double take over the synthetic doubler.   

Few have approached the generative audio for producing double takes that is suitable for the audio doubling effect. 
For a mixer, this is a potential time and money saver.

It is also hoped that using vocal conversion, it will produce a timbre based doubling effect sounding natural enough for the listener.  

Some papers that might be related are: 

- [Tae, Jaesung, Hyeongju Kim, and Younggun Lee. "Mlp singer: Towards rapid parallel korean singing voice synthesis." 2021 IEEE 31st International Workshop on Machine Learning for Signal Processing (MLSP). IEEE, 2021.](https://arxiv.org/abs/2106.07886)
- [Tamaru, Hiroki, et al. "Generative moment matching network-based neural double-tracking for synthesized and natural singing voices." IEICE TRANSACTIONS on Information and Systems 103.3 (2020): 639-647.](https://www.jstage.jst.go.jp/article/transinf/E103.D/3/E103.D_2019EDP7228/_pdf)
- [AlBadawy, Ehab A., and Siwei Lyu. "Voice Conversion Using Speech-to-Speech Neuro-Style Transfer." Interspeech. 2020.](https://ebadawy.github.io/post/speech_style_transfer/Albadawy_et_al-2020-INTERSPEECH.pdf)
- [AUTOVC: Zero-Shot Voice Style Transfer with Only Autoencoder Loss](https://arxiv.org/pdf/1905.05879.pdf)
- 
For ML datasets, usually we feed an input X and target Y for the model to learn (X->Y).

Potentially, our dataset for double takes could be easier if the model learns by using the same input audio as the target.
- (X -> X).

The model will therefore predict X* from the input X.
- (X->X*).

Our (X - X*) should be non-zero but close enough to be a good double. 
This will be subjected to some measurable metrics for objective comparison. 

If we are able to find double take datasets, it will be useful as well. 
That is X is the lead, Y is the double.

The end result should produce natural sounding audio which might only be subjectively judged.

Lastly, the model should be small and performant enough to run in a plugin.

# Goal
- To generate high quality audio usable for mixing. (sample rate >= 44100Hz)
- plugin latency should be low. ( <= 1 sec of samples )
- deterministic/reproducibility of plugin models ( the AI model should not churn out a different output for the same playback)
- Model size should be acceptable for plugin installation. ( <200MB )
- CPU usage should also be acceptable. (10 instances running real time in a DAW at the same time)

# Stretched Goal
- provide a vocal personality for VC, and use it for background harmony.
- auto generate harmony similar to Waves's Harmony plugin, with our vocal personality.

# ToDos
- Create a simple JUCE plugin without AI as a start. (done)
- Search good quality datasets, do preprocessing (done)
- prepare possible augmentations (done)
- create the basic wavenet (done)
- investigate loss functions (done)
  - checked out ESR, DC, LogCosh, SNR, SDSDR, MSE, various stft 
  - quick training suggest each have its own weakness see results.xlsx in models
  - sticking to multi res stft after it sounds the most natural 
- train a decent model without bells and whistles, etc augmentation. just able to produce identity sound will do. (done)
- create a pipeline of model deployment into JUCE (done)
  - convert model to ONNX, 
  - in JUCE, use ONNX runtime in c++
- Iterate experiments. 
  - check out STFT based loss functions, already part of auraloss (done)
  - check U wave net. (done)
  - train 'spectral recovery' type of neural model (done)
    - using low passed input. predict full spectrum sound.
  - Increase model size on the small NUS dataset, evaluate usefulness(done)
  - However, there is a realisation that training from scratch is not practical with current time and machine limitation.
  - Try out pre-trained auto encoders (done)
    - using an oversampled audio into an encoder trained in 48kHz seems to be a possible solution to reduce degrading quality for short sample block
    - Notebook investigating auto encoders
  - Try out pre-trained speaker embedding (done)
    - re process data folders.. etc speakerA/1.wav, speakerB/1.wav
    - do tsne plot of the output embeddings of the speakers.
  - Try out auto encoder + speaker embedding finetuning 
    - train with A's wave on target speaker A embedding, reconstructing A's wave 
  - test with A's wave on target speaker B embedding, reconstructing A's wave with B's style  

- Improve plugin usefulness
  - UI
  - Sound, might need tricks to beat the weird bleep during the front of output 
- prepare a video demo

# Stretched ToDos
- download and extract free multitracks that contains vocal doubles, use it to train/ fine-tune the model

# Datasets
- NUS-48E
  - [Duan, Zhiyan, et al. "The NUS sung and spoken lyrics corpus: A quantitative comparison of singing and speech." 2013 Asia-Pacific Signal and Information Processing Association Annual Summit and Conference. IEEE, 2013.](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=6694316)
  - 12 singers with 4 songs for each singer
  - 48 pairs of sung and spoken
- VocalSet
  - [Wilkins, Julia, et al. "VocalSet: A Singing Voice Dataset." ISMIR. 2018.](https://zenodo.org/record/1193957#.Y_zvvexBzA0)

- VCTK
  - [Veaux, Christophe, Junichi Yamagishi, and Kirsten MacDonald. "CSTR VCTK corpus: English multi-speaker corpus for CSTR voice cloning toolkit." University of Edinburgh. The Centre for Speech Technology Research (CSTR) (2017).](https://datashare.ed.ac.uk/handle/10283/3443)
- more data to come...

# Experiments
- use a simple wavenet. time based input/output, convert to run in JUCE
- use a pre-trained auto encoder
- use a pre-trained speaker embedding

# Findings
- multi res stft loss function creates the most natural sounding generation, tested on basic wavenet
- melspectrum, any preemphasis also resulted in less natural sounding generation
- augmentations done on training/testing data only produces models that predicts the original wav, 
  - the resulting audio is almost a copy of input.
  - might need a new loss function to penalise exact copy. even then, the audio could be phased flip, eg cossimloss == 1 or -1 
- realisation that for any useful effects to be used, training from scratch is not practical for this competition.
  - current machine is not capable to run experiments in time.
  - need to find pre-trained models, fine-tune and adapt to other potential useful plugins. 
- pre-trained models also suffer reconstruction artifacts.
  - there is an issue of degrading audio from short sample blocks, any lower than 32768 samples. (nearly 0.68 sec)
  - we should be able to oversample the audio, passing 32768 samples into the pre-trained model(trained in 48kHz), which represents a shorter blocktime (0.17 sec).
  - might explore `cached_conv` library to solve clicks from inferencing the beginning of the sample block. Onnx might not be able to convert it??
  - the 32 channels in the bottleneck vector z, where it is sized [batch, 32, T], is likely to represent some frequency bands based on the quick experiment on zeroing out some channels. See (notebooks/reducing_bottleneck_of_AE(channels).ipynb) 
  
# Brief description of Source code folders and scripts
- download_data.py -> downloads dataset into data/raw, then pick the audio and place into data/interim
- download_pre-trained_models.py -> download pre-trained models into models/pre-trained for later uses. 
- process_data.py -> use the audio from data/interim, process the audio into xx sec blocks, cuts silences and place into data/processed
- cache_dataset.py -> cache dataset's speech embeddings from wav files.
- train_model.py -> trains data from data/processed,
- test_model.py -> test (output as metrics) and do prediction (outputs for listening ) from data/processed
- export_model_to_onnx.py -> export model to onnx 