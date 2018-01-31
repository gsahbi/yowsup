from .message import MessageProtocolEntity
from yowsup.structs import ProtocolTreeNode


class ExtendedTextMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, node):
        super(ExtendedTextMessageProtocolEntity, self).__init__(node)
        self.setExtendedTextProps(**node.getChild("body").data)

    def __str__(self):
        out = super(ExtendedTextMessageProtocolEntity, self).__str__()
        out += "Text: %s\n" % self.text
        out += "Matched Text: %s\n" % self.matched_text
        out += "Canonical URL: %s\n" % self.canonical_url
        out += "Title: %s\n" % self.title
        out += "Description: %s\n" % self.description
        out += "Has Thumnail: %s\n" % ("Yes" if self.jpeg_thumbnail is not None else "No")
        return out

    def getText(self):
        return self.text

    def setExtendedTextProps(self, text, matched_text=None, canonical_url=None,
                             description=None, title=None, jpeg_thumbnail=None, **kwargs):
        self.text = text
        self.matched_text = matched_text
        self.canonical_url = canonical_url
        self.description = description
        self.title = title
        self.jpeg_thumbnail = jpeg_thumbnail


    def fromProtocolTreeNode(self, node):
        super(ExtendedTextMessageProtocolEntity, self).__init__(node)
        self.setExtendedTextProps(**node.getChild("body").data)


    def toProtocolTreeNode(self):
        node = super(ExtendedTextMessageProtocolEntity, self).toProtocolTreeNode()
        mediaNode = node.getChild("enc")
        mediaNode["type"] = "vcard"
        vcardNode = ProtocolTreeNode("vcard", {"name": self.name}, None, self.card_data)
        mediaNode.addChild(vcardNode)
        return node
