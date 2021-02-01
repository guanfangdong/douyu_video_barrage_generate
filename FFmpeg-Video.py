# coding=utf-8
import numpy as np
import os
import wave
import subprocess
import pylab as pl
import numpy as np
import datetime
import math
import json
import pprint
from moviepy.editor import *
from natsort import natsorted
import librosa
from pydub import AudioSegment
from moviepy.editor import AudioFileClip
import re
import time
import threading
import random
import struct
import shutil


# method 1: absSum
def calVolume(waveData, frameSize, overLap):
    wlen = len(waveData)
    step = frameSize - overLap
    frameNum = int(math.ceil(wlen*1.0/step))
    volume = np.zeros((frameNum, 1))
    for i in range(frameNum):
        curFrame = waveData[np.arange(i*step, min(i*step+frameSize, wlen))]
        curFrame = curFrame - np.median(curFrame)  # zero-justified
        volume[i] = np.sum(np.abs(curFrame))
    return volume

# method 2: 10 times log10 of square sum


def calVolumeDB(waveData, frameSize, overLap):
    wlen = len(waveData)
    step = frameSize - overLap
    frameNum = int(math.ceil(wlen*1.0/step))
    volume = np.zeros((frameNum, 1))
    for i in range(frameNum):
        curFrame = waveData[np.arange(i*step, min(i*step+frameSize, wlen))]
        curFrame = curFrame - np.mean(curFrame)  # zero-justified
        volume[i] = 10*np.log10(np.sum(curFrame*curFrame))
    return volume


def get_loud_times(wav_path, threshold=500, time_constant=0.5):
    '''Work out which parts of a WAV file are loud.
        - threshold: the variance threshold that is considered loud
        - time_constant: the approximate reaction time in seconds'''

    wav = wave.open(wav_path, 'r')
    length = wav.getnframes()
    samplerate = wav.getframerate()

    print(wav.getsampwidth())
    assert wav.getnchannels() == 1, 'wav must be mono'
    assert wav.getsampwidth() == 2, 'wav must be 16-bit'

    # Our result will be a list of (time, is_loud) giving the times when
    # when the audio switches from loud to quiet and back.
    is_loud = False
    result = [(0., is_loud)]

    number_frames = int(samplerate * time_constant)
    loop_number = int(length // number_frames)

    # The following values track the mean and variance of the signal.
    # When the variance is large, the audio is loud.
    # mean = 0
    # variance = 0

    # If alpha is small, mean and variance change slower but are less noisy.
    # alpha = 1 / (time_constant * float(samplerate))

    return_list = []
    for i in range(loop_number):
        # sample_time = float(i) / samplerate

        total = 0
        for j in range(number_frames):
            sample = struct.unpack('<h', wav.readframes(1))[0]
            sample = abs(sample)
            total += sample

        ave = total / number_frames
        if ave > threshold:
            sample_time = i * time_constant
            # sample_time = time.strftime('%H:%M:%S', time.gmtime(sample_time))
            return_list.append(sample_time)

    return return_list, time_constant


def play_sentence(wav_path):
    loud_times, time_constant = get_loud_times(wav_path)
    all_periods = []
    flag = 1
    continue_num = 0
    for step, current in enumerate(loud_times):
        print(flag)
        if continue_num == 0:
            flag = 1
        if flag == 1:
            try:
                interval_length = 2
                idx = step
                while current + interval_length > loud_times[idx + 1]:
                    interval_length += time_constant
                    continue_num += 1
                    idx += 1
                end = loud_times[idx]
                all_periods.append((current, end))
                flag = 0
            except:
                print("finished")
        elif flag == 0:
            continue_num -= 1
            if continue_num == 0:
                continue_num = 0
                flag = 1
            continue

    print(all_periods)
    return all_periods


class FFmpeg:

    def __init__(self, editvdo, addlogo=None, addmusic=None,
                 addvdohead=None, addvdotail=None):
        self.editvdo = editvdo
        self.addlogo = addlogo
        self.addmusic = addmusic
        self.addvdohead = addvdohead
        self.addvdotail = addvdotail
        self.vdo_time, self.vdo_width, self.vdo_height, self.attr_dict = self.get_attr()
        self.editvdo_path = os.path.dirname(editvdo)
        self.editvdo_name = os.path.basename(editvdo)

    def get_attr(self):
        """
        获取视频属性参数
        :return:
        """
        strcmd = r'ffprobe -print_format json -show_streams -i "{}"'.format(
            self.editvdo)
        status, output = subprocess.getstatusoutput(strcmd)
        agrs = eval(
            re.search('{.*}', output, re.S).group().replace("\n", "").replace(" ", ''))
        streams = agrs.get('streams', [])
        agrs_dict = dict()
        [agrs_dict.update(x) for x in streams]
        vdo_time = agrs_dict.get('duration')
        vdo_width = agrs_dict.get('width')
        vdo_height = agrs_dict.get('height')
        attr = (vdo_time, vdo_width, vdo_height, agrs_dict)
        return attr

    def edit_head(self, start_time, end_time, deposit=None):
        """
        截取指定长度视频
        :param second: 去除开始的多少秒
        :param deposit: 另存为文件
        :return: True/Flase
        """
        if None == deposit:
            deposit = self.editvdo_path+'/'+'edit_head'+self.editvdo_name
        save_path = self.editvdo_path + '/%s' % deposit
        start = time.strftime('%H:%M:%S', time.gmtime(start_time))
        end = time.strftime('%H:%M:%S', time.gmtime(end_time))

        print(start)
        strcmd = 'ffmpeg -i "{}" -vcodec copy -acodec copy -ss {} -t {} -y -async 1 "{}"'.format(
            self.editvdo, start, end, save_path)
        print(strcmd)
        result = subprocess.run(
            args=strcmd, stdout=subprocess.PIPE, shell=True)
        # if os.path.exists(deposit):
        #     os.remove(self.editvdo)
        #     os.rename(deposit, self.editvdo)
        #     return True
        # else:
        #     return False

    def edit_logo(self, deposit=None):
        """
        添加水印
        :param deposit:添加水印后另存为路径，为空则覆盖
        :return: True/False
        """
        if None == deposit:
            deposit = self.editvdo_path+'/'+'edit_logo'+self.editvdo_name
        strcmd = r'ffmpeg -i "{}" -vf "movie=\'{}\' [watermark];[in] ' \
                 r'[watermark] overlay=main_w-overlay_w-10:10 [out]"  "{}"'.format(
                     self.editvdo, self.addlogo, deposit)
        result = subprocess.run(
            args=strcmd, stdout=subprocess.PIPE, shell=True)
        if os.path.exists(deposit):
            os.remove(self.editvdo)
            os.rename(deposit, self.editvdo)
            return True
        else:
            return False

    def edit_music(self, deposit=None):
        if None == deposit:
            deposit = self.editvdo_path+'/'+'edit_music'+self.editvdo_name
        strcmd = r'ffmpeg -y -i "{}" -i "{}" -filter_complex "[0:a] ' \
                 r'pan=stereo|c0=1*c0|c1=1*c1 [a1], [1:a] ' \
                 r'pan=stereo|c0=1*c0|c1=1*c1 [a2],[a1][a2]amix=duration=first,' \
                 r'pan=stereo|c0<c0+c1|c1<c2+c3,pan=mono|c0=c0+c1[a]" ' \
                 r'-map "[a]" -map 0:v -c:v libx264 -c:a aac ' \
                 r'-strict -2 -ac 2 "{}"'.format(self.editvdo,
                                                 self.addmusic, deposit)
        result = subprocess.run(
            args=strcmd, stdout=subprocess.PIPE, shell=True)
        if os.path.exists(deposit):
            os.remove(self.editvdo)
            os.rename(deposit, self.editvdo)
            return True
        else:
            return False

    def edit_rate(self, rete=30, deposit=None):
        """
        改变帧率
        :param rete: 修改大小帧率
        :param deposit: 修改后保存路径
        :return:
        """
        if None == deposit:
            deposit = self.editvdo_path+'/'+'edit_music'+self.editvdo_name
        strcmd = r'ffmpeg -i "{}" -r {} "{}"' % (self.editvdo, rete, deposit)
        result = subprocess.run(
            args=strcmd, stdout=subprocess.PIPE, shell=True)
        if os.path.exists(deposit):
            os.remove(self.editvdo)
            os.rename(deposit, self.editvdo)
            return True
        else:
            return False

    def edit_power(self, power='1280x720', deposit=None):
        """
        修改分辨率
        :param power: 分辨率
        :param deposit: 修改后保存路径，为空则覆盖
        :return:
        """
        if None == deposit:
            deposit = self.editvdo_path+'/'+'edit_power'+self.editvdo_name
        strcmd = r'ffmpeg -i "{}" -s {} "{}"'.format(
            self.editvdo, power, deposit)
        result = subprocess.run(
            args=strcmd, stdout=subprocess.PIPE, shell=True)
        if os.path.exists(deposit):
            os.remove(self.editvdo)
            os.rename(deposit, self.editvdo)
            return True
        else:
            return False

    def rdit_marge(self, vdo_head, vdo_tail, deposit=None):
        if None == deposit:
            deposit = self.editvdo_path+'/'+'rdit_marge'+self.editvdo_name
        with open(self.editvdo_path+'/'+'rdit_marge.txt', 'w', encoding='utf-8') as f:
            f.write("file '{}' \nfile '{}' \nfile '{}'" .format(
                vdo_head, self.editvdo, vdo_tail))
        strcmd = r'ffmpeg -f concat -safe 0 -i "{}" -c copy "{}"'.format(
            self.editvdo_path + '/' + 'rdit_marge.txt', deposit)
        result = subprocess.run(
            args=strcmd, stdout=subprocess.PIPE, shell=True)
        if os.path.exists(deposit):
            os.remove(self.editvdo)
            os.rename(deposit, self.editvdo)
            return True
        else:
            return False



if __name__ == "__main__":
    current_path = os.path.dirname(os.path.realpath(__file__)) + "/"
    video_name = "1.ts"
    video_path = current_path + video_name
    sound_path = current_path + video_name.split(".")[0] + ".wav"

    my_audio_clip = AudioFileClip(video_path)
    # my_audio_clip.write_audiofile(sound_path)

    duration = int(my_audio_clip.duration)

    cmd_run = 'spleeter separate -p spleeter:2stems -o output %s -d %d' % (sound_path, duration)
    os.system(cmd_run)

    file_name = video_name.split(".")[0]

    output_path = current_path + "output/%s/" % file_name
    all_files = os.listdir(output_path)

    numbers = 0
    for i in all_files:
        if "vocals" in i:
            numbers += 1

    combine_list = []
    for i in range(numbers):
        sound = AudioSegment.from_wav("%svocals_%d.wav" % (output_path, i))
        combine_list.append(sound)

    combined_sounds = combine_list[0]
    for i in combine_list[1:]:
        combined_sounds += i

    combined_sounds.export("joinedFile.wav", format="wav")

    sound = AudioSegment.from_wav("joinedFile.wav")
    sound = sound.set_channels(1)
    sound.export("joinedFile.wav", format="wav", parameters=["-ac","1","-ar","5000"])

    # test = FFmpeg(video_path)
    
    all_period = play_sentence("joinedFile.wav")[10:]
    num = 1
    for step, i in enumerate(all_period):
        if i[0] == i[1]:
            continue
        start = i[0] - 1
        end = i[1] + 1
        # start = np.int(np.floor(start))
        # end = np.int(np.ceil(start))

        start_f = time.strftime('%H:%M:%S', time.gmtime(start))
        end_f = time.strftime('%H:%M:%S', time.gmtime(end))

        start_s = time.strftime('%H_%M_%S', time.gmtime(start))

        print(start, end)


        # period = end - start
        clip = VideoFileClip(video_path)
        result_clip = clip.subclip(start_f,end_f)
        # result_clip.write_videofile("%d.mp4" % (current_path, num))
        result_clip.write_videofile("%soutput/%d_%s.mp4" % (current_path, num, start_s))


        # test.edit_head(start, period, "output/%d.mp4" % num)
        num += 1


    # L =[]

    # for root, dirs, files in os.walk("/path/to/the/files"):

    #     #files.sort()
    #     files = natsorted(files)
    #     for file in files:
    #         if os.path.splitext(file)[1] == '.mp4':
    #             filePath = os.path.join(root, file)
    #             video = VideoFileClip(filePath)
    #             L.append(video)

    # final_clip = concatenate_videoclips(L)
    # final_clip.to_videofile("output.mp4", fps=24, remove_temp=False)
    # test = FFmpeg(video_path)
    # test.edit_head(7100, 30, "111")
