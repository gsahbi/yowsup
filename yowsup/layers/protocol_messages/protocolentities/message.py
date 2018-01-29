from copy import deepcopy

from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.structs import ProtocolEntity


class MessageProtocolEntity(ProtocolEntity):

    MESSAGE_TYPE_TEXT = "text"
    MESSAGE_TYPE_MEDIA = "media"

    def __init__(self, node):

        super(MessageProtocolEntity, self).__init__("message")
        offline = node.getAttributeValue('offline')
        retry = node.getAttributeValue('retry')
        self._type = node.getAttributeValue('type')
        self._id = node.getAttributeValue('id') or self._generateId()
        self._from = node.getAttributeValue('from')
        self.to = node.getAttributeValue('to')
        self.timestamp = int(node.getAttributeValue('t')) or self._getCurrentTimestamp()
        self.notify = node.getAttributeValue('notify')
        self.offline = offline == "1" if offline is not None else offline
        self.retry = int(retry) if retry else None
        self.participant = node.getAttributeValue('participant')

        assert (self.to or self._from), "Must specify either to or _from jids to create the message"
        assert not (self.to and self._from), "Can't set both attributes to message at same time (to, _from)"


    def getType(self):
        return self._type

    def getId(self):
        return self._id

    def getTimestamp(self):
        return self.timestamp

    def getFrom(self, full=True):
        return self._from if full else self._from.split('@')[0]

    def isBroadcast(self):
        return False

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
        return self.participant != None

    def __str__(self):
        out = "Message:\n"
        out += "ID: %s\n" % self._id
        out += "To: %s\n" % self.to if self.isOutgoing() else "From: %s\n" % self._from
        out += "Type:  %s\n" % self._type
        out += "Timestamp: %s\n" % self.timestamp
        if self.participant:
            out += "Participant: %s\n" % self.participant
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
