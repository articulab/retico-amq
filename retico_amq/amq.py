"""
ActiveMQ Module
=============

This module defines two incremental modules ZeroMQReader and ZeroMQWriter that act as a
a bridge between ZeroMQ and retico. For this, a ZeroMQIU is defined that contains the
information revceived over the ZeroMQ bridge.
"""

# retico
import keyboard
import retico_core
from retico_core.abstract import *

# activemq & supporting libraries
import json
import threading
import datetime
import stomp
import time
from collections import deque


class AMQIU(retico_core.IncrementalUnit):
    """Decorator class for IncrementalUnit that will be sent through ActiveMQ. Adding headers and destination parameters."""

    @staticmethod
    def type():
        return "AMQ IU"

    def __init__(
        self,
        creator=None,
        iuid=0,
        previous_iu=None,
        grounded_in=None,
        decorated_iu=None,
        headers=None,
        destination=None,
        **kwargs,
    ):
        super().__init__(
            creator=creator,
            iuid=iuid,
            previous_iu=previous_iu,
            grounded_in=grounded_in,
        )
        self.decorated_iu = decorated_iu
        self.headers = headers
        self.destination = destination

    def get_deco_iu(self):
        return self.decorated_iu

    def set_amq(self, decorated_iu, headers, destination):
        self.decorated_iu = decorated_iu
        self.headers = headers
        self.destination = destination


class AMQReader(retico_core.AbstractProducingModule):

    @staticmethod
    def name():
        return "AMQReader Module"

    @staticmethod
    def description():
        return "A Module providing reading onto a ActiveMQ bus"

    @staticmethod
    def output_iu():
        return IncrementalUnit

    def __init__(self, ip, port, **kwargs):
        """Initializes the ActiveMQReader.

        Args: topic(str): the topic/scope where the information will be read.

        """
        super().__init__(**kwargs)
        hosts = [(ip, port)]
        self.conn = stomp.Connection(host_and_ports=hosts, auto_content_length=False)
        self.conn.connect("admin", "admin", wait=True)
        self.conn.set_listener("", self.Listener(self))
        self.target_iu_types = dict()
        self.queue = deque()
        self._tts_thread_active = False

    def process_update(self, update_message):
        pass

    def prepare_run(self):
        super().prepare_run()
        self._tts_thread_active = True
        threading.Thread(target=self.run_process).start()
        # time.sleep(100000)
        keyboard.wait("q")

    def shutdown(self):
        """
        overrides AbstractModule : https://github.com/retico-team/retico-core/blob/main/retico_core/abstract.py#L819
        """
        super().shutdown()
        self._tts_thread_active = False

    class Listener(stomp.ConnectionListener):
        def __init__(self, module):
            super().__init__()
            # in order to use methods of activeMQ we create its instance
            self.module = module

        # Override the methods on_error and on_message provides by the parent class
        def on_error(self, frame):
            self.module.on_listener_error(frame)
            # print('received an error "%s"' % frame.body)

        def on_message(self, frame):
            # self.module.logMessageReception(frame)
            self.module.on_message(frame)

    def add(self, destination, target_iu_type):
        self.conn.subscribe(destination=destination, id=1, ack="auto")
        self.target_iu_types[destination] = target_iu_type

    def on_message(self, frame):
        self.queue.append(frame)

    def run_process(self):
        while self._tts_thread_active:
            time.sleep(0.2)
            if len(self.queue) > 0:
                frame = self.queue.popleft()
                message = frame.body
                destination = frame.headers["destination"]

                if destination not in self.target_iu_types:
                    print(destination, "is not a recognized destination")
                    return None

                self.terminal_logger.info("new iu", message=message)
                try:
                    # try to parse the message to create a dict (it has to be a structured message JSON), and put it in the IU's init parameters.
                    # create the decorated IU (cannot use classical create_iu from AbstractModule)
                    msg_json = json.loads(message)
                    self.terminal_logger.info("new iu json", msg_json=msg_json)
                    output_iu = self.target_iu_types[destination](
                        creator=self,
                        iuid=f"{hash(self)}:{self.iu_counter}",
                        previous_iu=self._previous_iu,
                        grounded_in=None,
                        **msg_json,
                    )
                except Exception:
                    # if message not parsable as a structured message (JSON), then put it as the IU's payload.
                    # create the decorated IU (cannot use classical create_iu from AbstractModule)
                    output_iu = self.target_iu_types[destination](
                        creator=self,
                        iuid=f"{hash(self)}:{self.iu_counter}",
                        previous_iu=self._previous_iu,
                        grounded_in=None,
                        # payload=message,
                    )

                # create the decorated IU (cannot use classical create_iu from AbstractModule)
                # output_iu = self.target_iu_types[destination](
                #     creator=self,
                #     iuid=f"{hash(self)}:{self.iu_counter}",
                #     previous_iu=self._previous_iu,
                #     grounded_in=None,
                # )
                # output_iu.payload = message
                self.iu_counter += 1
                self._previous_iu = output_iu
                update_message = retico_core.UpdateMessage()

                if "update_type" not in frame.headers:
                    print("Incoming IU has no update_type!")
                    update_message.add_iu(output_iu, retico_core.UpdateType.ADD)
                elif frame.headers["update_type"] == "UpdateType.ADD":
                    update_message.add_iu(output_iu, retico_core.UpdateType.ADD)
                elif frame.headers["update_type"] == "UpdateType.REVOKE":
                    update_message.add_iu(output_iu, retico_core.UpdateType.REVOKE)
                elif frame.headers["update_type"] == "UpdateType.COMMIT":
                    update_message.add_iu(output_iu, retico_core.UpdateType.COMMIT)
                self.append(update_message)


class AMQWriter(retico_core.AbstractModule):

    @staticmethod
    def name():
        return "AMQWriter Module"

    @staticmethod
    def description():
        return "A Module providing writing onto a ActiveMQ bus"

    @staticmethod
    def output_iu():
        return None

    @staticmethod
    def input_ius():
        return [AMQIU]

    def __init__(self, ip, port, **kwargs):
        """Initializes the ActiveMQWriter.

        Args: topic(str): the topic/scope where the information will be read.

        """
        super().__init__(**kwargs)
        hosts = [(ip, port)]
        self.conn = stomp.Connection(host_and_ports=hosts, auto_content_length=False)
        self.conn.connect("admin", "admin", wait=True)

    def process_update(self, update_message):
        """
        This assumes that the message is json formatted, then packages it as payload into an IU
        """

        for amq_iu, ut in update_message:

            # create a JSON from all decorated IU extracted information
            decorated_iu = amq_iu.get_deco_iu()

            # if we want all iu info
            # body = json.dumps(decorated_iu.__dict__)
            # if we want all iu info except some
            black_listed_keys = {
                "creator",
                "previous_iu",
                "grounded_in",
                "_processed_list",
                "mutex",
                "committed",
                "revoked",
                "meta_data",
            }
            iu_info = decorated_iu.__dict__
            print("KEYS = ", iu_info.keys())
            print("DICT = ", iu_info)
            iu_info = {key: iu_info[key] for key in iu_info.keys() - black_listed_keys}
            print("DICT AFTER = ", iu_info)
            body = json.dumps(iu_info)
            # if you have a to_amq() function in IU class
            # body = decorated_iu.to_amq()
            # # if we just want to send the payload
            # body = decorated_iu.payload

            # send the message to the correct destination
            print(
                f"sent {body},  to : {amq_iu.destination} , with headers : {amq_iu.headers}"
            )
            # self.terminal_logger.info(
            #     f"sent {body},  to : {amq_iu.destination} , with headers : {amq_iu.headers}"
            # )
            self.terminal_logger.info(
                "sent", destination=amq_iu.destination, headers=amq_iu.headers
            )
            self.conn.send(
                body=body,
                destination=amq_iu.destination,
                headers=amq_iu.headers,
                persistent=True,
            )

        return None


class AMQBridgeTest(retico_core.AbstractModule):

    @staticmethod
    def name():
        return "ActiveMQ Bridge Test Module"

    @staticmethod
    def description():
        return "A Module providing a test module that bridges between textIU to AMQIU"

    @staticmethod
    def output_iu():
        return AMQIU

    @staticmethod
    def input_ius():
        return [IncrementalUnit]

    def __init__(self, headers, destination, **kwargs):
        """Initializes the ActiveMQWriter.

        Args: topic(str): the topic/scope where the information will be read.

        """
        super().__init__(**kwargs)
        self.headers = headers
        self.destination = destination

    def process_update(self, update_message):
        """
        This assumes that the message is json formatted, then packages it as payload into an IU
        """

        um = retico_core.abstract.UpdateMessage()

        for input_iu, ut in update_message:
            if not input_iu.final:
                # create AMQIU
                output_iu = self.create_iu(
                    decorated_iu=input_iu,
                    destination=self.destination,
                    headers=self.headers,
                )
                um.add_iu(output_iu, ut)
            else:
                self.terminal_logger.warning("IU IS FINAL")
            #     # create AMQIU
            #     output_iu = self.create_iu(
            #         decorated_iu=input_iu,
            #         destination=self.destination,
            #         headers=self.headers,
            #     )
            #     um.add_iu(output_iu, ut)

        return um


## The retico-zmq implementation method
class WriterSingleton:
    __instance = None

    @staticmethod
    def getInstance():
        """Static access method."""
        return WriterSingleton.__instance

    def __init__(self, ip, port, kwargs):
        """Virtually private constructor."""
        if WriterSingleton.__instance == None:
            super().__init__(**kwargs)
            hosts = [(ip, port)]
            self.conn = stomp.Connection(
                host_and_ports=hosts, auto_content_length=False
            )
            self.conn.connect("admin", "admin", wait=True)
            self.queue = deque()
            WriterSingleton.__instance = self
            t = threading.Thread(target=self.run_writer)
            t.start()

    def send(self, data):
        self.queue.append(data)

    def run_writer(self):
        while True:
            if len(self.queue) == 0:
                time.sleep(0.1)
                continue
            data = self.queue.popleft()
            body, destination, headers = data
            print(f"sent {body},  to : {destination} , with headers : {headers}")
            self.conn.send(
                body=body,
                destination=destination,
                headers=headers,
                persistent=True,
            )


class ActiveMQWriter(retico_core.AbstractModule):
    """A ActiveMQ Writer Module

    Note: If you are using this to pass IU payloads to PSI, make sure you're passing JSON-formatable stuff (i.e., dicts not tuples)

    Attributes:
    topic (str): topic/scope that this writes to
    """

    @staticmethod
    def name():
        return "ActiveMQ Writer Module"

    @staticmethod
    def description():
        return "A Module providing writing onto a ActiveMQ bus"

    @staticmethod
    def output_iu():
        return None

    @staticmethod
    def input_ius():
        return [retico_core.IncrementalUnit]

    def __init__(self, destination, **kwargs):
        """Initializes the ActiveMQWriter.

        Args: destination(str): the destination where the information will be read.

        """
        super().__init__(**kwargs)
        self.destination = destination
        self.queue = deque()  # no maxlen
        self.writer = WriterSingleton.getInstance()

    def process_update(self, update_message):
        """
        This assumes that the message is json formatted, then packages it as payload into an IU
        """
        for amq_iu, um in update_message:
            # create a JSON from all decorated IU extracted information
            decorated_iu = amq_iu.get_deco_iu()

            # if we want all iu info
            body = json.dumps(decorated_iu.__dict__)
            # # if you have a to_amq() function in IU class
            # body = decorated_iu.to_amq()
            # # if we just want to send the payload
            # body = decorated_iu.payload

            # send the message to the correct destination
            print(
                f"sent {body},  to : {amq_iu.destination} , with headers : {amq_iu.headers}"
            )
            self.writer.send((body, amq_iu.destination, amq_iu.headers))

        return None
