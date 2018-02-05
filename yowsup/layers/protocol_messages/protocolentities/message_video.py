from yowsup.structs import ProtocolTreeNode

from yowsup.common.tools import VideoTools
from .message_downloadable import DownloadableMessageProtocolEntity


class VideoMessageProtocolEntity(DownloadableMessageProtocolEntity):

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            VideoMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            VideoMessageProtocolEntity.load_properties(self, **kwargs)

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
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, v):
        self._duration = int(v)

    @property
    def jpeg_thumbnail(self):
        return self._jpeg_thumbnail

    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, v):
        self._jpeg_thumbnail = v

    def __str__(self):
        out = super(VideoMessageProtocolEntity, self).__str__()
        out += "Duration: %s\n" % self.duration
        out += "Width: %s\n" % self.width
        out += "Height: %s\n" % self.height
        if self.caption is not None:
            out += "Caption: %s\n" % self.caption
        return out

    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        assert body is not None and body["type"] == "video", "Called with wrong body payload"
        data = body.getData()

        self.duration = data["seconds"] if "seconds" in data else None
        self.width = data["width"] if "width" in data else None
        self.height = data["height"] if "height" in data else None
        self.caption = data["caption"] if "caption" in data else None
        self.jpeg_thumbnail = data["jpeg_thumbnail"] if "jpeg_thumbnail" in data else None

    def toProtocolTreeNode(self):

        node = super().toProtocolTreeNode()
        bodyNode = node.getChild("body") or ProtocolTreeNode("body", {}, None, None)

        bodyNode["type"] = "video"
        bodyNode["mediatype"] = "video"

        data = {
            "height": self.height,
            "width": self.width,
            "jpeg_thumbnail": self.jpeg_thumbnail
        }

        if self.duration is not None:
            data["seconds"] = self.duration

        if self.caption is not None:
            data["caption"] = self.caption

        data = {**bodyNode.getData(), **data}
        bodyNode.setData(data)

        return node

    @staticmethod
    def fromFilePath(path, caption=None):
        preview = VideoTools.generatePreviewFromVideo(path)
        entity = DownloadableMessageProtocolEntity.fromFilePath(path, url,
                                                                DownloadableMessageProtocolEntity.MEDIA_TYPE_VIDEO,
                                                                ip, to, mimeType, preview)
        entity.__class__ = VideoMessageProtocolEntity

        width, height, bitrate, duration = VideoTools.getVideoProperties(path)
        assert width, "Could not determine video properties"

        duration = int(duration)
        entity.setVideoProps('raw', width, height, duration=duration, seconds=duration, caption=caption)
        return entity
