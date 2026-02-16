
from PyQt5.QtMultimedia import QSound, QSoundEffect
from PyQt5.QtCore import QUrl, QTimer
#import threading, queue

class SoundEffect(QSoundEffect):

    def __init__(self,name,volume=1):
        QSoundEffect.__init__(self)
        self.timer = None
        wav_file = QUrl.fromLocalFile("resources/"+name+'.wav')
        self.setSource(wav_file)
        self.setVolume(volume)
        self.lowSoundEffect = QSoundEffect()
        self.lowSoundEffect.setSource(wav_file)
        self.lowSoundEffect.setVolume(volume/8)

    def play_once(self, volume=None, is_low_volume=False):
        # if self.isMuted():
        #     self.setMuted(False)
        #if not self.isPlaying():
        if is_low_volume:
            self.lowSoundEffect.play_once()
        else:
            if volume is not None:
                #old_volume = self.volume()
                if volume < 0.005:
                    return
                self.setVolume(volume)
            self.play()

    def play_long(self, duration_in_ms=50):
        if self.timer is None or not self.isPlaying():
            if self.isMuted():
                self.setMuted(False)
            self.play_once()
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self._stop)
        else:
            self.timer.stop()
        self.timer.start(duration_in_ms)

    def _stop(self):
        self.timer = None
        self.setMuted(True)


class Sound:

    @staticmethod
    def sound_effect(name,volume=None):
        se = QSoundEffect()
        se.setSource(QUrl.fromLocalFile(name+'.wav'))
        if volume is not None:
            se.setVolume(volume)
        return se

    @staticmethod
    def init():
        Sound.explosion1 = SoundEffect('explosion1')
        Sound.explosion2 = SoundEffect('435413__v-ktor__explosion12')
        Sound.hit1 = SoundEffect('hit1', 0.1)
        Sound.hit2 = SoundEffect('hit2', 0.1)
        Sound.hit3 = SoundEffect('hit3', 0.1)
        #Sound.start1 = SoundEffect('start1')
        Sound.thrust1 = SoundEffect('thrust1', 0.05)
        #Sound.thrust2 = SoundEffect('thrust2', 0.05)
        #Sound.thrust3 = SoundEffect('thrust3', 0.05)
        Sound.thrust4 = SoundEffect('824193__chungus43a__emd-567-engine-notch-4-synth-recreation', 0.05)
        Sound.thrust5 = SoundEffect('222804__gthall__engine-idle', 0.20)
        Sound.shoot1 = SoundEffect('shoot1', 0.15)
        Sound.shoot2 = SoundEffect('shoot2', 0.15)
        Sound.shoot3 = SoundEffect('shoot3', 0.15)
        # Sound.water1 = SoundEffect('water1', 0.5)
        # Sound.water2 = SoundEffect('water2', 0.2)
        # Sound.water3 = SoundEffect('water3')
        # Sound.water1b = SoundEffect('water1', 0.1)
        # Sound.water3b = SoundEffect('water3', 0.04)
        Sound.change_scene = SoundEffect('change_scene', 0.25)
        Sound.change_scene.play_once()
        '''
        for s in Sound.__dict__.values():
            if isinstance(s,QSound):
                s.play()
                s.stop()
        '''

#Sound.init()
#
# def sound_thread_function():
#     while True:
#         #message_queue.get().stop()
#         (func, obj) = message_queue.get()
#         func(obj)
#
# message_queue = queue.Queue()
# sound_tread = threading.Thread(target=sound_thread_function, daemon=True)
# sound_tread.start()
#

