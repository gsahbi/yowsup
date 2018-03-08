import inspect
from copy import deepcopy

from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.structs import ProtocolEntity


class MessageContext(object):

    def __init__(self, stanza_id=None, participant=None, quoted_message=None, remote_jid=None, mentioned_jid=None):
        self.stanza_id = stanza_id
        self.participant = participant
        self.quoted_message = quoted_message
        self.remote_jid = remote_jid
        self.mentioned_jid = list(mentioned_jid) if mentioned_jid is not None else None


    @property
    def stanza_id(self): return self._stanza_id

    @stanza_id.setter
    def stanza_id(self, v):
        self._stanza_id = v

    @property
    def participant(self): return self._participant

    @participant.setter
    def participant(self, v):
        self._participant = v

    @property
    def quoted_message(self): return self._quoted_message

    @quoted_message.setter
    def quoted_message(self, v):
        self._quoted_message = v

    @property
    def remote_jid(self): return self._remote_jid

    @remote_jid.setter
    def remote_jid(self, v):
        self._remote_jid = v

    @property
    def mentioned_jid(self): return self._mentioned_jids


    @mentioned_jid.setter
    def mentioned_jid(self, v):
        self._mentioned_jids = v

    def __str__(self):

        out = ''
        if self.is_reply():
            out += "Reply context:\n"
            out += "\tMessage ID: %s\n" % self.stanza_id
            out += "\tParticipant: %s\n" % self.participant
            if self.quoted_message is not None:
                out += "\tQuoted message:\n"
                out += "\t\tType: %s\n" % " ".join(self.quoted_message.keys())

        if self.is_mention():
            out += "Mention context:\n"
            out += "\tMentioned JIDs: %s\n" % ", ".join(self.mentioned_jid)
            if self.remote_jid is not None:
                out += "\tRemote JID: %s\n" % self.remote_jid

        return out

    def is_reply(self):
        return self.stanza_id is not None

    def is_mention(self):
        return self.mentioned_jid is not None

    def get_quoted_message_type(self):
        if self.quoted_message:
            return self.quoted_message.keys()
        else:
            return None

    def get_mentioned_jids(self):
        if self.mentioned_jid:
            return self.mentioned_jid
        else:
            return None


class MessageProtocolEntity(ProtocolEntity):

    def __init__(self, ptn=None, **kwargs):

        super().__init__(tag="message")
        if ptn:
            MessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            MessageProtocolEntity.load_properties(self, **kwargs)

        assert (self.sender or self.destination), "Must specify either to or _from jids to create the message"
        assert not (self.sender and self.destination), "Can't set both attributes to message at same time (to, _from)"

    def load_properties(self, **kwargs):
        stack = inspect.stack()
        caller_class = stack[1][0].f_locals['__class__']
        props = [name for name, value in vars(caller_class).items() if isinstance(value, property)]
        for p in props:
            setattr(self, p, kwargs[p] if p in kwargs else None)

    @property
    def participant(self):
        return self._participant

    @participant.setter
    def participant(self, v):
        self._participant = v

    @property
    def destination(self):
        return self._destination

    @destination.setter
    def destination(self, v):
        self._destination = v

    @property
    def retry(self):
        return self._retry

    @retry.setter
    def retry(self, v):
        self._retry = int(v) if v else None

    @property
    def offline(self):
        return self._offline

    @offline.setter
    def offline(self, v=None):
        self._offline = v == "1" if v is not None else v

    @property
    def notify(self):
        return self._notify

    @notify.setter
    def notify(self, v):
        self._notify = v

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, t=None):
        self._timestamp = int(t) if t else self._getCurrentTimestamp()

    @property
    def sender(self):
        return self._sender

    @sender.setter
    def sender(self, v):
        self._sender = v

    @property
    def message_id(self):
        return self._message_id

    @message_id.setter
    def message_id(self, v=None):
        self._message_id = self._generateId() if v is None else v

    @property
    def message_type(self):  # media or text
        return self._message_type

    @message_type.setter
    def message_type(self, v):
        self._message_type = v


    @property
    def media_type(self): return self._media_type

    @media_type.setter
    def media_type(self, v):
        self._media_type = v


    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, v):
        self._context = MessageContext(**v) if v is not None else None

    # TODO : Implement broadcast
    # TODO : Remove most of the boilerplate by leveraging docstring property as a mapping string

    def getAuthor(self):
        return self.participant if self.isGroupMessage() else self.sender

    def isOutgoing(self):
        return self.sender is None

    def isGroupMessage(self):
        if self.isOutgoing():
            return "-" in self.destination
        return self.participant is not None

    def is_downloadable(self):
        return False

    def __str__(self):
        out = "Message:\n"
        out += "ID: %s\n" % self.message_id
        out += ("To: %s\n" % self.destination if self.isOutgoing() else "From: %s\n" % self.sender)
        out += "Type:  %s\n" % self.message_type
        out += "Timestamp: %s\n" % self.timestamp
        if self.participant:
            out += "Participant: %s\n" % self.participant
        return out

    def ack(self, read=False):
        return OutgoingReceiptProtocolEntity(self.message_id, self.sender, read, participant=self.participant)

    def forward(self, destination, message_id=None):
        OutgoingMessage = deepcopy(self)
        OutgoingMessage.destination = destination
        OutgoingMessage.sender = None
        OutgoingMessage.notify = None
        OutgoingMessage.participant = None
        OutgoingMessage.message_id = message_id
        return OutgoingMessage

    def fromProtocolTreeNode(self, node):
        enc = node.getChild("enc")
        self.media_type = enc["mediatype"] if enc else None

        body = node.getChild('body')
        if body is not None and 'context_info' in body.data:
            self.context = body.data['context_info']
        else:
            self.context = None

        self.message_type = node["type"]
        self.message_id = node["id"]
        self.sender = node["from"]
        self.destination = node["to"]
        self.notify = node["notify"]
        self.timestamp = node["t"]
        self.participant = node["participant"]
        self.offline = node["offline"]
        self.retry = node["retry"]

    def toProtocolTreeNode(self):
        attribs = {
            "type": self.message_type,
            "id": self.message_id,
        }

        if self.isOutgoing():
            attribs["to"] = self.destination
        else:
            attribs["from"] = self.sender

        attribs["t"] = str(self.timestamp)

        if self.offline is not None:
            attribs["offline"] = "1" if self.offline else "0"
        if self.notify:
            attribs["notify"] = self.notify
        if self.retry:
            attribs["retry"] = str(self.retry)
        if self.participant:
            attribs["participant"] = self.participant

        return self._createProtocolTreeNode(attribs, children=None, data=None)
