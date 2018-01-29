import logging

from yowsup.layers import YowProtocolLayer
from yowsup.layers.protocol_iq.protocolentities import IqProtocolEntity, ErrorIqProtocolEntity
from yowsup.layers.protocol_messages.protocolentities import ResultRequestUploadIqProtocolEntity
from .protocolentities import TextMessageProtocolEntity, ExtendedTextMessageProtocolEntity, ImageMessageProtocolEntity, \
    AudioMessageProtocolEntity, VideoMessageProtocolEntity, DocumentMessageProtocolEntity, \
    LocationMessageProtocolEntity, \
    ContactMessageProtocolEntity  # , ContactArrayMessageProtocolEntity

logger = logging.getLogger(__name__)


class YowMessagesProtocolLayer(YowProtocolLayer):
    def __init__(self):
        handleMap = {
            "message": (self.recvMessageStanza, self.sendMessageEntity),
            "iq": (self.recvIq, self.sendIq)
        }
        super(YowMessagesProtocolLayer, self).__init__(handleMap)

    def __str__(self):
        return "Messages Layer"

    def sendMessageEntity(self, entity):
        if entity.getType() == "message":
            self.entityToLower(entity)

    def recvMessageStanza(self, node):

        if node.getAttributeValue("type") == "text":
            entity = TextMessageProtocolEntity(node)
            self.toUpper(entity)

        elif node.getAttributeValue("type") == "media":
            message = node.getChild("body")
            message_type = message.getAttributeValue("type")

            if message_type == "extended_text":
                entity = ExtendedTextMessageProtocolEntity(node)
            elif message_type == "image":
                entity = ImageMessageProtocolEntity(node)
            elif message_type == "audio":
                entity = AudioMessageProtocolEntity(node)
            elif message_type == "video":
                entity = VideoMessageProtocolEntity(node)
            elif message_type == "document":
                entity = DocumentMessageProtocolEntity(node)
            elif message_type == "location":
                entity = LocationMessageProtocolEntity(node)
            elif message_type == "contact":
                entity = ContactMessageProtocolEntity(node)
            elif message_type == "contact_array":
                entity = ContactMessageProtocolEntity(node)
            else:
                logger.debug("Unrecognized message type %s " % message_type)
                return

            self.toUpper(entity)

    def sendIq(self, entity):
        """
        :type entity: IqProtocolEntity
        """
        if entity.getType() == IqProtocolEntity.TYPE_SET and entity.getXmlns() == "w:m":
            # media upload!
            self._sendIq(entity, self.onRequestUploadSuccess, self.onRequestUploadError)

    def recvIq(self, entity):
        pass

    def onRequestUploadSuccess(self, resultNode, requestUploadEntity):
        self.toUpper(ResultRequestUploadIqProtocolEntity.fromProtocolTreeNode(resultNode))

    def onRequestUploadError(self, errorNode, requestUploadEntity):
        self.toUpper(ErrorIqProtocolEntity.fromProtocolTreeNode(errorNode))
