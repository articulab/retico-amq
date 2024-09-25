from functools import partial
import json
import threading
import time
import keyboard
import retico_core
import base64

from amq import AMQReader, AMQWriter, AMQBridge


class GestureIU(retico_core.IncrementalUnit):
    """"""

    @staticmethod
    def type():
        return "Gesture IU"

    def __init__(
        self,
        creator=None,
        iuid=0,
        previous_iu=None,
        grounded_in=None,
        animations=None,
        emotions=None,
        eye_gazes=None,
        left_hand_movements=None,
        right_hand_movements=None,
        head_movements=None,
        **kwargs,
    ):
        super().__init__(
            creator=creator,
            iuid=iuid,
            previous_iu=previous_iu,
            grounded_in=grounded_in,
            payload=None,
        )
        self.animations = animations
        self.emotions = emotions
        self.eye_gazes = eye_gazes
        self.left_hand_movements = left_hand_movements
        self.right_hand_movements = right_hand_movements
        self.head_movements = head_movements


class TestTextIUProducingModule(retico_core.abstract.AbstractProducingModule):

    @staticmethod
    def name():
        return "AMQReader Module"

    @staticmethod
    def description():
        return "A Module providing reading onto a ActiveMQ bus"

    @staticmethod
    def output_iu():
        return retico_core.text.TextIU

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tts_thread_active = False
        self.cpt = 0

    def prepare_run(self):
        super().prepare_run()
        self._tts_thread_active = True
        threading.Thread(target=self.run_process).start()

    def shutdown(self):
        """
        overrides AbstractModule : https://github.com/retico-team/retico-core/blob/main/retico_core/abstract.py#L819
        """
        super().shutdown()
        self._tts_thread_active = False

    def process_update(self, update_message):
        pass

    def run_process(self):
        while self._tts_thread_active:
            um = retico_core.UpdateMessage()
            iu = self.create_iu(text=f"this is a test message : {self.cpt}")
            self.cpt += 1
            um.add_iu(iu, retico_core.UpdateType.ADD)
            self.append(um)
            self.terminal_logger.info(
                "TestProducingModule creates a retico IU",
                text=iu.text,
            )
            time.sleep(10)


class TestAudioIUProducingModule(retico_core.abstract.AbstractProducingModule):

    @staticmethod
    def name():
        return "AMQReader Module"

    @staticmethod
    def description():
        return "A Module providing reading onto a ActiveMQ bus"

    @staticmethod
    def output_iu():
        return retico_core.audio.AudioIU

    def __init__(self, frame_length=0.02, rate=16000, sample_width=2, **kwargs):
        """
        Initialize the TestAudioIUProducingModule Module.

        Args:
            frame_length (float): The length of one frame (i.e., IU) in seconds
            rate (int): The frame rate of the audio
            sample_width (int): The width of a single sample of audio in bytes.
        """
        super().__init__(**kwargs)
        self.frame_length = frame_length
        self.chunk_size = round(rate * frame_length)
        self.rate = rate
        self.sample_width = sample_width
        self._tts_thread_active = False

    def prepare_run(self):
        super().prepare_run()
        self._tts_thread_active = True
        threading.Thread(target=self.run_process).start()

    def shutdown(self):
        """
        overrides AbstractModule : https://github.com/retico-team/retico-core/blob/main/retico_core/abstract.py#L819
        """
        super().shutdown()
        self._tts_thread_active = False

    def process_update(self, update_message):
        pass

    def run_process(self):
        # The module doesn't send enough audio to have a continous signal, it's just a test module
        # If you want the module to send continous signal, change the time.sleep to time.sleep(self.frame_length), or the frame_length to 10
        while self._tts_thread_active:
            um = retico_core.UpdateMessage()
            audio_chunk = b"\x00" * self.sample_width * self.chunk_size
            # audio_encoded = base64.b64encode(audio_chunk)
            audio_chunk_str = str(audio_chunk)
            iu = self.create_iu(
                raw_audio=audio_chunk_str,
                nframes=self.frame_length,
                rate=self.rate,
                sample_width=self.sample_width,
            )
            um.add_iu(iu, retico_core.UpdateType.ADD)
            self.append(um)
            self.terminal_logger.info(
                "TestProducingModule creates a retico IU",
                audio_first_bytes=iu.payload[:20],
            )
            time.sleep(10)
            # time.sleep(self.frame_length)


class TestGestureIUProducingModule(retico_core.abstract.AbstractProducingModule):

    @staticmethod
    def name():
        return "AMQReader Module"

    @staticmethod
    def description():
        return "A Module providing reading onto a ActiveMQ bus"

    @staticmethod
    def output_iu():
        return GestureIU

    def __init__(self, **kwargs):
        """
        Initialize the TestAudioIUProducingModule Module.

        Args:
            frame_length (float): The length of one frame (i.e., IU) in seconds
            rate (int): The frame rate of the audio
            sample_width (int): The width of a single sample of audio in bytes.
        """
        super().__init__(**kwargs)
        self._tts_thread_active = False

    def prepare_run(self):
        super().prepare_run()
        self._tts_thread_active = True
        threading.Thread(target=self.run_process).start()

    def shutdown(self):
        """
        overrides AbstractModule : https://github.com/retico-team/retico-core/blob/main/retico_core/abstract.py#L819
        """
        super().shutdown()
        self._tts_thread_active = False

    def process_update(self, update_message):
        pass

    def run_process(self):
        # The module doesn't send enough audio to have a continous signal, it's just a test module
        # If you want the module to send continous signal, change the time.sleep to time.sleep(self.frame_length), or the frame_length to 10
        while self._tts_thread_active:
            animations = [
                {"name": "waiving", "duration": 1, "delay": 0},
                {"name": "pointing", "duration": 1, "delay": 1},
            ]
            emotions = [
                {"name": "happy", "duration": 1, "delay": 0},
                {"name": "sad", "duration": 1, "delay": 1},
            ]
            eye_gazes = [
                {"x": 30, "y": 50, "duration": 1, "delay": 0},
                {"x": 0, "y": 0, "duration": 1, "delay": 1},
            ]
            left_hand_movements = [{"x": 100, "y": 30, "duration": 1, "delay": 1}]
            right_hand_movements = [
                {"x": 30, "y": 0, "duration": 0.5, "delay": 0},
                {"x": 0, "y": 50, "duration": 1, "delay": 0.5},
            ]
            head_movements = [{"x": 20, "y": 20, "duration": 2, "delay": 0}]
            iu = self.create_iu(
                animations=animations,
                emotions=emotions,
                eye_gazes=eye_gazes,
                left_hand_movements=left_hand_movements,
                right_hand_movements=right_hand_movements,
                head_movements=head_movements,
            )

            um = retico_core.UpdateMessage()
            um.add_iu(iu, retico_core.UpdateType.ADD)
            self.append(um)
            self.terminal_logger.info(
                "TestProducingModule creates a retico IU",
                # audio_first_bytes=iu.payload[:20],
            )
            time.sleep(10)
            # time.sleep(self.frame_length)


def callback_fun(update_msg):
    for iu, ut in update_msg:
        print(iu)


def callback_text_AMQReader(update_msg, module=None):
    for iu, ut in update_msg:
        module.terminal_logger.info(
            "CallbackModule receives a retico IU from AMQReader", text=iu.payload
        )


def callback_audio_AMQReader(update_msg, module=None):
    for iu, ut in update_msg:
        module.terminal_logger.info(
            "CallbackModule receives a retico IU from AMQReader",
            audio_first_bytes=iu.payload[:20],
            # iu=iu,
        )


def callback_gesture_AMQReader(update_msg, module=None):
    for iu, ut in update_msg:
        module.terminal_logger.info(
            "CallbackModule receives a retico IU from AMQReader",
        )


def test_exchange_through_activeMQ(type):
    # Parameters
    ip = "localhost"
    port = "61613"
    headers = {"header_key_test": "header_value_test"}
    destination = "/topic/AMQ_test"
    printing = True

    # Modules
    bridge = AMQBridge(headers, destination)

    aw = AMQWriter(ip=ip, port=port, print=printing)

    ar = AMQReader(ip=ip, port=port, print=printing)

    cback = retico_core.debug.CallbackModule(callback=callback_fun)

    # network
    bridge.subscribe(aw)
    aw.subscribe(ar)  # just so that they are on the same network
    ar.subscribe(cback)

    # additions depending on the tested IU type
    if type == "text":
        producer = TestTextIUProducingModule()
        producer.subscribe(bridge)
        ar.add(destination=destination, target_iu_type=retico_core.text.TextIU)
        cback.callback = partial(callback_text_AMQReader, module=cback)
    elif type == "audio":
        producer = TestAudioIUProducingModule()
        producer.subscribe(bridge)

        ar.add(destination=destination, target_iu_type=retico_core.audio.AudioIU)
        cback.callback = partial(callback_audio_AMQReader, module=cback)
    elif type == "gesture":
        producer = TestGestureIUProducingModule()
        producer.subscribe(bridge)
        ar.add(destination=destination, target_iu_type=GestureIU)
        cback.callback = partial(callback_gesture_AMQReader, module=cback)

    # FILTERS FOR LOGGING SYSTEM
    retico_core.network.LOG_FILTERS = [
        partial(
            retico_core.log_utils.filter_value_not_in_list,
            key="event",
            values=[
                "error",
                "TestProducingModule creates a retico IU",
                "AMQWriter sends a message to ActiveMQ",
                "AMQReader receives a message from ActiveMQ",
                "AMQReader creates new iu",
                "CallbackModule receives a retico IU from AMQReader",
            ],
        ),
    ]

    # running system
    try:
        retico_core.network.run(producer)
        print("test running until ENTER key is pressed")
        # keyboard.wait("q")
        input()
        retico_core.network.stop(producer)
    except Exception as err:
        print(f"Unexpected {err}")
        print(err.with_traceback())
        retico_core.network.stop(producer)


if __name__ == "__main__":
    # test_exchange_through_activeMQ("text")
    # test_exchange_through_activeMQ("audio")
    test_exchange_through_activeMQ("gesture")
