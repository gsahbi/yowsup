from .message import MessageProtocolEntity
from yowsup.structs import ProtocolTreeNode


class ExtendedTextMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            ExtendedTextMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            ExtendedTextMessageProtocolEntity.load_properties(self, **kwargs)


    def __str__(self):
        out = super(ExtendedTextMessageProtocolEntity, self).__str__()
        out += "Text: %s\n" % self.text
        out += "Media Type: %s\n" % self.media_type
        out += "Matched Text: %s\n" % self.matched_text
        out += "Canonical URL: %s\n" % self.canonical_url
        out += "Title: %s\n" % self.title
        out += "Description: %s\n" % self.description
        out += "Has Thumnail: %s\n" % ("Yes" if self.jpeg_thumbnail is not None else "No")
        return out

    @property
    def text(self): return self._text

    @text.setter
    def text(self, v): self._text = v



    @property
    def media_type(self): return self._media_type

    @media_type.setter
    def media_type(self, v): self._media_type = v



    @property
    def matched_text(self): return self._matched_text

    @matched_text.setter
    def matched_text(self, v): self._matched_text = v



    @property
    def canonical_url(self): return self._canonical_url

    @canonical_url.setter
    def canonical_url(self, v): self._canonical_url = v



    @property
    def description(self): return self._description

    @description.setter
    def description(self, v): self._description = v


    @property
    def title(self): return self._title

    @title.setter
    def title(self, v): self._title = v


    @property
    def jpeg_thumbnail(self): return self._jpeg_thumbnail

    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, v): self._jpeg_thumbnail = v


    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        enc = node.getChild("enc")
        assert body is not None and body["type"] == "extended_text", "Called with wrong body payload"
        data = body.getData()

        self.media_type = enc["mediatype"] if enc else None
        self.matched_text = data["matched_text"] if "matched_text" in data else None
        self.canonical_url = data["canonical_url"] if "canonical_url" in data else None
        self.description = data["description"] if "description" in data else None
        self.title = data["title"] if "title" in data else None
        self.jpeg_thumbnail = data["jpeg_thumbnail"] if "jpeg_thumbnail" in data else None
        self.text = data["text"] if "text" in data else None

    def toProtocolTreeNode(self):
        node = super().toProtocolTreeNode()

        data = {
            'text': self.text,
            'matched_text': self.matched_text,
            'canonical_url': self.canonical_url,
            'description': self.description,
            'title': self.title,
            'jpeg_thumbnail': self.jpeg_thumbnail,
        }

        attribs = {"type": "extended_text"}
        if self.media_type:
            attribs["mediatype"] = self.media_type

        bodyNode = ProtocolTreeNode("body", attribs, None, data)
        node.addChild(bodyNode)
        return node
