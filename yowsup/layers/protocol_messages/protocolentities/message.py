from copy import deepcopy

from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.structs import ProtocolEntity


class MessageContext(object):

    def __init__(self, stanza_id=None, participant=None,
                 remote_jid=None, mentioned_jid=None, quoted_message=None):
        self.stanza_id = stanza_id
        self.participant = participant
        self.quoted_message = quoted_message
        self.remote_jid = remote_jid
        self.mentioned_jid = mentioned_jid

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

    def get_participant(self):
        return self.participant

    def get_stanza_id(self):
        return self.stanza_id

class MessageProtocolEntity(ProtocolEntity):

    def __init__(self, node):

        super(MessageProtocolEntity, self).__init__("message")
        self.offline = node['offline']
        self.retry = node['retry']
        self._type = node['type']
        self._id = node['id'] or self._generateId()
        self._from = node['from']
        self.to = node['to']
        self.timestamp = int(node['t']) or self._getCurrentTimestamp()
        self.notify = node['notify']
        self.participant = node['participant']
        self.context = None
        self.is_broadcast = False

        body = node.getChild('body')
        if body is not None and 'context_info' in body.data:
            self.context = MessageContext(**body.data['context_info'])

    def build(self, _type, _id=None, _from=None, to=None, notify=None, timestamp=None,
              participant=None, offline=None, retry=None):

        assert (to or _from), "Must specify either to or _from jids to create the message"
        assert not (to and _from), "Can't set both attributes to message at same time (to, _from)"

        super(MessageProtocolEntity, self).build("message")
        self._type = _type
        self._id = MessageProtocolEntity._generateId()
        self._from = _from
        self.to = to
        self.timestamp = int(timestamp) if timestamp else MessageProtocolEntity._getCurrentTimestamp()
        self.notify = notify
        self.offline = offline == "1" if offline is not None else offline
        self.retry = int(retry) if retry else None
        self.participant = participant
        self.context = None
        self.is_broadcast = False

    def getContext(self):
        return self.context

    def getType(self):
        return self._type

    def getId(self):
        return self._id

    def getTimestamp(self):
        return self.timestamp

    def getFrom(self, full=True):
        return self._from if full else self._from.split('@')[0]

    def isBroadcast(self):
        return self.is_broadcast

    def getTo(self, full=True):
        return self.to if full else self.to.split('@')[0]

    def getParticipant(self, full=True):
        return self.participant if full else self.participant.split('@')[0]

    def getAuthor(self, full=True):
        return self.getParticipant(full) if self.isGroupMessage() else self.getFrom(full)

    def getNotify(self):
        return self.notify

    def toProtocolTreeNode(self):
        attribs = {
            "type": self._type,
            "id": self._id,
        }

        if self.isOutgoing():
            attribs["to"] = self.to
        else:
            attribs["from"] = self._from

            attribs["t"] = str(self.timestamp)

            if self.offline is not None:
                attribs["offline"] = "1" if self.offline else "0"
            if self.notify:
                attribs["notify"] = self.notify
            if self.retry:
                attribs["retry"] = str(self.retry)
            if self.participant:
                attribs["participant"] = self.participant

        xNode = None
        # if self.isOutgoing():
        #    serverNode = ProtocolTreeNode("server", {})
        #    xNode = ProtocolTreeNode("x", {"xmlns": "jabber:x:event"}, [serverNode])

        return self._createProtocolTreeNode(attribs, children=[xNode] if xNode else None, data=None)

    def isOutgoing(self):
        return self._from is None

    def isGroupMessage(self):
        if self.isOutgoing():
            return "-" in self.to
        return self.participant is not None

    def __str__(self):
        out = "Message:\n"
        out += "ID: %s\n" % self._id
        out += "To: %s\n" % self.to if self.isOutgoing() else "From: %s\n" % self._from
        out += "Type:  %s\n" % self._type
        out += "Timestamp: %s\n" % self.timestamp
        if self.participant:
            out += "Participant: %s\n" % self.participant
        if self.context:
            out += str(self.context)

        return out

    def ack(self, read=False):
        return OutgoingReceiptProtocolEntity(
            self.getId(), self.getFrom(), read, participant=self.getParticipant())

    def forward(self, to, _id=None):
        OutgoingMessage = deepcopy(self)
        OutgoingMessage.to = to
        OutgoingMessage._from = None
        OutgoingMessage._id = self._generateId() if _id is None else _id
        return OutgoingMessage
