"""
ActiveMQ Module
=============

This module defines two incremental modules ZeroMQReader and ZeroMQWriter that act as a
a bridge between ZeroMQ and retico. For this, a ZeroMQIU is defined that contains the
information revceived over the ZeroMQ bridge.
"""

# retico
# from functools import partial
import traceback
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
from retico_core.log_utils import log_exception


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
    """
    Module providing a retico system with ActiveMQ message reception.
    The module can subscribe to different ActiveMQ destinations, each will correspond to a desired IU type.
    At each message reception from one of the destinations, the module transforms the ActiveMQ message to an IncrementalUnit of the corresponding IU type.
    """

    @staticmethod
    def name():
        return "AMQReader Module"

    @staticmethod
    def description():
        return "A Module providing a retico system with ActiveMQ message reception"

    @staticmethod
    def output_iu():
        return IncrementalUnit

    def __init__(self, ip, port, print=False, **kwargs):
        """Initializes the ActiveMQReader.

        Args:
            ip (str): the IP of the computer.
            port (str): the port corresponding to ActiveMQ
            print (bool): boolean that manages printing
        """
        super().__init__(**kwargs)
        self.hosts = [(ip, port)]
        self.conn = None
        self.target_iu_types = dict()
        self.queue = deque()
        self._tts_thread_active = False
        self.print = print

    def process_update(self, update_message):
        if self._tts_thread_active:
            time.sleep(0.1)

    def setup(self):
        super().setup()
        try:
            self.conn = stomp.Connection(
                host_and_ports=self.hosts, auto_content_length=False
            )
            self.conn.connect("admin", "admin", wait=True)
            self.conn.set_listener("", self.Listener(self))
            for destination in self.target_iu_types:
                self.conn.subscribe(destination=destination, id=1, ack="auto")
        except stomp.exception.ConnectFailedException as e:
            log_exception(module=self, exception=e)
            raise stomp.exception.ConnectFailedException from e

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

    class Listener(stomp.ConnectionListener):
        """Listener that triggers ANQReader's `on_message` function every time a message is unqueued in one of the subscribed destination."""

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
        """Stores the destination to subscribe to and the corresponding desired IU type in `target_iu_type`.

        Args:
            destination (_type_): the ActiveMQ destination to subscribe to.
            target_iu_type (dict): dictionary of all destination-IU type associations.
        """
        self.target_iu_types[destination] = target_iu_type

    def on_message(self, frame):
        """The function that is triggered every time a message (= `frame`)is unqueued in one of the subscribed destination.
        The message is then processed an transformed into an IU of the corresponding type.

        Args:
            frame (stomp.frame): the received ActiveMQ message.
        """
        # check if it doesn't throw exception ? in case some frame parameter is not printable
        self.terminal_logger.info(
            "AMQReader receives a message from ActiveMQ",
            destination=frame.headers["destination"],
            # headers=frame.headers,
            # message=frame.body,
        )
        self.queue.append(frame)

    def run_process(self):
        """Function that will run on a separate thread and process the ActiveMQ messages received, and previous append in the class parameter `queue`.

        Returns:
            _type_: _description_
        """
        while self._tts_thread_active:
            try:
                time.sleep(0.2)
                if len(self.queue) > 0:
                    frame = self.queue.popleft()
                    message = frame.body
                    destination = frame.headers["destination"]

                    if destination not in self.target_iu_types:
                        print(destination, "is not a recognized destination")
                        return None

                    try:
                        # try to parse the message to create a dict (it has to be a structured message JSON), and put it in the IU's init parameters.
                        # create the decorated IU (cannot use classical create_iu from AbstractModule)
                        msg_json = json.loads(message)
                        iu_type = self.target_iu_types[destination]
                        init_args = iu_type.__init__.__code__.co_varnames
                        common_args = msg_json.keys() & init_args
                        deleted_args = msg_json.keys() - init_args
                        # print(common_args)
                        # print(deleted_args)
                        msg_json_filtered = {key: msg_json[key] for key in common_args}
                        output_iu = self.target_iu_types[destination](
                            creator=self,
                            iuid=f"{hash(self)}:{self.iu_counter}",
                            previous_iu=self._previous_iu,
                            grounded_in=None,
                            **msg_json_filtered,
                        )
                        if self.print:
                            print(
                                "JSON MESSAGE RECEIVED: \n",
                                json.dumps(msg_json, indent=2),
                            )
                        self.terminal_logger.info(
                            "AMQReader creates new iu",
                            destination=frame.headers["destination"],
                            ID=msg_json["requestID"],
                        )
                    except Exception as e:
                        # if message not parsable as a structured message (JSON), then put it as the IU's payload.
                        # create the decorated IU (cannot use classical create_iu from AbstractModule)
                        log_exception(module=self, exception=e)
                        output_iu = self.target_iu_types[destination](
                            creator=self,
                            iuid=f"{hash(self)}:{self.iu_counter}",
                            previous_iu=self._previous_iu,
                            grounded_in=None,
                            # payload=message,
                        )
                    self.terminal_logger.info(
                        "create_iu",
                        iuid=output_iu.iuid,
                        previous_iu=(
                            output_iu.previous_iu.iuid
                            if output_iu.previous_iu is not None
                            else None
                        ),
                        grounded_in=(
                            output_iu.grounded_in.iuid
                            if output_iu.grounded_in is not None
                            else None
                        ),
                    )

                    self.iu_counter += 1
                    self._previous_iu = output_iu
                    update_message = retico_core.UpdateMessage()

                    if "update_type" not in frame.headers:
                        # print("Incoming IU has no update_type!")
                        update_message.add_iu(output_iu, retico_core.UpdateType.ADD)
                    elif frame.headers["update_type"] == "UpdateType.ADD":
                        update_message.add_iu(output_iu, retico_core.UpdateType.ADD)
                    elif frame.headers["update_type"] == "UpdateType.REVOKE":
                        update_message.add_iu(output_iu, retico_core.UpdateType.REVOKE)
                    elif frame.headers["update_type"] == "UpdateType.COMMIT":
                        update_message.add_iu(output_iu, retico_core.UpdateType.COMMIT)
                    self.append(update_message)
            except Exception as e:
                log_exception(module=self, exception=e)


class AMQWriter(retico_core.AbstractModule):
    """
    Module providing a retico system with ActiveMQ message sending.
    The module will transform the AMQIU received into ActiveMQ messages, and send them to ActiveMQ following the AMQIU's `destination` and `headers` parameters.
    """

    @staticmethod
    def name():
        return "AMQWriter Module"

    @staticmethod
    def description():
        return "A Module providing a retico system with ActiveMQ message sending."

    @staticmethod
    def output_iu():
        return None

    @staticmethod
    def input_ius():
        return [AMQIU]

    def __init__(self, ip, port, print=False, **kwargs):
        """Initializes the ActiveMQWriter.

        Args:
            ip (str): the IP of the computer.
            port (str): the port corresponding to ActiveMQ
            print (bool): boolean that manages printing
        """
        super().__init__(**kwargs)
        self.hosts = [(ip, port)]
        self.print = print
        self.conn = None

    def setup(self):
        super().setup()
        try:
            self.conn = stomp.Connection(
                host_and_ports=self.hosts, auto_content_length=False
            )
            self.conn.connect("admin", "admin", wait=True)
        except stomp.exception.ConnectFailedException as e:
            log_exception(module=self, exception=e)
            raise stomp.exception.ConnectFailedException from e

    def process_update(self, update_message):
        """
        The function will take all parameters from each decorated IU, and transform it into a json so that it can be sent to ActiveMQ.
        Some IU parameters are blacklisted (`black_listed_keys`), they either can't be transformed into json, or are useless outside of the retico system.
        """

        for amq_iu, _ in update_message:

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
                "iuid",
            }
            iu_info = decorated_iu.__dict__
            iu_info_filtered = {
                key: iu_info[key] for key in iu_info.keys() - black_listed_keys
            }
            iu_info_filtered["requestID"] = iu_info["iuid"]
            body = json.dumps(iu_info_filtered, indent=2)
            # if you have a to_amq() function in IU class
            # body = decorated_iu.to_amq()
            # # if we just want to send the payload
            # body = decorated_iu.payload

            # send the message to the correct destination
            self.terminal_logger.info(
                "AMQWriter sends a message to ActiveMQ",
                destination=amq_iu.destination,
                ID=iu_info["iuid"],
                # headers=amq_iu.headers,
                # body=body,
            )
            if self.print:
                print("JSON MESSAGE SENT: \n", body)
            self.conn.send(
                body=body,
                destination=amq_iu.destination,
                headers=amq_iu.headers,
                persistent=True,
            )

        return None


class AMQBridge(retico_core.AbstractModule):
    """Module providing a retico system with the capacity to transform any retico IU into an AMQIU.
    A AMQIU enhance an IU with a `destination` and a `headers` parameters.
    """

    @staticmethod
    def name():
        return "AMQBridge Module"

    @staticmethod
    def description():
        return "A Module providing a module that bridges between retico and ActiveMQ by creating AMQIU from IncrementalUnit"

    @staticmethod
    def output_iu():
        return AMQIU

    @staticmethod
    def input_ius():
        return [IncrementalUnit]

    def __init__(self, headers, destination, **kwargs):
        """Initializes the AMQBridge.

        Args:
            headers (dict): the ActiveMQ headers to be sent with the message.
            destination (str): the ActiveMQ destination to send the message to.
        """
        super().__init__(**kwargs)
        self.headers = headers
        self.destination = destination

    def process_update(self, update_message):
        """Transform an IU into an AMQIU.
        For now : except the `final` IUs which are empty
        """
        um = retico_core.abstract.UpdateMessage()

        for input_iu, ut in update_message:
            if hasattr(input_iu, "final"):
                if input_iu.final:
                    self.terminal_logger.warning("IU IS FINAL")
                else:
                    # create AMQIU
                    output_iu = self.create_iu(
                        decorated_iu=input_iu,
                        destination=self.destination,
                        headers=self.headers,
                    )
                    um.add_iu(output_iu, ut)
            else:
                # create AMQIU
                output_iu = self.create_iu(
                    decorated_iu=input_iu,
                    destination=self.destination,
                    headers=self.headers,
                )
                um.add_iu(output_iu, ut)

        return um


## The retico-zmq implementation method

# class WriterSingleton:
#     __instance = None

#     @staticmethod
#     def getInstance():
#         """Static access method."""
#         return WriterSingleton.__instance

#     def __init__(self, ip, port, kwargs):
#         """Virtually private constructor."""
#         if WriterSingleton.__instance == None:
#             super().__init__(**kwargs)
#             hosts = [(ip, port)]
#             self.conn = stomp.Connection(
#                 host_and_ports=hosts, auto_content_length=False
#             )
#             self.conn.connect("admin", "admin", wait=True)
#             self.queue = deque()
#             WriterSingleton.__instance = self
#             t = threading.Thread(target=self.run_writer)
#             t.start()

#     def send(self, data):
#         self.queue.append(data)

#     def run_writer(self):
#         while True:
#             if len(self.queue) == 0:
#                 time.sleep(0.1)
#                 continue
#             data = self.queue.popleft()
#             body, destination, headers = data
#             print(f"sent {body},  to : {destination} , with headers : {headers}")
#             self.conn.send(
#                 body=body,
#                 destination=destination,
#                 headers=headers,
#                 persistent=True,
#             )


# class ActiveMQWriter(retico_core.AbstractModule):
#     """A ActiveMQ Writer Module

#     Note: If you are using this to pass IU payloads to PSI, make sure you're passing JSON-formatable stuff (i.e., dicts not tuples)

#     Attributes:
#     topic (str): topic/scope that this writes to
#     """

#     @staticmethod
#     def name():
#         return "ActiveMQ Writer Module"

#     @staticmethod
#     def description():
#         return "A Module providing writing onto a ActiveMQ bus"

#     @staticmethod
#     def output_iu():
#         return None

#     @staticmethod
#     def input_ius():
#         return [retico_core.IncrementalUnit]

#     def __init__(self, destination, **kwargs):
#         """Initializes the ActiveMQWriter.

#         Args: destination(str): the destination where the information will be read.

#         """
#         super().__init__(**kwargs)
#         self.destination = destination
#         self.queue = deque()  # no maxlen
#         self.writer = WriterSingleton.getInstance()

#     def process_update(self, update_message):
#         """
#         This assumes that the message is json formatted, then packages it as payload into an IU
#         """
#         for amq_iu, um in update_message:
#             # create a JSON from all decorated IU extracted information
#             decorated_iu = amq_iu.get_deco_iu()

#             # if we want all iu info
#             body = json.dumps(decorated_iu.__dict__)
#             # # if you have a to_amq() function in IU class
#             # body = decorated_iu.to_amq()
#             # # if we just want to send the payload
#             # body = decorated_iu.payload

#             # send the message to the correct destination
#             print(
#                 f"sent {body},  to : {amq_iu.destination} , with headers : {amq_iu.headers}"
#             )
#             self.writer.send((body, amq_iu.destination, amq_iu.headers))

#         return None
