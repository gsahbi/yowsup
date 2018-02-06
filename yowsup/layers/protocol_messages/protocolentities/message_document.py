from yowsup.structs import ProtocolTreeNode
from .message_downloadable import DownloadableMessageProtocolEntity


class DocumentMessageProtocolEntity(DownloadableMessageProtocolEntity):

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            DocumentMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            DocumentMessageProtocolEntity.load_properties(self, **kwargs)

        self.crypt_keys = '576861747341707020446f63756d656e74204b657973'


    @property
    def title(self): return self._title

    @title.setter
    def title(self, v):
        self._title = v


    @property
    def page_count(self): return self._page_count

    @page_count.setter
    def page_count(self, v):
        self._page_count = int(v)


    @property
    def file_name(self): return self._file_name

    @file_name.setter
    def file_name(self, v):
        self._file_name = v


    @property
    def jpeg_thumbnail(self): return self._jpeg_thumbnail

    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, v):
        self._jpeg_thumbnail = v


    def __str__(self):
        out = super().__str__()

        if self.title:
            out += "Title: %s\n" % self.title
        if self.page_count:
            out += "Page Count: %s\n" % self.page_count
        if self.file_name:
            out += "File Name: %s\n" % self.file_name
        return out



    def toProtocolTreeNode(self):
        node = super().toProtocolTreeNode()
        bodyNode = node.getChild("body") or ProtocolTreeNode("body", {}, None, None)
        bodyNode["type"] = "document"

        data = {
            'title': self.title,
            'page_count': self.page_count,
            'file_name': self.file_name,
            'jpeg_thumbnail': self.jpeg_thumbnail
        }

        data = {**bodyNode.getData(), **data}
        bodyNode.setData(data)
        return node

    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        data = body.getData()
        self.title = data["title"] if "title" in data else None
        self.page_count = data["page_count"] if "page_count" in data else 0
        self.file_name = data["file_name"] if "file_name" in data else None
        self.jpeg_thumbnail = data["jpeg_thumbnail"] if "jpeg_thumbnail" in data else None

    @staticmethod
    def fromFilePath(path, url, ip, to, mimeType=None):
        builder = DocumentMessageProtocolEntity.getBuilder(to, path)
        builder.set("url", url)
        builder.set("ip", ip)
        builder.set("mimetype", mimeType)
        return DocumentMessageProtocolEntity.fromBuilder(builder)
