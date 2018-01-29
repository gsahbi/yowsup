from yowsup.structs import ProtocolTreeNode
from .message import MessageProtocolEntity


class TextMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, node):
        super(TextMessageProtocolEntity, self).__init__(node)
        body = node.getChild("body")
        self.body = body.getData()


    def __str__(self):
        out = super(TextMessageProtocolEntity, self).__str__()
        out += "Body: %s\n" % self.body
        return out

    def setBody(self, body):
        self.body = body

    def getBody(self):
        return self.body

    def toProtocolTreeNode(self):
        node = super(TextMessageProtocolEntity, self).toProtocolTreeNode()
        bodyNode = ProtocolTreeNode("body", {}, None, self.body)
        node.addChild(bodyNode)
        return node
