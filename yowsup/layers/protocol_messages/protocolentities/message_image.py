from yowsup.common.tools import ImageTools
from yowsup.layers.protocol_messages.proto.wa_pb2 import ImageMessage
from .builder_message_media_downloadable import DownloadableMediaMessageBuilder
from .message_downloadable import DownloadableMessageProtocolEntity


class ImageMessageProtocolEntity(DownloadableMessageProtocolEntity):

    crypt_keys = '576861747341707020496d616765204b657973'

    def __init__(self, node):

        super(ImageMessageProtocolEntity, self).__init__(node)
        self.setImageProps(**node.getChild("body").data)


    def __str__(self):
        out = super(ImageMessageProtocolEntity, self).__str__()
        out += "Width: %s\n" % self.width
        out += "Height: %s\n" % self.height
        if self.caption:
            out += "Caption: %s\n" % self.caption
        return out

    def setImageProps(self, jpeg_thumbnail=None, width='0', height='0', caption=None, **kwargs):
        self.jpeg_thumbnail = jpeg_thumbnail
        self.width = int(width)
        self.height = int(height)
        self.caption = caption


    def getCaption(self):
        return self.caption

    def toProtocolTreeNode(self):
        node = super(ImageMessageProtocolEntity, self).toProtocolTreeNode()
        mediaNode = node.getChild("enc")

        mediaNode.setAttribute("width", str(self.width))
        mediaNode.setAttribute("height", str(self.height))
        if self.caption:
            mediaNode.setAttribute("caption", self.caption)

        return node

    def toProtobufMessage(self):
        image_message = ImageMessage()
        image_message.url = self.url
        image_message.width = self.width
        image_message.height = self.height
        image_message.mime_type = self.mimeType
        image_message.file_sha256 = self.fileHash
        image_message.file_length = self.size
        image_message.caption = self.caption
        image_message.jpeg_thumbnail = self.preview
        image_message.media_key = self.mediaKey

        return image_message

    @staticmethod
    def getBuilder(jid, filepath):
        return DownloadableMediaMessageBuilder(ImageMessageProtocolEntity, jid, filepath)

    @staticmethod
    def fromBuilder(builder):
        builder.getOrSet("preview", lambda: ImageTools.generatePreviewFromImage(builder.getOriginalFilepath()))
        filepath = builder.getFilepath()
        caption = builder.get("caption")
        mimeType = builder.get("mimetype")
        dimensions = builder.get("dimensions", ImageTools.getImageDimensions(builder.getOriginalFilepath()))
        assert dimensions, "Could not determine image dimensions"
        width, height = dimensions

        entity = DownloadableMessageProtocolEntity.fromBuilder(builder)
        entity.__class__ = builder.cls
        entity.setImageProps("raw", width, height, caption)
        return entity

    @staticmethod
    def fromFilePath(path, url, ip, to, mimeType=None, caption=None, dimensions=None):
        builder = ImageMessageProtocolEntity.getBuilder(to, path)
        builder.set("url", url)
        builder.set("ip", ip)
        builder.set("caption", caption)
        builder.set("mimetype", mimeType)
        builder.set("dimensions", dimensions)
        return ImageMessageProtocolEntity.fromBuilder(builder)
