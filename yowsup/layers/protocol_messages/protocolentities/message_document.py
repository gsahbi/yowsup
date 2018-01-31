from urllib.request import urlopen

from yowsup.common.tools import DocumentTools
from yowsup.layers.protocol_messages.proto.wa_pb2 import DocumentMessage
from .builder_message_media_downloadable import DownloadableMediaMessageBuilder
from .message_downloadable import DownloadableMessageProtocolEntity


class DocumentMessageProtocolEntity(DownloadableMessageProtocolEntity):


    def __init__(self,
                 mimeType, fileHash, url, ip, size, fileName, pageCount,
                 encoding=None, width=None, height=None, caption=None, mediaKey=None,
                 _id=None, _from=None, to=None, notify=None, timestamp=None,
                 participant=None, preview=None, offline=None, retry=None):

        super(DocumentMessageProtocolEntity, self).__init__("document",
                                                            mimeType, fileHash, url, ip, size, fileName, pageCount,
                                                            mediaKey,
                                                            _id, _from, to, notify, timestamp, participant, preview,
                                                            offline, retry)
        self.setDocumentProps(pageCount)

    def __str__(self):
        out = super(DocumentMessageProtocolEntity, self).__str__()
        out += "Encoding: %s\n" % self.encoding
        # out += "Width: %s\n" % self.width
        # out += "Height: %s\n" % self.height
        if self.caption:
            out += "Caption: %s\n" % self.caption
        return out

    def setDocumentProps(self, pageCount):
        self.pageCount = str(pageCount)
        self.cryptKeys = '576861747341707020446f63756d656e74204b657973'

    def setFileName(self, fileName):
        self.fileName = fileName

    def getFileName(self):
        return self.fileName

    def getCaption(self):
        return self.caption

    def toProtocolTreeNode(self):
        node = super(DocumentMessageProtocolEntity, self).toProtocolTreeNode()
        mediaNode = node.getChild("enc")
        mediaNode.setAttribute("pageCount", str(self.pageCount))
        return node

    def toProtobufMessage(self):
        document_message = DocumentMessage()
        document_message.url = self.url
        document_message.mime_type = self.mimeType  # "application/pdf"
        document_message.title = self.fileName
        document_message.file_sha256 = self.fileHash
        document_message.file_length = self.size
        document_message.page_count = self.pageCount;
        document_message.media_key = self.mediaKey
        document_message.jpeg_thumbnail = self.preview

        return document_message

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = DownloadableMessageProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = DocumentMessageProtocolEntity
        mediaNode = node.getChild("media")
        entity.setFileName(mediaNode.getAttributeValue("title"))
        entity.setDocumentProps(
            mediaNode.getAttributeValue("encoding")
        )
        return entity

    @staticmethod
    def getBuilder(jid, filepath):
        return DownloadableMediaMessageBuilder(DocumentMessageProtocolEntity, jid, filepath)

    @staticmethod
    def fromBuilder(builder):
        builder.getOrSet("preview", lambda: DocumentTools.generatePreviewFromDocument(builder.getOriginalFilepath()))
        pageCount = DocumentTools.getDocumentProperties(builder.getOriginalFilepath())
        entity = DownloadableMessageProtocolEntity.fromBuilder(builder)
        entity.__class__ = builder.cls
        entity.setDocumentProps(pageCount)
        return entity

    @staticmethod
    def fromFilePath(path, url, ip, to, mimeType=None):
        builder = DocumentMessageProtocolEntity.getBuilder(to, path)
        builder.set("url", url)
        builder.set("ip", ip)
        builder.set("mimetype", mimeType)
        return DocumentMessageProtocolEntity.fromBuilder(builder)

    def unpad(self, s):
        return s[:-ord(s[len(s) - 1:])]


    def is_encrypted(self):
        return self.cryptKeys and self.mediaKey

    def getMediaContent(self):
        data = urlopen(self.url.decode('ASCII')).read()
        if self.is_encrypted():
            data = self.decrypt(data, self.mediaKey)
        return data
