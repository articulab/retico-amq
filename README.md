# retico-amq

ReTiCo module for ActiveMQ

### Installation

### Example

```
Writers are individual modules, but Readers are all a single module with the option of having many channels. Each channel can be set to output a specific IU type. 

# the IP of the writer should be the originating PC's IP
WriterSingleton(ip=ip, port='12345')
refer_od = ZeroMQWriter(topic='referod')
refer_dm = ZeroMQWriter(topic='referdm')
refer_wac = ZeroMQWriter(topic='referwac')

# the IP of the reader should be the target PC's IP
reader = ReaderSingleton(ip=ip2, port='12346')
reader.add(topic='camera', target_iu_type=ImageIU)
reader.add(topic='refer', target_iu_type=GenericDictIU)

```
