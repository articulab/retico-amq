# retico-amq

ReTiCo module for ActiveMQ

## requirements

- ActiveMQ (version 5.15.0 : <https://activemq.apache.org/components/classic/download/classic-05-15-00>)

## Installation

```bash
cd path/to/your/retico-amq/clone
```

```bash
pip install .
```

## Quick init example

```python
# Both reader and writer are single modules that can handle multiple message sending / reception.

# the IP of the writer should be the originating PC's IP, the port would be ActiveMQ's
writer = AMQWriter(ip=ip, port='61613')

# the IP of the reader should be the target PC's IP, the port would be ActiveMQ's
reader = AMQReader(ip=ip, port='61613')
reader.add(destination="/topic/ASR", target_iu_type=SpeechRecognitionIU)
```

## How to connect them to other modules

### AMQWriter

The AMQWriter takes as input AMQIUs, that are defined in this retico-amq package. The AMQIU class is a decorator for IncrementalUnit, and is enhancing it with 2 ActiveMQ parameters : destination and headers. So an AMQIU keeps all parameters from its decorated_iu, plus the destination and headers parameters.

#### Case 1 : You implement a module that directly outputs AMQIU

If your module outputs AMQIU, and already handles the definition of headers and destination, you just have to subscribe the writer to your module.

```python
# the IP of the writer should be the originating PC's IP, the port would be ActiveMQ's
writer = AMQWriter(ip=ip, port='61613')
a = module_that_outputs_AMQIU(headers={"my_header":"my_header_value"}, destination="/topic/my_topic")

a.subscribe(writer)
```

#### Case 2 : You want to use an already implemented module that doesn't output AMQIU

You have to create a bridge module that takes your module IUs and enhanced them with headers and destination.
A General Bridge module is already implemented, it needs headers and destination parameters at initialization, and enhance the received IncrementalUnits by creating a decorating AMQIU around it with the headers and destination parameters.
If you want to do some treatement before sending the IUs to AMQWriter (such as filter the parameter sent), you can create your own AMQBridge module.

```python
# the IP of the writer should be the originating PC's IP, the port would be ActiveMQ's
writer = AMQWriter(ip=ip, port='61613')
b = module_that_doesnt_output_amqIU()
c = AMQBridge(headers={"my_header":"my_header_value"}, destination="/topic/my_topic")

b.subscribe(c)
c.subscribe(writer)
```

### AMQReader

To receive messages from an ActiveMQ source, to a retico module, you need to add to AMQReader the ActiveMQ source and the IU type you wish your retico module receives. Then, you can subscribe your module to AMQReader.

```python
# the IP of the reader should be the target PC's IP, the port would be ActiveMQ's
reader = AMQReader(ip=ip, port='61613')
e = module_that_takes_SpeechRecognitionIU_as_input()

reader.add(destination="/topic/ASR", target_iu_type=SpeechRecognitionIU)
reader.subscribe(e)
```

### Test the AMQWriter and AMQReader classes

The `utils.py` file contains classes and functions to test the execution of these 2 modules. The testing function `test_exchange_through_activeMQ` takes 1 argument `iu_type`, you can it to `"text"`, `"audio"`, `"audio_turn"` or `"gesture"` to test the exchange of corresponding IUs through ActiveMQ (you set the argument in the bottom of the file). The ActiveMQ topic where the messages are exchanged is `/topic/AMQ_test/`, you can monitor through ActiveMQ portal : <http://127.0.0.1:8161/admin/>.

To run the test, you first need to have ActiveMQ running on your computer :
<https://activemq.apache.org/components/classic/documentation/getting-started#StartingActiveMQStartingActiveMQ>

Then, from your retico-amq clone, run the following commads :

```bash
cd retico_amq
python utils.py
```

### Example of execution trace

Both AMQWriter and AMQReader have a `print` parameter, that you can set to True at initialization to enables the printing of the JSON body of the message sent to or received from ActiveMQ.

With print = False (Default) :

```bash
test running until ENTER key is pressed
2024-09-25T12:28:57.062708Z [info     ] TestProducingModule creates a retico IU module=AMQReader Module
2024-09-25T12:28:57.142886Z [info     ] AMQWriter sends a message to ActiveMQ ID=122806061901:0 destination=/topic/AMQ_test module=AMQWriter Module
2024-09-25T12:28:57.439677Z [info     ] AMQReader receives a message from ActiveMQ destination=/topic/AMQ_test module=AMQReader Module
2024-09-25T12:28:57.676791Z [info     ] AMQReader creates new iu       ID=122806061901:0 destination=/topic/AMQ_test module=AMQReader Module
2024-09-25T12:28:57.792264Z [info     ] CallbackModule receives a retico IU from AMQReader module=Callback Debug Module
```

With print = True :

```bash
test running until ENTER key is pressed
2024-09-25T12:28:57.062708Z [info     ] TestProducingModule creates a retico IU module=AMQReader Module
2024-09-25T12:28:57.142886Z [info     ] AMQWriter sends a message to ActiveMQ ID=122806061901:0 destination=/topic/AMQ_test module=AMQWriter Module
JSON MESSAGE SENT:
 {
  "created_at": "2024-09-25T14:28:57.050670",
  "head_movements": [
    {
      "x": 20,
      "y": 20,
      "duration": 2,
      "delay": 0
    }
  ],
  "emotions": [
    {
      "name": "happy",
      "duration": 1,
      "delay": 0
    },
    {
      "name": "sad",
      "duration": 1,
      "delay": 1
    }
  ],
  "payload": null,
  "eye_gazes": [
    {
      "x": 30,
      "y": 50,
      "duration": 1,
      "delay": 0
    },
    {
      "x": 0,
      "y": 0,
      "duration": 1,
      "delay": 1
    }
  ],
  "left_hand_movements": [
    {
      "x": 100,
      "y": 30,
      "duration": 1,
      "delay": 1
    }
  ],
  "animations": [
    {
      "name": "waiving",
      "duration": 1,
      "delay": 0
    },
    {
      "name": "pointing",
      "duration": 1,
      "delay": 1
    }
  ],
  "right_hand_movements": [
    {
      "x": 30,
      "y": 0,
      "duration": 0.5,
      "delay": 0
    },
    {
      "x": 0,
      "y": 50,
      "duration": 1,
      "delay": 0.5
    }
  ],
  "ID": "122806061901:0"
}
2024-09-25T12:28:57.439677Z [info     ] AMQReader receives a message from ActiveMQ destination=/topic/AMQ_test module=AMQReader Module
JSON MESSAGE RECEIVED:
 {
  "created_at": "2024-09-25T14:28:57.050670",
  "head_movements": [
    {
      "x": 20,
      "y": 20,
      "duration": 2,
      "delay": 0
    }
  ],
  "emotions": [
    {
      "name": "happy",
      "duration": 1,
      "delay": 0
    },
    {
      "name": "sad",
      "duration": 1,
      "delay": 1
    }
  ],
  "payload": null,
  "eye_gazes": [
    {
      "x": 30,
      "y": 50,
      "duration": 1,
      "delay": 0
    },
    {
      "x": 0,
      "y": 0,
      "duration": 1,
      "delay": 1
    }
  ],
  "left_hand_movements": [
    {
      "x": 100,
      "y": 30,
      "duration": 1,
      "delay": 1
    }
  ],
  "animations": [
    {
      "name": "waiving",
      "duration": 1,
      "delay": 0
    },
    {
      "name": "pointing",
      "duration": 1,
      "delay": 1
    }
  ],
  "right_hand_movements": [
    {
      "x": 30,
      "y": 0,
      "duration": 0.5,
      "delay": 0
    },
    {
      "x": 0,
      "y": 50,
      "duration": 1,
      "delay": 0.5
    }
  ],
  "ID": "122806061901:0"
}
2024-09-25T12:28:57.676791Z [info     ] AMQReader creates new iu       ID=122806061901:0 destination=/topic/AMQ_test module=AMQReader Module
2024-09-25T12:28:57.792264Z [info     ] CallbackModule receives a retico IU from AMQReader module=Callback Debug Module
```
