import time
import requests
import math
from lxml.html import fromstring


def catch_danmu(video_id):

    r = requests.get(f'https://v.douyu.com/show/{video_id}')
    tree = fromstring(r.content)
    title = tree.findtext('.//title')
    txt = open("%s.txt" % title, 'w')
    print(title)
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
    url = f'https://v.douyu.com/wgapi/vod/center/getBarrageListByPage?vid={video_id}&forward=0&offset=-1'
    while True:
        res = requests.get(url=url, headers=headers).json()
        next_json = res['data']['pre']
        if next_json == -1:
            break
        for i in res['data']['list']:
            # print(i)
            msg = i["ctt"]
            time = i["tl"]/1000/60
            sep = math.modf(time)
            minute = int(sep[1])
            second = int(sep[0]*60)
            # print(msg, minute, second)
            # print("\n")
            try:
                if second < 10:
                    txt.write("%d:0%d&&&%s\n" % (minute, second, msg))
                else:
                    txt.write("%d:%d&&&%s\n" % (minute, second, msg))
            except:
                continue
                # print("一条弹幕截取未成功")
        url = f'https://v.douyu.com/wgapi/vod/center/getBarrageListByPage?vid={video_id}&forward=0&offset={next_json}'
    txt.close()
    return title


def gen_barrage_positions(gap, lines):
    col = [186.0, 83.0, 289.0]
    row_start = 15.0
    barrage_positions = []

    for j in range(lines):
        for i in col:
            barrage_positions.append((i, row_start + j * gap))
    return barrage_positions


class DouYu_barrage_generate:

    def __init__(self):
        self.barrage_list = []
        self.barrage_default = ['\ufeff[Script Info]\n', '; Script generated by Aegisub 3.2.2\n', '; http://www.aegisub.org/\n', 'Synch Point: 1\n', 'ScriptType: v4.00+\n', 'PlayResX: 0\n', 'PlayResY: 0\n', 'WrapStyle: 0\n', 'ScaledBorderAndShadow: no\n', '\n', '[Aegisub Project Garbage]\n', 'Last Style Storage: Default\n', 'Video Zoom Percent: 0.875000\n', 'Active Line: 6\n', 'Video Position: 352\n', '\n', '[V4+ Styles]\n',
                                'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n', 'Style: Default,微软雅黑,14,&H00FFFFFF,&HF0000000,&H00000000,&H32000000,0,0,0,0,100,100,0,0,1,2,1,2,5,5,2,134\n', '\n', '[Events]\n', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n']

        # self.barrage_positions = [(186.0, 15.0), (83.0, 15.0), (289.0, 15.0),
        #                           (186.0, 25.0), (83.0, 25.0), (289.0, 25.0),
        #                           (186.0, 35.0), (83.0, 35.0), (289.0, 35.0),
        #                           (186.0, 45.0), (83.0, 45.0), (289.0, 45.0),
        #                           (186.0, 55.0), (83.0, 55.0), (289.0, 55.0),
        #                           (186.0, 65.0), (83.0, 65.0), (289.0, 65.0),
        #                           (186.0, 75.0), (83.0, 75.0), (289.0, 75.0),
        #                           (186.0, 85.0), (83.0, 85.0), (289.0, 85.0),
        #                           (186.0, 95.0), (83.0, 95.0), (289.0, 95.0),
        #                           (186.0, 105.0), (83.0, 105.0), (289.0, 105.0),
        #                           (186.0, 115.0), (83.0, 115.0), (289.0, 115.0),
        #                           (186.0, 125.0), (83.0, 125.0), (289.0, 125.0),
        #                           (186.0, 135.0), (83.0, 135.0), (289.0, 135.0),
        #                           (186.0, 145.0), (83.0, 145.0), (289.0, 145.0),
        #                           (186.0, 155.0), (83.0, 155.0), (289.0, 155.0),
        #                           (186.0, 165.0), (83.0, 165.0), (289.0, 165.0),
        #                           (186.0, 175.0), (83.0, 175.0), (289.0, 175.0),
        #                           (186.0, 185.0), (83.0, 185.0), (289.0, 185.0)]
        self.barrage_positions = gen_barrage_positions(14, 18)

        self.barrage_gates = [1]*len(self.barrage_positions)
        self.barrage_time = [None]*len(self.barrage_positions)
        self.barrage_text = [None]*len(self.barrage_positions)

    def load_barrage(self, filename):
        f = open(filename+".txt", mode='r')
        for line in f.readlines():
            line = line.strip()
            if "&&&" in line:
                each_barrage = line.split("&&&")
                self.barrage_list.append(each_barrage)

        def take_first(elem):
            parts = elem[0].split(':')
            minute = int(parts[0])
            second = int(parts[1])
            return minute*60+second
        self.barrage_list.reverse()
        self.barrage_list.sort(key=take_first)
        f.close()

    def generate_each_barrage(self, barrage, stay_time):
        index = None

        barrage_time_part = barrage[0].split(':')
        hour = 0
        minute = int(barrage_time_part[0])
        second = int(barrage_time_part[1])
        if minute // 60 != 0:
            hour = minute // 60
            minute = minute % 60

        count_time_as_second = hour*3600 + minute*60 + second
        barrage_content = barrage[1]
        # print(count_time_as_second)

        for i in range(len(self.barrage_time)):
            if self.barrage_time[i] != None and count_time_as_second >= self.barrage_time[i] + stay_time:
                self.barrage_time[i] = None
                self.barrage_gates[i] = 1
                self.barrage_text[i] = None

        try:
            index = self.barrage_gates.index(1)
            if len(barrage_content) > 15:
                indices = [i for i, x in enumerate(
                    self.barrage_gates) if x == 1]
                for i in indices:
                    if i % 3 == 0:
                        if self.barrage_gates[i+1] == 1 and self.barrage_gates[i+2] == 1:
                            index = i
                            self.barrage_gates[i+1] = 0
                            self.barrage_gates[i+2] = 0
                            self.barrage_time[i+1] = count_time_as_second
                            self.barrage_time[i+2] = count_time_as_second
                            break
                    elif i % 3 == 1:
                        if self.barrage_gates[i-1] == 1:
                            index = i
                            self.barrage_gates[i-1] = 0
                            self.barrage_time[i-1] = count_time_as_second
                            break
                    elif i % 3 == 2:
                        if self.barrage_gates[i-2] == 1:
                            index = i
                            self.barrage_gates[i-2] = 0
                            self.barrage_time[i-2] = count_time_as_second
                            break

        except:
            index = self.barrage_time.index(min(self.barrage_time))
        position = self.barrage_positions[index]
        self.barrage_gates[index] = 0

        barrage_start_time = str(hour)+":"+str(minute)+":"+str(second)+".00"
        barrage_end_time = str(hour)+":"+str(minute) + \
            ":"+str(second+stay_time)+".00"
        if (second + stay_time) > 60:
            left = second + stay_time - 60
            barrage_end_time = str(hour)+":" + \
                str(minute + 1)+":"+str(left)+".00"
        barrage_position = "{\pos("+str(position[0])+","+str(position[1])+")}"

        final_barrage = "Dialogue: 0,"+str(barrage_start_time)+","+str(barrage_end_time) +\
            ",*Default,NTP,0,0,0,," + \
            str(barrage_position)+str(barrage_content)+"\n"

        self.barrage_time[index] = count_time_as_second

        # print(self.barrage_time)
        return final_barrage

    def generate_barrage(self, filename, stay_time):

        f = open(filename+".ass", mode='w', encoding='UTF-8')
        f.writelines(self.barrage_default)
        for barrage in self.barrage_list:
            f.write(self.generate_each_barrage(barrage, stay_time))
        f.close()

    def run(self, filename, stay_time):
        self.load_barrage(filename)
        self.generate_barrage(filename, stay_time)
        print("完成")


if __name__ == "__main__":
    flag = True
    stay_time = 5
    while flag:
        t = time.time()
        v_id = input("输入对应视频的id：")
        # title  = "zard1991_【2020-12-10 21点场】zard1991：zard1991_斗鱼视频 - 最6的弹幕视频网站"
        title = catch_danmu(v_id)
        douYu_barrage_generate = DouYu_barrage_generate()
        douYu_barrage_generate.run(title, stay_time)
        time_cost = time.time() - t
        print("花费时间为%.2f秒。" % time_cost)
        print("完成，现在开始下一个！\n")
