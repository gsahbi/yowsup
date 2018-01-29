from yowsup.layers.protocol_messages.protocolentities import MessageProtocolEntity

from yowsup.structs import ProtocolTreeNode


class ContactMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, name, card_data, _id=None, _from=None, to=None, notify=None, timestamp=None, participant=None,
                 preview=None, offline=None, retry=None):
        super(ContactMessageProtocolEntity, self).__init__("Contact", _id, _from, to, notify, timestamp, participant,
                                                           preview, offline, retry)
        self.setContactMediaProps(name, card_data)

    def __str__(self):
        out = super(MessageProtocolEntity, self).__str__()
        out += "Name: %s\n" % self.name
        out += "Card Data: %s\n" % self.card_data
        return out

    def getName(self):
        return self.name

    def getCardData(self):
        return self.card_data

    def setContactMediaProps(self, name, card_data):
        self.name = name
        self.card_data = card_data

    def toProtocolTreeNode(self):
        node = super(ContactMessageProtocolEntity, self).toProtocolTreeNode()
        mediaNode = node.getChild("enc")
        mediaNode["type"] = "contact"
        ContactNode = ProtocolTreeNode("contact", {"name": self.name}, None, self.card_data)
        mediaNode.addChild(ContactNode)
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = MessageProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = ContactMessageProtocolEntity
        mediaNode = node.getChild("media")
        entity.setContactMediaProps(
            mediaNode.getAllChildren()[0].getAttributeValue('name'),
            mediaNode.getChild("Contact").getData()
        )
        return entity
