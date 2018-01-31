from yowsup.structs import ProtocolTreeNode
from .message import MessageProtocolEntity


class TextMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, node):
        super(TextMessageProtocolEntity, self).__init__(node)
        body = node.getChild("body")
        self.text = body.getData()

    def __str__(self):
        out = super(TextMessageProtocolEntity, self).__str__()
        out += "Text: %s\n" % self.text
        return out

    def setText(self, text):
        self.text = text

    def getText(self):
        return self.text

    @staticmethod
    def buildTextMessage(text, _id=None, _from=None, to=None, notify=None,
                         timestamp=None, participant=None, offline=None, retry=None):
        node = TextMessageProtocolEntity.__new__(TextMessageProtocolEntity)
        super(TextMessageProtocolEntity, node).build(_type="text", _id=_id, _from=_from, to=to, notify=notify,
                                                     timestamp=timestamp, participant=participant,
                                                     offline=offline, retry=retry)
        node.setText(text)
        return node

    def toProtocolTreeNode(self):
        node = super(TextMessageProtocolEntity, self).toProtocolTreeNode()
        bodyNode = ProtocolTreeNode("body", {}, None, self.text)
        node.addChild(bodyNode)
        return node
