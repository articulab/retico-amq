from functools import partial
import json
import threading
import time
import traceback
import keyboard
import retico_core
import base64

import retico_amq
from retico_amq.amq import AMQReader, AMQWriter, AMQBridge
from retico_core.log_utils import log_exception


class TestTextIUProducingModule(retico_core.abstract.AbstractProducingModule):

    @staticmethod
    def name():
        return "TestTextIUProducing Module"

    @staticmethod
    def description():
        return "A Module producing TextIU each n seconds"

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
        super().shutdown()
        self._tts_thread_active = False

    def process_update(self, update_message):
        pass

    def run_process(self):
        while self._tts_thread_active:
            try:
                # hardcoded IU values just for the test
                iu = self.create_iu(text=f"this is a test message : {self.cpt}")

                um = retico_core.UpdateMessage()
                um.add_iu(iu, retico_core.UpdateType.ADD)
                self.append(um)
                self.terminal_logger.info(
                    "TestProducingModule creates a retico IU",
                    text=iu.text,
                )
                self.cpt += 1
                time.sleep(10)
            except Exception as e:
                log_exception(module=self, exception=e)


class TestAudioIUProducingModule(retico_core.abstract.AbstractProducingModule):

    @staticmethod
    def name():
        return "TestAudioIUProducing Module"

    @staticmethod
    def description():
        return "A Module producing AudioIU each n seconds"

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
        super().shutdown()
        self._tts_thread_active = False

    def process_update(self, update_message):
        pass

    def run_process(self):
        # The module doesn't send enough audio to have a continous signal, it's just a test module
        # If you want the module to send continous signal, change the time.sleep to time.sleep(self.frame_length), or the frame_length to 10
        while self._tts_thread_active:
            try:

                # hardcoded IU values just for the test
                audio_chunk = b"\x00" * self.sample_width * self.chunk_size
                # audio_encoded = base64.b64encode(audio_chunk)
                audio_chunk_str = str(audio_chunk)

                iu = self.create_iu(
                    raw_audio=audio_chunk_str,
                    nframes=self.frame_length,
                    rate=self.rate,
                    sample_width=self.sample_width,
                )

                um = retico_core.UpdateMessage()
                um.add_iu(iu, retico_core.UpdateType.ADD)
                self.append(um)
                self.terminal_logger.info(
                    "TestProducingModule creates a retico IU",
                    audio_first_bytes=iu.payload[:20],
                )
                time.sleep(10)
                # time.sleep(self.frame_length)
            except Exception as e:
                log_exception(module=self, exception=e)


class TextAlignedAudioIU(retico_core.audio.AudioIU):
    """AudioIU enhanced with information that aligns the AudioIU to the current written agent turn.

    Attributes:
        - grounded_word : the word corresponding to the audio.
        - turn_id (int) : The index of the dialogue's turn the IU is part of.
        - clause_id (int) : The index of the clause the IU is part of, in the current turn.
        - word_id (int) : The index of the word that corresponds to the end of the IU].
        - char_id (int) : The index of the last character from the grounded_word.
        - final (bool) : Wether the IU is an EOT.
    """

    @staticmethod
    def type():
        return "Text Aligned Audio IU"

    def __init__(
        self,
        creator=None,
        iuid=0,
        previous_iu=None,
        grounded_in=None,
        raw_audio=None,
        rate=None,
        nframes=None,
        sample_width=None,
        grounded_word=None,
        word_id=None,
        char_id=None,
        turn_id=None,
        clause_id=None,
        final=None,
        **kwargs,
    ):
        super().__init__(
            creator=creator,
            iuid=iuid,
            previous_iu=previous_iu,
            grounded_in=grounded_in,
            payload=raw_audio,
            raw_audio=raw_audio,
            rate=rate,
            nframes=nframes,
            sample_width=sample_width,
        )
        self.grounded_word = grounded_word
        self.word_id = word_id
        self.char_id = char_id
        self.turn_id = turn_id
        self.clause_id = clause_id
        self.final = final


class TestAudioTurnIUProducingModule(retico_core.abstract.AbstractProducingModule):

    @staticmethod
    def name():
        return "TestAudioTurnIUProducing Module"

    @staticmethod
    def description():
        return "A Module producing TextAlignedAudioIU each n seconds"

    @staticmethod
    def output_iu():
        return TextAlignedAudioIU

    def __init__(self, frame_length=0.02, rate=16000, sample_width=2, **kwargs):
        """
        Initialize the TestAudioTurnIUProducingModule Module.

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
        super().shutdown()
        self._tts_thread_active = False

    def process_update(self, update_message):
        pass

    def run_process(self):
        # The module doesn't send enough audio to have a continous signal, it's just a test module
        # If you want the module to send continous signal, change the time.sleep to time.sleep(self.frame_length), or the frame_length to 10
        while self._tts_thread_active:
            try:

                # hardcoded IU values just for the test
                audio_chunk = b"\x00" * self.sample_width * self.chunk_size
                # audio_encoded = base64.b64encode(audio_chunk)
                audio_chunk_str = str(audio_chunk)
                grounded_word = "test_grounded_word"
                word_id = 0
                char_id = 18
                turn_id = 0
                clause_id = 0
                final = False

                iu = self.create_iu(
                    raw_audio=audio_chunk_str,
                    nframes=self.frame_length,
                    rate=self.rate,
                    sample_width=self.sample_width,
                    grounded_word=grounded_word,
                    word_id=word_id,
                    char_id=char_id,
                    turn_id=turn_id,
                    clause_id=clause_id,
                    final=final,
                )

                um = retico_core.UpdateMessage()
                um.add_iu(iu, retico_core.UpdateType.ADD)
                self.append(um)
                self.terminal_logger.info(
                    "TestProducingModule creates a retico IU",
                    audio_first_bytes=iu.payload[:20],
                )
                time.sleep(10)
                # time.sleep(self.frame_length)
            except Exception as e:
                log_exception(module=self, exception=e)


class GestureIU(retico_core.IncrementalUnit):

    @staticmethod
    def type():
        return "Gesture IU"

    def __init__(
        self,
        creator=None,
        iuid=0,
        previous_iu=None,
        grounded_in=None,
        turnID=None,
        clauseID=None,
        interrupt=None,
        animations=None,
        blendshapes=None,
        gazes=None,
        left_hand_movements=None,
        right_hand_movements=None,
        lookAt=None,
        **kwargs,
    ):
        super().__init__(
            creator=creator,
            iuid=iuid,
            previous_iu=previous_iu,
            grounded_in=grounded_in,
            payload=None,
        )

        self.turnID = turnID
        self.clauseID = clauseID
        self.interrupt = interrupt
        self.animations = animations
        self.blendshapes = blendshapes
        self.gazes = gazes
        self.left_hand_movements = left_hand_movements
        self.right_hand_movements = right_hand_movements
        self.lookAt = lookAt


class TestGestureIUProducingModule(retico_core.abstract.AbstractProducingModule):

    @staticmethod
    def name():
        return "TestGestureIUProducing Module"

    @staticmethod
    def description():
        return "A Module producing GestureIU each n seconds"

    @staticmethod
    def output_iu():
        return GestureIU

    def __init__(self, **kwargs):
        """
        Initialize the TestGestureIUProducingModule Module.
        """
        super().__init__(**kwargs)
        self._tts_thread_active = False
        self.cpt = 0

    def prepare_run(self):
        super().prepare_run()
        self._tts_thread_active = True
        threading.Thread(target=self.run_process).start()

    def shutdown(self):
        super().shutdown()
        self._tts_thread_active = False

    def process_update(self, update_message):
        pass

    def run_process(self):
        # The module doesn't send enough audio to have a continous signal, it's just a test module
        # If you want the module to send continous signal, change the time.sleep to time.sleep(self.frame_length), or the frame_length to 10
        while self._tts_thread_active:
            try:
                turnID = self.cpt // 2
                clauseID = self.cpt % 2
                interrupt = 0
                animations = [
                    {
                        "animation": "waiving",
                        "bodypart": "all",
                        "duration": 1.0,
                        "delay": 0.0,
                    },
                    {
                        "animation": "pointing",
                        "bodypart": "leftArm",
                        "duration": 1.0,
                        "delay": 1.0,
                    },
                ]
                blendshapes = [
                    {"id": "happy", "value": 1.0, "duration": 1.0, "delay": 0.0},
                    {"id": "sad", "value": 1.0, "duration": 1.0, "delay": 1.0},
                ]
                gazes = [
                    {"x": 30, "y": 50, "duration": 1.0, "delay": 0.0},
                    {"x": 0, "y": 0, "duration": 1.0, "delay": 1.0},
                ]
                left_hand_movements = [
                    {"x": 100, "y": 30, "duration": 1.0, "delay": 1.0}
                ]
                right_hand_movements = [
                    {"x": 30, "y": 0, "duration": 0.5, "delay": 0.0},
                    {"x": 0, "y": 50, "duration": 1.0, "delay": 0.5},
                ]
                lookAt = [{"x": 20, "y": 20, "duration": 2.0, "delay": 0.0}]
                iu = self.create_iu(
                    turnID=turnID,
                    clauseID=clauseID,
                    interrupt=interrupt,
                    animations=animations,
                    blendshapes=blendshapes,
                    gazes=gazes,
                    left_hand_movements=left_hand_movements,
                    right_hand_movements=right_hand_movements,
                    lookAt=lookAt,
                )

                um = retico_core.UpdateMessage()
                um.add_iu(iu, retico_core.UpdateType.ADD)
                self.append(um)
                self.terminal_logger.info(
                    "TestProducingModule creates a retico IU",
                    # audio_first_bytes=iu.payload[:20],
                )
                self.cpt += 1
                time.sleep(10)
                # time.sleep(self.frame_length)
            except Exception as e:
                log_exception(module=self, exception=e)


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


def test_exchange_through_activeMQ(iu_type=None):
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
    if iu_type == "text":
        producer = TestTextIUProducingModule()
        producer.subscribe(bridge)
        ar.add(destination=destination, target_iu_type=retico_core.text.TextIU)
        cback.callback = partial(callback_text_AMQReader, module=cback)
    elif iu_type == "audio":
        producer = TestAudioIUProducingModule()
        producer.subscribe(bridge)

        ar.add(destination=destination, target_iu_type=retico_core.audio.AudioIU)
        cback.callback = partial(callback_audio_AMQReader, module=cback)
    elif iu_type == "audio_turn":
        producer = TestAudioTurnIUProducingModule()
        producer.subscribe(bridge)

        ar.add(destination=destination, target_iu_type=TextAlignedAudioIU)
        cback.callback = partial(callback_audio_AMQReader, module=cback)
    elif iu_type == "gesture":
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
    # test_exchange_through_activeMQ("audio_turn")
    test_exchange_through_activeMQ("gesture")
