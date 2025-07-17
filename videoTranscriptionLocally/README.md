# Description
Small script to convert video files with help of `ffmpeg` and OpenAI's `whisper` to a transcript.  
Unless you have GPU support, transcribing will take a while (see the 4 min-example output for a 40 min video).  
Stuff the result into any LLM for high level summary, done.

## Call

```bash
time python main.py foo.mp4
```

## Example view of the execution

```bash
 time python main.py foo.mp4                                                                      INT ✘  videoTranscriptionLocally  

[1/3] Extracting audio...
ffmpeg version n7.1.1 Copyright (c) 2000-2025 the FFmpeg developers
  built with gcc 15.1.1 (GCC) 20250425
  configuration: --prefix=/usr --disable-debug --disable-static --disable-stripping --enable-amf --enable-avisynth --enable-cuda-llvm --enable-lto --enable-fontconfig --enable-frei0r --enable-gmp --enable-gnutls --enable-gpl --enable-ladspa --enable-libaom --enable-libass --enable-libbluray --enable-libbs2b --enable-libdav1d --enable-libdrm --enable-libdvdnav --enable-libdvdread --enable-libfreetype --enable-libfribidi --enable-libglslang --enable-libgsm --enable-libharfbuzz --enable-libiec61883 --enable-libjack --enable-libjxl --enable-libmodplug --enable-libmp3lame --enable-libopencore_amrnb --enable-libopencore_amrwb --enable-libopenjpeg --enable-libopenmpt --enable-libopus --enable-libplacebo --enable-libpulse --enable-librav1e --enable-librsvg --enable-librubberband --enable-libsnappy --enable-libsoxr --enable-libspeex --enable-libsrt --enable-libssh --enable-libsvtav1 --enable-libtheora --enable-libv4l2 --enable-libvidstab --enable-libvmaf --enable-libvorbis --enable-libvpl --enable-libvpx --enable-libwebp --enable-libx264 --enable-libx265 --enable-libxcb --enable-libxml2 --enable-libxvid --enable-libzimg --enable-libzmq --enable-nvdec --enable-nvenc --enable-opencl --enable-opengl --enable-shared --enable-vapoursynth --enable-version3 --enable-vulkan
  libavutil      59. 39.100 / 59. 39.100
  libavcodec     61. 19.101 / 61. 19.101
  libavformat    61.  7.100 / 61.  7.100
  libavdevice    61.  3.100 / 61.  3.100
  libavfilter    10.  4.100 / 10.  4.100
  libswscale      8.  3.100 /  8.  3.100
  libswresample   5.  3.100 /  5.  3.100
  libpostproc    58.  3.100 / 58.  3.100
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'foo.mp4':
  Metadata:
    major_brand     : isom
    minor_version   : 512
    compatible_brands: isomiso2
    creation_time   : 2024-12-04T13:00:01.000000Z
  Duration: 00:38:31.55, start: 0.000000, bitrate: 961 kb/s
  Stream #0:0[0x2](eng): Video: h264 (Constrained Baseline) (avc1 / 0x31637661), yuv420p(progressive), 1920x1080, 881 kb/s, 16 fps, 16 tbr, 10k tbn (default)
      Metadata:
        creation_time   : 2024-12-04T13:00:01.000000Z
        vendor_id       : [0][0][0][0]
  Stream #0:1[0x1](eng): Audio: aac (LC) (mp4a / 0x6134706D), 16000 Hz, mono, fltp, 77 kb/s (default)
      Metadata:
        creation_time   : 2024-12-04T13:00:01.000000Z
        vendor_id       : [0][0][0][0]
Stream mapping:
  Stream #0:1 -> #0:0 (aac (native) -> pcm_s16le (native))
Press [q] to stop, [?] for help
Output #0, wav, to 'foo.temp.wav':
  Metadata:
    major_brand     : isom
    minor_version   : 512
    compatible_brands: isomiso2
    ISFT            : Lavf61.7.100
  Stream #0:0(eng): Audio: pcm_s16le ([1][0][0][0] / 0x0001), 16000 Hz, mono, s16, 256 kb/s (default)
      Metadata:
        creation_time   : 2024-12-04T13:00:01.000000Z
        vendor_id       : [0][0][0][0]
        encoder         : Lavc61.19.101 pcm_s16le
[out#0/wav @ 0x56097a7b8840] video:0KiB audio:72236KiB subtitle:0KiB other streams:0KiB global headers:0KiB muxing overhead: 0.000105%
size=   72236KiB time=00:38:31.55 bitrate= 256.0kbits/s speed=4.28e+03x    
[2/3] Transcribing...
/home/mpetrick/repos/codingWithGPT/videoTranscriptionLocally/.venv/lib/python3.13/site-packages/whisper/transcribe.py:132: UserWarning: FP16 is not supported on CPU; using FP32 instead
  warnings.warn("FP16 is not supported on CPU; using FP32 instead")
[3/3] Saving transcript...

Transcript saved to: foo.mp4.transcript.md
python main.py foo.mp4  1429.78s user 6.50s system 588% cpu 4:03.93 total
    ~/r/codingWithGPT/videoTranscriptionLocally    master ⇡1 *6 !2 ?1  wc foo.mp4.transcript.md                                                                ✔  4m 4s   videoTranscriptionLocally  
    0  6564 41746 foo.mp4.transcript.md
    ~/r/codingWithGPT/videoTranscriptionLocally    master ⇡1 *6 !2 ?

```
