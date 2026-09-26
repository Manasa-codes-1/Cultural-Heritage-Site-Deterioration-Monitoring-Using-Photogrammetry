import visdom
import numpy as np
import time
import torch
import os
import matplotlib.pyplot as plt
from collections import defaultdict


class Visualizer(object):

    def __init__(self, env='default', **kwargs):
        self.env = env
        self.vis = visdom.Visdom(env=env, use_incoming_socket=False, **kwargs)
        self._vis_kwargs = kwargs

        self.index = {}
        self.log_text = {}

        self.plot_history = defaultdict(list)
        # 创建保存图像的文件夹
        self.save_path = 'log/plots'
        os.makedirs(self.save_path, exist_ok=True)

    def save_settings(self, save_path=None, save_log=False, save_img=False, save_plot=False):

        save_format = '{info}-{time}'.format(time=time.strftime("%Y-%m-%d %H:%M:%S"), info=self.env)
        self.save_path = os.path.join(save_path, save_format)

        if self.save_path and not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

        self.save_log = save_log

        if self.save_path and self.save_log:
            os.mkdir((os.path.join(self.save_path, 'logs')))

        self.save_img = save_img

        if self.save_path and self.save_img:
            os.mkdir((os.path.join(self.save_path, 'imgs')))
        self.save_plot = save_plot

        if self.save_path and self.save_plot:
            os.mkdir((os.path.join(self.save_path, 'plots')))

    def __getattr__(self, name):
        return getattr(self.vis, name)

    def reinit(self, env, **kwargs):
        self.vis = visdom.Visdom(env=env, **kwargs)

    def state_dict(self):
        return {
            'index': self.index,
            'log_text': self.log_text,
            '_vis_kwargs': self._vis_kwargs,
            'env': self.vis.env,
        }

    def load_state_dict(self, d):
        self.vis = visdom.Visdom(env=d.get('env', self.vis.env), use_incoming_socket=False, **d.get('_vis_kwargs'))
        self.log_text = d.get('log_text', {})
        self.index = d.get('index', {})

    def log(self, info, win='defalut'):

        """
        self.log({'loss':1,'lr':0.0001}, 'loss')
        self.log('start load dataset ...', 'info')
        self.log('acc TP:%f, FP:%f ....'%(a,b), 'acc')
        """

        if self.log_text.get(win, None) is not None:
            flag = True
        else:
            flag = False

        self.log_text[win] = ('[{time}] {info}\n'.format(time=time.strftime("%Y-%m-%d %H:%M:%S"), info=info))
        self.vis.text(self.log_text[win], win, append=flag)

        # if self.save_log:
        #     with open(os.path.join(self.save_path, 'logs', '%s.txt'%win), 'a') as f:
        #         f.write('%s'%(self.log_text[win]))

    def log_many(self, d):
        '''
        d: dict{'loss':{'loss':1,'lr':0.0001},
                'info':'start load dataset ...'
                'acc':'acc TP:%f, FP:%f ....'%(a,b)}
        '''

        for k, v in d.items():
            self.log(v, k)

    def img(self, img, win='default', **kwargs):
        '''
        only tensor or numpy
        self.img(t.Tensor(64,64))
        self.img(t.Tensor(3,64,64))
        self.img('input_imgs',t.Tensor(100,1,64,64))
        self.img('input_imgs',t.Tensor(100,3,64,64),nrows=10)
        '''

        if torch.is_tensor(img):
            img = img.detach().cpu().numpy()
        self.vis.images(img, win=win, opts=dict(title=win), **kwargs)

    def img_many(self, d):
        for k, v in d.items():
            self.img(v, k)

    def plot(self, y, win='loss', **kwargs):
        '''
        :param y: float or tensor or anything convertible to float
        :param win: window name
        '''
        x = self.index.get(win, 0)

        try:
            # 强制转换为 float，如果失败就会被 except 捕获
            y = float(y)

            # 检查是否是 NaN
            if np.isnan(y):
                print(f'[Visdom Warning] y is NaN at win="{win}", skip plotting...')
                return

            self.vis.line(Y=np.array([y]), X=np.array([x]), win=win,
                        opts=dict(title=win), update=None if x == 0 else 'append', **kwargs)
            self.index[win] = x + 1

        except Exception as e:
            print(f'[Visdom Error] Failed to plot {win} with value "{y}": {e}')



    def plot_many(self, d):
        """
        plot multi values
        @params d: dict (name,value) i.e. ('loss',0.11)
        """
        for key, val in d.items():
            if val is not None:
                self.plot(y=val, win=key)  # 原有 visdom 可视化
                # 新增：保存为图像
                self.plot_history[key].append(val)
                # 保存为本地 PNG 图像
                if len(self.plot_history[key]) >= 2:
                    plt.figure()
                    plt.plot(self.plot_history[key])
                    plt.title(key)
                    plt.xlabel('Iteration')
                    plt.ylabel(key)
                    plt.grid(True)
                    plt.savefig(os.path.join(self.save_path, f'{key}.svg'))
                    plt.close()
