from urllib.request import urlopen

from yowsup.common.tools import AudioTools
from .message_downloadable import DownloadableMessageProtocolEntity


class AudioMessageProtocolEntity(DownloadableMessageProtocolEntity):

    crypt_keys = '576861747341707020496d616765204b657973'

    def __init__(self, node):
        super(AudioMessageProtocolEntity, self).__init__(node)
        self.setAudioProps(**node.getChild("body").data)

    def __str__(self):
        out = super(AudioMessageProtocolEntity, self).__str__()
        out += "Duration: %s\n" % self.seconds
        return out

    def setAudioProps(self, seconds=None, **kwargs):
        self.seconds = seconds

    def toProtocolTreeNode(self):
        node = super(AudioMessageProtocolEntity, self).toProtocolTreeNode()
        mediaNode = node.getChild("enc")
        mediaNode.setAttribute("duration", self.duration)
        return node

    # @staticmethod
    # def fromProtocolTreeNode(node):
    #     entity = DownloadableMessageProtocolEntity.fromProtocolTreeNode(node)
    #     entity.__class__ = AudioMessageProtocolEntity
    #     mediaNode = node.getChild("body")
    #     entity.setMimeType(mediaNode.getAttributeValue("mimetype"))
    #     entity.setAudioProps(
    #         mediaNode.getAttributeValue("duration")
    #     )
    #     return entity

    @staticmethod
    def fromFilePath(fpath, url, ip, to, mimeType=None, preview=None, filehash=None, filesize=None):
        entity = DownloadableMessageProtocolEntity.fromFilePath(fpath, url,
                                                                DownloadableMessageProtocolEntity.MEDIA_TYPE_AUDIO,
                                                                ip, to, mimeType, preview)
        entity.__class__ = AudioMessageProtocolEntity
        duration = AudioTools.getAudioProperties(fpath)
        entity.setAudioProps(duration=duration)

        return entity
