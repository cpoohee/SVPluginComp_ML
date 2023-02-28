# Introduction
This project investigates the use of AI generative models create vocal doubles for mixing from a single vocal take.
This is intended to be a short project aimed for submission for [Neural Audio Plugin Competition](https://www.theaudioprogrammer.com/neural-audio).

# Installation Instructions
- placeholder

# Background
Some literature review on what's possible in recent audio AI, and suitable for music production are:

- audio source separation
- Singing/Speech Voice Conversion (VC)
- Singing/Speech Style Conversion
- Text to Speech (TTS)
- Singing Voice Synthesis 

There are definitely more AI applications than listed above.

Most of the demos are lacking in fidelity with audio downsampled to 20khz or less. 
The resultant generated audio are therefore missing high-end frequencies 10khz and more.
Our plugin should avoid that sacrifice fidelity. 

Personally, I have experience in recording and mixing music too. 
In a live performance recording with a small group of musicians (5 people), it is difficult to get a refined vocal lead/background performances comparable to highly produced production.

In a typical highly produced multitrack for mixing, the vocal double/triples or more could be recorded for mixing. 
An experienced mixer will be able to utilise the doubling effect to enhance the performance by adding the double track balanced just below the lead track.
The resulting vocal performance will cut through the mix and sound thicker.

A simple copy of the same track does not work as doubling as the sum of two identical track just results in a 3db louder audio. 
Therefore, a double track is always a different take from the lead track. 
The differences in (and not limited to) phase, pitch, timing, tone of a fresh take all contributes to the doubling effect.

Even more so for background vocals, they are usually more than 2 takes of the same parts, multiplied by the harmony lines.

Without double tracks, a mixer do make use of some existing artificial techniques that mimic doubling. 
For example, de-tuning, delaying, chorusing a copy the same track. See Waves's doubler.
However, a mixer will want to have the option to choose the real double take over the synthetic doubler.   

Few have approached the generative audio from the same audio to produce a double take that is suitable for the audio doubling effect. 
Probably it is not exciting enough to publish a research work, but for a mixer, this is a potential time and money saver.
It is also hoped that with enough variations and stacked layers of this plugin, it will sound natural enough for the listener.  

Some papers that might be related are: 

- [Tae, Jaesung, Hyeongju Kim, and Younggun Lee. "Mlp singer: Towards rapid parallel korean singing voice synthesis." 2021 IEEE 31st International Workshop on Machine Learning for Signal Processing (MLSP). IEEE, 2021.](https://arxiv.org/abs/2106.07886)
- [Tamaru, Hiroki, et al. "Generative moment matching network-based neural double-tracking for synthesized and natural singing voices." IEICE TRANSACTIONS on Information and Systems 103.3 (2020): 639-647.](https://www.jstage.jst.go.jp/article/transinf/E103.D/3/E103.D_2019EDP7228/_pdf)

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
- Search good quality datasets, do preprocessing
- create a pipeline of model deployment into JUCE
- Iterate experiments. 

# Datasets
- NUS-48E
  - [Duan, Zhiyan, et al. "The NUS sung and spoken lyrics corpus: A quantitative comparison of singing and speech." 2013 Asia-Pacific Signal and Information Processing Association Annual Summit and Conference. IEEE, 2013.](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=6694316)
  - 12 singers with 4 songs for each singer
  - 48 pairs of sung and spoken
- VocalSet
  - [Wilkins, Julia, et al. "VocalSet: A Singing Voice Dataset." ISMIR. 2018.](https://zenodo.org/record/1193957#.Y_zvvexBzA0)

- more data to come...

# Experiments
- use a simple wavenet. time based input/output, convert to run in JUCE
- use a STFT-based input to investigate latency limitation or benefits in natural sounding
- Decide on method and improve.

