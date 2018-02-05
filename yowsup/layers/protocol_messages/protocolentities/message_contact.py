from yowsup.layers.protocol_messages.protocolentities import MessageProtocolEntity

from yowsup.structs import ProtocolTreeNode


class ContactMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            ContactMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            ContactMessageProtocolEntity.load_properties(self, **kwargs)

    @property
    def caption(self): return self._caption

    @caption.setter
    def caption(self, v):
        self._caption = v


    @property
    def vcards(self): return self._vcards

    @vcards.setter
    def vcards(self, v):
        self._vcards = v


    def __str__(self):
        out = super().__str__()
        count = 1
        out += "%d Contacts:\n" % len(self.vcards)
        for card in self.vcards:
            out += "\t%d.Name: %s\n" % (count, card['display_name'])
            out += "\t%d.Card Data: %s\n" % (count, card['vcard'])
            count += 1

        return out

    def toProtocolTreeNode(self):
        node = super().toProtocolTreeNode()
        mediaNode = node.getChild("enc")
        mediaNode["type"] = "contact"
        ContactNode = ProtocolTreeNode("contact", {"name": self.name}, None, self.card_data)
        mediaNode.addChild(ContactNode)
        return node

    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        assert body is not None and body["type"] in ("contact_array", "contact"), "Called with wrong body payload"
        data = body.getData()
        self.caption = data["display_name"] if "display_name" in data else None

        if body["type"] == "contact":
            assert type(data["contact"]) == str, "Wrong type of contact data received.."
            self.vcards = [{
                'display_name': data["display_name"] if "display_name" in data else None,
                'vcard': data["contact"] if "vcard" in data else None
            }]
        else:
            assert type(data["contact"]) == list, "Contact data should be list.."
            self.vcards = list(data["contact"])



