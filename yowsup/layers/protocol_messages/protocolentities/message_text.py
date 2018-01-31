from yowsup.structs import ProtocolTreeNode
from .message import MessageProtocolEntity


class TextMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, text, _id=None, _from=None, to=None, notify=None,
                 timestamp=None, participant=None, offline=None, retry=None, context=None):
        super(TextMessageProtocolEntity, self).__init__(_type="text", _id=_id, _from=_from, to=to, notify=notify,
                                                        timestamp=timestamp, participant=participant,
                                                        offline=offline, retry=retry, context=context)
        self.setText(text)

    def __str__(self):
        out = super(TextMessageProtocolEntity, self).__str__()
        out += "Text: %s\n" % self.text
        return out

    def setText(self, text):
        self.text = text

    def getText(self):
        return self.text

    def toProtocolTreeNode(self):
        node = super(TextMessageProtocolEntity, self).toProtocolTreeNode()
        bodyNode = ProtocolTreeNode("body", {}, None, self.text)
        node.addChild(bodyNode)
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = MessageProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = TextMessageProtocolEntity
        body = node.getChild("body")
        entity.text = body.getData()
        return entity
