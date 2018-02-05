from yowsup.structs import ProtocolTreeNode

from yowsup.common.tools import ImageTools
from .message_downloadable import DownloadableMessageProtocolEntity


class ImageMessageProtocolEntity(DownloadableMessageProtocolEntity):

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            ImageMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            ImageMessageProtocolEntity.load_properties(self, **kwargs)
        self.crypt_keys = '576861747341707020566964656f204b657973'

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, v):
        self._height = int(v)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, v):
        self._width = int(v)

    @property
    def caption(self):
        return self._caption

    @caption.setter
    def caption(self, v):
        self._caption = v

    @property
    def jpeg_thumbnail(self):
        return self._jpeg_thumbnail

    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, v):
        self._jpeg_thumbnail = v

    def __str__(self):
        out = super(ImageMessageProtocolEntity, self).__str__()
        out += "Width: %s\n" % self.width
        out += "Height: %s\n" % self.height
        if self.caption:
            out += "Caption: %s\n" % self.caption
        return out

    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        assert body is not None and body["type"] == "image", "Called with wrong body payload"
        data = body.getData()

        self.width = data["width"] if "width" in data else None
        self.height = data["height"] if "height" in data else None
        self.caption = data["caption"] if "caption" in data else None
        self.jpeg_thumbnail = data["jpeg_thumbnail"] if "jpeg_thumbnail" in data else None

    def getCaption(self):
        return self.caption

    def toProtocolTreeNode(self):
        node = super().toProtocolTreeNode()
        bodyNode = node.getChild("body") or ProtocolTreeNode("body", {}, None, None)

        bodyNode["type"] = "image"
        bodyNode["mediatype"] = "image"

        data = {
            "heigh": self.height,
            "width": self.width,
            "jpeg_thumbnail": self.jpeg_thumbnail
        }

        if self.caption is not None:
            data["caption"] = str(self.caption)

        data = {**bodyNode.getData(), **data}
        bodyNode.setData(data)

        return node

    @staticmethod
    def fromFilePath(fpath, caption=None):

        preview = ImageTools.generatePreviewFromImage(fpath)
        dimensions = ImageTools.getImageDimensions(fpath)
        assert dimensions, "Could not determine image dimensions"
        width, height = dimensions
        entity = DownloadableMessageProtocolEntity("raw", width, height, caption)
        return entity
