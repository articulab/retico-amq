"""
ZeroMQ Module
=============

This module defines two incremental modules ZeroMQReader and ZeroMQWriter that act as a
a bridge between ZeroMQ and retico. For this, a ZeroMQIU is defined that contains the
information revceived over the ZeroMQ bridge.
"""

# retico
import retico_core
from retico_core.abstract import *

# zeromq & supporting libraries
import zmq, json
import threading
import datetime
import time
from collections import deque

class ReaderSingleton:
    __instance = None

    @staticmethod
    def getInstance():
        """Static access method."""
        return ReaderSingleton.__instance

    def __init__(self, ip, port):
        """Virtually private constructor."""
        if ReaderSingleton.__instance == None:
            self.socket = zmq.Context().socket(zmq.SUB)
            self.socket.connect("tcp://{}:{}".format(ip, port))
            ReaderSingleton.__instance = self


class WriterSingleton:
    __instance = None

    @staticmethod
    def getInstance():
        """Static access method."""
        return WriterSingleton.__instance

    def __init__(self, ip, port):
        """Virtually private constructor."""
        if WriterSingleton.__instance == None:
            context = zmq.Context()
            self.socket = context.socket(zmq.PUB)
            self.socket.bind("tcp://{}:{}".format(ip, port))
            WriterSingleton.__instance = self


class ZeroMQIU(retico_core.IncrementalUnit):
    @staticmethod
    def type():
        return "ZeroMQ Incremental Unit"

    def __init__(
        self,
        creator=None,
        iuid=0,
        previous_iu=None,
        grounded_in=None,
        payload=None,
        **kwargs
    ):
        """Initialize the DialogueActIU with act and concepts.

        Args:
            act (string): A representation of the act.
            concepts (dict): A representation of the concepts as a dictionary.
        """
        super().__init__(
            creator=creator,
            iuid=iuid,
            previous_iu=previous_iu,
            grounded_in=grounded_in,
            payload=payload,
        )

    def set_payload(self, payload):
        self.payload = payload


class ZeroMQReader(retico_core.AbstractProducingModule):

    """A ZeroMQ Reader Module

    Attributes:

    """

    @staticmethod
    def name():
        return "ZeroMQ Reader Module"

    @staticmethod
    def description():
        return "A Module providing reading from a ZeroMQ bus"

    @staticmethod
    def output_iu():
        return IncrementalUnit

    def __init__(self, topic, target_iu_type, **kwargs):
        """Initializes the ZeroMQReader.

        Args: topic(str): the topic/scope where the information will be read.

        """
        super().__init__(**kwargs)
        self.topic = topic
        self.reader = None
        self.target_iu_type = target_iu_type

    def process_update(self, input_iu):
        """
        This assumes that the message is json formatted, then packages it as payload into an IU
        """
        [topic, message] = self.reader.recv_multipart()
        
        output_iu = self.target_iu_type(
                    creator=self,
                    iuid=f"{hash(self)}:{self.iu_counter}",
                    previous_iu=self._previous_iu,
                    grounded_in=None,
                )
        self.iu_counter += 1
        self._previous_iu = output_iu
        j = json.loads(message)
        output_iu.from_zmq(j)

        update_message = retico_core.UpdateMessage()

        if "update_type" not in j:
            print("Incoming IU has no update_type!")
        if j["update_type"] == "UpdateType.ADD":
            update_message.add_iu(output_iu, retico_core.UpdateType.ADD)
        elif j["update_type"] == "UpdateType.REVOKE":
            update_message.add_iu(output_iu, retico_core.UpdateType.REVOKE)
        elif j["update_type"] == "UpdateType.COMMIT":
            update_message.add_iu(output_iu, retico_core.UpdateType.COMMIT)

        return update_message

    def prepare_run(self):
        self.reader = ReaderSingleton.getInstance().socket
        self.reader.setsockopt(zmq.SUBSCRIBE, self.topic.encode())

    def setup(self):
        pass



class ZeroMQWriter(retico_core.AbstractModule):

    """A ZeroMQ Writer Module

    Note: If you are using this to pass IU payloads to PSI, make sure you're passing JSON-formatable stuff (i.e., dicts not tuples)

    Attributes:
    topic (str): topic/scope that this writes to
    """

    @staticmethod
    def name():
        return "ZeroMQ Writer Module"

    @staticmethod
    def description():
        return "A Module providing writing onto a ZeroMQ bus"

    @staticmethod
    def output_iu():
        return None

    @staticmethod
    def input_ius():
        return [retico_core.IncrementalUnit]

    def __init__(self, topic, **kwargs):
        """Initializes the ZeroMQReader.

        Args: topic(str): the topic/scope where the information will be read.

        """
        super().__init__(**kwargs)
        self.topic = topic.encode()
        self.queue = deque()  # no maxlen
        self.writer = None

    def process_update(self, update_message):
        """
        This assumes that the message is json formatted, then packages it as payload into an IU
        """
        for um in update_message:
            self.queue.append(um)

        return None

    def run_writer(self):

        while True:
            if len(self.queue) == 0:
                time.sleep(0.1)
                continue
            input_iu, ut = self.queue.popleft()

            # print(input_iu.payload)
            # if isinstance(input_iu, ImageIU) or isinstance(input_iu, DetectedObjectsIU)  or isinstance(input_iu, ObjectFeaturesIU):
            #     payload['message'] = json.dumps(input_iu.get_json())
            self.writer.send_multipart(
                [self.topic, json.dumps(input_iu.to_zmq(ut)).encode("utf-8")]
            )

    def setup(self):
        self.writer = WriterSingleton.getInstance().socket
        t = threading.Thread(target=self.run_writer)
        t.start()


# class ZMQtoImage(retico_core.AbstractModule):
#     @staticmethod
#     def name():
#         return "ZMQtoASR"
#     @staticmethod
#     def description():
#         return "Convert ZeroMQIU to SpeechRecognitionIU"
#     @staticmethod
#     def input_ius():
#         return [ZeroMQIU]
#     @staticmethod
#     def output_iu():
#         return ImageIU

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)

#     def process_update(self,update_message):

#         for iu,um in update_message:
#             # print("getting ZMQ", iu.payload['message'])
#             output_iu = self.create_iu(iu)
#             output_iu.create_from_json(json.loads(iu.payload['message']))
#             # self.current_ius.append(output_iu)
#             new_um = retico_core.UpdateMessage.from_iu(output_iu, um)
            
#         return new_um

#     def setup(self):
#         pass


# class ZMQtoDetectedObjects(retico_core.AbstractModule):
#     @staticmethod
#     def name():
#         return "ZMQtoDetectedObjects"
#     @staticmethod
#     def description():
#         return "Convert ZeroMQIU to DetectedObjectsIU"
#     @staticmethod
#     def input_ius():
#         return [ZeroMQIU]
#     @staticmethod
#     def output_iu():
#         return ObjectFeaturesIU

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)

#     def process_update(self,update_message):
#         for iu,um in update_message:
#             # print("getting ZMQ", iu.payload['message'])
#             output_iu = self.create_iu(iu)
#             output_iu.create_from_json(json.loads(iu.payload['message']))
#             # self.current_ius.append(output_iu)
#             new_um = retico_core.UpdateMessage.from_iu(output_iu, um)
            
#         return new_um

#     def setup(self):
#         pass