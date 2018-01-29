from urllib.request import urlopen

from yowsup.common.tools import AudioTools
from .message_downloadable import DownloadableMessageProtocolEntity


class AudioMessageProtocolEntity(DownloadableMessageProtocolEntity):
    cryptKeys = '576861747341707020417564696f204b657973'

    def __init__(self,
                 mimeType, fileHash, url, ip, size, fileName,
                 abitrate, acodec, asampfreq, duration, encoding, origin, seconds, mediaKey=None,
                 _id=None, _from=None, to=None, notify=None, timestamp=None,
                 participant=None, preview=None, offline=None, retry=None):
        super(AudioMessageProtocolEntity, self).__init__("audio",
                                                         mimeType, fileHash, url, ip, size, fileName, mediaKey,
                                                         _id, _from, to, notify, timestamp, participant, preview,
                                                         offline, retry)

        self.setAudioProps(abitrate, acodec, asampfreq, duration, encoding, origin, seconds)

    def __str__(self):
        out = super(AudioMessageProtocolEntity, self).__str__()
        out += "mimeType: %s\n" % self.mimeType
        out += "Duration: %s\n" % self.duration
        return out

    def setAudioProps(self, duration=None):
        self.duration = duration

    def toProtocolTreeNode(self):
        node = super(AudioMessageProtocolEntity, self).toProtocolTreeNode()
        mediaNode = node.getChild("enc")
        mediaNode.setAttribute("duration", self.duration)
        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = DownloadableMessageProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = AudioMessageProtocolEntity
        mediaNode = node.getChild("body")
        entity.setMimeType(mediaNode.getAttributeValue("mimetype"))
        entity.setAudioProps(
            mediaNode.getAttributeValue("duration")
        )
        return entity

    @staticmethod
    def fromFilePath(fpath, url, ip, to, mimeType=None, preview=None, filehash=None, filesize=None):
        entity = DownloadableMessageProtocolEntity.fromFilePath(fpath, url,
                                                                DownloadableMessageProtocolEntity.MEDIA_TYPE_AUDIO,
                                                                ip, to, mimeType, preview)
        entity.__class__ = AudioMessageProtocolEntity
        duration = AudioTools.getAudioProperties(fpath)
        entity.setAudioProps(duration=duration)

        return entity


    def getMediaContent(self):
        data = urlopen(self.url.decode('ASCII')).read()
        # data = urlopen(self.url).read()
        if self.is_encrypted():
            data = self.decrypt(data, self.mediaKey)
        return bytearray(data)
