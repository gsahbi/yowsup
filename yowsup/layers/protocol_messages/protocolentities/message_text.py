from yowsup.structs import ProtocolTreeNode
from .message import MessageProtocolEntity


class TextMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            TextMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            TextMessageProtocolEntity.load_properties(self, **kwargs)

    def __str__(self):
        out = super(TextMessageProtocolEntity, self).__str__()
        out += "Text: %s\n" % self.text
        return out

    @property
    def text(self): return self._text

    @text.setter
    def text(self, v):
        self._text = v

    def toProtocolTreeNode(self):
        node = super().toProtocolTreeNode()
        bodyNode = ProtocolTreeNode("body", {}, None, self.text)
        node.addChild(bodyNode)
        return node

    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        self.text = body.getData()
