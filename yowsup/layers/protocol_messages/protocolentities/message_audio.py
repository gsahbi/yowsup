from urllib.request import urlopen

from yowsup.structs import ProtocolTreeNode

from yowsup.common.tools import AudioTools
from .message_downloadable import DownloadableMessageProtocolEntity


class AudioMessageProtocolEntity(DownloadableMessageProtocolEntity):

    crypt_keys = '576861747341707020496d616765204b657973'

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            AudioMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            AudioMessageProtocolEntity.load_properties(self, **kwargs)

        self.crypt_keys = '576861747341707020566964656f204b657973'


    @property
    def duration(self): return self._duration

    @duration.setter
    def duration(self, v):
        self._duration = int(v)


    def __str__(self):
        out = super(AudioMessageProtocolEntity, self).__str__()
        out += "Duration: %ds\n" % self.duration
        return out

    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        assert body is not None and body["type"] == "audio", "Called with wrong body payload"
        data = body.getData()
        self.duration = data["seconds"] if "seconds" in data else None

    def toProtocolTreeNode(self):

        node = super().toProtocolTreeNode()
        bodyNode = node.getChild("body") or ProtocolTreeNode("body", {}, None, None)
        bodyNode["type"] = "audio"

        data = {}

        if self.duration is not None:
            data["seconds"] = self.duration

        data = {**bodyNode.getData(), **data}
        bodyNode.setData(data)

        return node

    @staticmethod
    def fromFilePath(fpath, url, ip, to, mimeType=None, preview=None, filehash=None, filesize=None):
        entity = DownloadableMessageProtocolEntity.fromFilePath(fpath, url,
                                                                DownloadableMessageProtocolEntity.MEDIA_TYPE_AUDIO,
                                                                ip, to, mimeType, preview)
        entity.__class__ = AudioMessageProtocolEntity
        duration = AudioTools.getAudioProperties(fpath)
        entity.setAudioProps(duration=duration)

        return entity
