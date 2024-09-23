# retico-amq

ReTiCo module for ActiveMQ

### Installation

### Example

```python
# Both reader and writer are single modules that can handle multiple message sending / reception.

# the IP of the writer should be the originating PC's IP, the port would be ActiveMQ's
writer = AMQWriter(ip=ip, port='61613')

# the IP of the reader should be the target PC's IP, the port would be ActiveMQ's
reader = AMQReader(ip=ip, port='61613')
reader.add(destination="/topic/ASR", target_iu_type=SpeechRecognitionIU)
```

### How to link them with other modules

#### AMQWriter

The AMQWriter takes as input AMQIUs, that are defined in this retico-amq package. The AMQIU class is a decorator for IncrementalUnit, and is enhancing it with 2 ActiveMQ parameters : destination and headers. So an AMQIU keeps all parameters from its decorated_iu, plus the destination and headers parameters.

##### Case 1 : You implement a module that directly outputs AMQIU

If your module outputs AMQIU, and already handles the definition of headers and destination, you just have to subscribe the writer to your module.

```python
# the IP of the writer should be the originating PC's IP, the port would be ActiveMQ's
writer = AMQWriter(ip=ip, port='61613')
a = module_that_outputs_AMQIU(headers={"my_header":"my_header_value"}, destination="/topic/my_topic")

a.subscribe(writer)
```

##### Case 2 : You want to use an already implemented module that doesn't output AMQIU

You have to create a bridge module that takes your module IUs and enhanced them with headers and destination.

```python
# the IP of the writer should be the originating PC's IP, the port would be ActiveMQ's
writer = AMQWriter(ip=ip, port='61613')
b = module_that_doesnt_output_amqIU()
c = bridge_between_retico_and_amq(headers={"my_header":"my_header_value"}, destination="/topic/my_topic")

b.subscribe(c)
c.subscribe(writer)
```

#### AMQReader

To receive messages from an ActiveMQ source, to a retico module, you need to add to AMQReader the ActiveMQ source and the IU type you wish your retico module receives. Then, you can subscribe your module to AMQReader.

```python
# the IP of the reader should be the target PC's IP, the port would be ActiveMQ's
reader = AMQReader(ip=ip, port='61613')
e = module_that_takes_SpeechRecognitionIU_as_input()

reader.add(destination="/topic/ASR", target_iu_type=SpeechRecognitionIU)
reader.subscribe(e)
```
