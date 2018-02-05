# -*- coding utf-8 -*-
import logging
from random import randint

import os
from axolotl.axolotladdress import AxolotlAddress
from axolotl.groups.groupcipher import GroupCipher
from axolotl.groups.groupsessionbuilder import GroupSessionBuilder
from axolotl.groups.senderkeyname import SenderKeyName
from axolotl.protocol.whispermessage import WhisperMessage
from axolotl.sessioncipher import SessionCipher

from yowsup.common.protobuf_to_dict.convertor import dict_to_protobuf
from yowsup.common.tools import Jid
from yowsup.layers.auth.layer_authentication import YowAuthenticationProtocolLayer
from yowsup.layers.axolotl.protocolentities import *
from yowsup.layers.protocol_groups.protocolentities import InfoGroupsIqProtocolEntity, InfoGroupsResultIqProtocolEntity
from yowsup.layers.protocol_messages.proto.wa_pb2 import *
from .layer_base import AxolotlBaseLayer

logger = logging.getLogger(__name__)


class AxolotlSendLayer(AxolotlBaseLayer):
    MAX_SENT_QUEUE = 100

    def __init__(self):
        super(AxolotlSendLayer, self).__init__()

        self.sessionCiphers = {}
        self.groupSessionBuilder = None
        self.groupCiphers = {}

        # Sent messages will be put in skalti entQueue until we receive a receipt for them.
        # This is for handling retry receipts which requires re-encrypting and resend of the original message
        # As the receipt for a sent message might arrive at a different yowsup instance,
        # ideally the original message should be fetched from a persistent storage.
        # Therefore, if the original message is not in sentQueue for any reason, we will
        # notify the upper layers and let them handle it.
        self.sentQueue = []

    def onNewStoreSet(self, store):
        if store is not None:
            self.groupSessionBuilder = GroupSessionBuilder(store)

    def __str__(self):
        return "Axolotl Layer"

    def handleEncNode(self, node):
        recipient_id = node["to"].split('@')[0]
        v2 = node["to"]
        if node.getChild("enc"):  # media enc is only for v2 messsages
            if '-' in recipient_id:  # Handle Groups
                def getResultNodes(resultNode, _requestEntity):
                    groupInfo = InfoGroupsResultIqProtocolEntity.fromProtocolTreeNode(resultNode)
                    jids = list(groupInfo.getParticipants().keys())  # keys in py3 returns dict_keys
                    jids.remove(self.getLayerInterface(YowAuthenticationProtocolLayer).getUsername(True))
                    jidsNoSession = []
                    for jid in jids:
                        if not self.store.containsSession(jid.split('@')[0], 1):
                            jidsNoSession.append(jid)
                    if len(jidsNoSession):
                        self.getKeysFor(jidsNoSession,
                                        lambda successJids, b: self.sendToGroupWithSessions(node, successJids))
                    else:
                        self.sendToGroupWithSessions(node, jids)

                groupInfoIq = InfoGroupsIqProtocolEntity(Jid.normalize(node["to"]))
                self._sendIq(groupInfoIq, getResultNodes)
            else:
                messageData = self.serializeToProtobuf(node)
                if messageData:
                    if not self.store.containsSession(recipient_id, 1):
                        def on_get_keys(successJids, _b):
                            if len(successJids) == 1:
                                self.sendToContact(node)
                            else:
                                self.toLower(node)

                        self.getKeysFor([node["to"]], on_get_keys, lambda: self.toLower(node))
                    else:
                        sessionCipher = self.getSessionCipher(recipient_id)
                        messageData = messageData + self.getPadding()
                        ciphertext = sessionCipher.encrypt(messageData)
                        mediaType = node.getChild("enc")["type"] if node.getChild("enc") else None
                        if ciphertext.__class__ == WhisperMessage:
                            enc_type = EncProtocolEntity.TYPE_MSG
                        else:
                            enc_type = EncProtocolEntity.TYPE_PKMSG
                        encEntity = EncryptedMessageProtocolEntity(
                            [
                                EncProtocolEntity(
                                    enc_type,
                                    2 if v2 else 1,
                                    ciphertext.serialize(), mediaType)
                            ],
                            "text" if not mediaType else "media",
                            _id=node["id"],
                            to=node["to"],
                            notify=node["notify"],
                            timestamp=node["timestamp"],
                            participant=node["participant"],
                            offline=node["offline"],
                            retry=node["retry"]
                        )
                        self.toLower(encEntity.toProtocolTreeNode())
                else:  # case of unserializable messages (audio, video) ?
                    self.toLower(node)
        else:
            self.toLower(node)

    def send(self, node):
        if node.tag == "message" and node["to"] not in self.skipEncJids and not node.getChild("enc"):
            self.processMessageAndSend(node)
        elif node.getChild("enc"):
            self.handleEncNode(node)
        else:
            self.toLower(node)

    def receive(self, protocolTreeNode):
        if not self.processIqRegistry(protocolTreeNode):
            if protocolTreeNode.tag == "receipt":
                # Going to keep all group message enqueued, as we get receipts from each participant
                # So can't just remove it on first receipt. Therefore, the MAX queue length mechanism
                # should better be working
                messageNode = self.getEnqueuedMessageNode(protocolTreeNode["id"],
                                                          protocolTreeNode["participant"] is not None)
                if not messageNode:
                    logger.debug("Axolotl layer does not have the message, bubbling it upwards")
                    self.toUpper(protocolTreeNode)
                elif protocolTreeNode["type"] == "retry":
                    logger.info(
                        "Got retry to for message %s, and Axolotl layer has the message" % protocolTreeNode["id"])
                    retryReceiptEntity = RetryIncomingReceiptProtocolEntity.fromProtocolTreeNode(protocolTreeNode)
                    self.toLower(retryReceiptEntity.ack().toProtocolTreeNode())
                    self.getKeysFor(
                        [protocolTreeNode["participant"] or protocolTreeNode["from"]],
                        lambda successJids, b: self.processMessageAndSend(messageNode, retryReceiptEntity) if len(
                            successJids) == 1 else None,
                        errorClbk=lambda errorNode, getKeysEntity: logger.error("Failed at getting keys during retry")
                    )
                else:
                    # not interested in any non retry receipts, bubble upwards
                    self.toUpper(protocolTreeNode)

    def processMessageAndSend(self, node, retryReceiptEntity=None):
        recipient_id = node["to"].split('@')[0]
        isGroup = "-" in recipient_id

        if isGroup:
            self.sendToGroup(node, retryReceiptEntity)
        elif self.store.containsSession(recipient_id, 1):
            self.sendToContact(node)
        else:
            self.getKeysFor([node["to"]],
                            lambda successJids, b: self.sendToContact(node) if len(successJids) == 1 else self.toLower(
                                node), lambda: self.toLower(node))

    def enqueueSent(self, node):
        if len(self.sentQueue) >= self.__class__.MAX_SENT_QUEUE:
            logger.warning("Discarding queued node without receipt")
            self.sentQueue.pop(0)
        self.sentQueue.append(node)

    def getEnqueuedMessageNode(self, messageId, keepEnqueued=False):
        for i in range(0, len(self.sentQueue)):
            if self.sentQueue[i]["id"] == messageId:
                if keepEnqueued:
                    return self.sentQueue[i]
                return self.sentQueue.pop(i)

    def sendEncEntities(self, node, encEntities):
        messageEntity = EncryptedMessageProtocolEntity(node, encEntities)
        self.enqueueSent(node)
        self.toLower(messageEntity.toProtocolTreeNode())

    def sendToContact(self, node):
        recipient_id = node["to"].split('@')[0]
        cipher = self.getSessionCipher(recipient_id)
        messageData = self.serializeToProtobuf(node) + self.getPadding()
        ciphertext = cipher.encrypt(messageData)
        mediaType = node.getChild("body")["mediatype"] if node.getChild("body") else None

        return self.sendEncEntities(node, [EncProtocolEntity(
            EncProtocolEntity.TYPE_MSG if ciphertext.__class__ == WhisperMessage else EncProtocolEntity.TYPE_PKMSG, 2,
            ciphertext.serialize(), mediaType)])

    def sendToGroupWithSessions(self, node, jidsNeedSenderKey=None, retryCount=0):
        jidsNeedSenderKey = jidsNeedSenderKey or []
        groupJid = node["to"]
        ownNumber = self.getLayerInterface(YowAuthenticationProtocolLayer).getUsername(False)
        senderKeyName = SenderKeyName(groupJid, AxolotlAddress(ownNumber, 0))
        cipher = self.getGroupCipher(groupJid, ownNumber)
        encEntities = []
        if len(jidsNeedSenderKey):
            senderKeyDistributionMessage = self.groupSessionBuilder.create(senderKeyName)
            for jid in jidsNeedSenderKey:
                sessionCipher = self.getSessionCipher(jid.split('@')[0])
                skdm = self.serializeSKDM(node["to"], senderKeyDistributionMessage)
                message = self.serializeToProtobuf(node if retryCount > 0 else None, skdm)
                ciphertext = sessionCipher.encrypt(message + self.getPadding())
                if ciphertext.__class__ == WhisperMessage:
                    enc_type = EncProtocolEntity.TYPE_MSG
                else:
                    enc_type = EncProtocolEntity.TYPE_PKMSG
                encEntities.append(EncProtocolEntity(enc_type, 2, ciphertext.serialize(), jid=jid))

        if not retryCount:
            messageData = self.serializeToProtobuf(node)
            ciphertext = cipher.encrypt(messageData + self.getPadding())
            mediaType = node.getChild("body")["mediatype"] if node.getChild("body") else None
            encEntities.append(EncProtocolEntity(EncProtocolEntity.TYPE_SKMSG, 2, ciphertext, mediaType))

        self.sendEncEntities(node, encEntities)

    def ensureSessionsAndSendToGroup(self, node, jids):
        jidsNoSession = []
        for jid in jids:
            if not self.store.containsSession(jid.split('@')[0], 1):
                jidsNoSession.append(jid)

        if len(jidsNoSession):
            self.getKeysFor(jidsNoSession, lambda successJids, b: self.sendToGroupWithSessions(node, successJids))
        else:
            self.sendToGroupWithSessions(node, jids)

    def sendToGroup(self, node, retryReceiptEntity=None):
        groupJid = node["to"]
        ownNumber = self.getLayerInterface(YowAuthenticationProtocolLayer).getUsername(False)
        ownJid = self.getLayerInterface(YowAuthenticationProtocolLayer).getUsername(True)
        senderKeyName = SenderKeyName(node["to"], AxolotlAddress(ownNumber, 0))
        senderKeyRecord = self.store.loadSenderKey(senderKeyName)

        def sendToGroup(resultNode, _requestEntity):
            groupInfo = InfoGroupsResultIqProtocolEntity.fromProtocolTreeNode(resultNode)
            jids = list(groupInfo.getParticipants().keys())  # keys in py3 returns dict_keys
            jids.remove(ownJid)
            return self.ensureSessionsAndSendToGroup(node, jids)

        if senderKeyRecord.isEmpty():
            groupInfoIq = InfoGroupsIqProtocolEntity(groupJid)
            self._sendIq(groupInfoIq, sendToGroup)
        else:
            retryCount = 0
            jidsNeedSenderKey = []
            if retryReceiptEntity is not None:
                retryCount = retryReceiptEntity.getRetryCount()
                jidsNeedSenderKey.append(retryReceiptEntity.getRetryJid())
            self.sendToGroupWithSessions(node, jidsNeedSenderKey, retryCount)

    def getSessionCipher(self, recipientId):
        if recipientId in self.sessionCiphers:
            sessionCipher = self.sessionCiphers[recipientId]
        else:
            sessionCipher = SessionCipher(self.store, self.store, self.store, self.store, recipientId, 1)
            self.sessionCiphers[recipientId] = sessionCipher

        return sessionCipher

    def getGroupCipher(self, groupId, senderId):
        senderKeyName = SenderKeyName(groupId, AxolotlAddress(senderId, 0))
        if senderKeyName in self.groupCiphers:
            groupCipher = self.groupCiphers[senderKeyName]
        else:
            groupCipher = GroupCipher(self.store, senderKeyName)
            self.groupCiphers[senderKeyName] = groupCipher
        return groupCipher


    @staticmethod
    def serializeToProtobuf(node=None, more=None, toString=True):

        params = more or {}
        if node:
            child = node.getChild("body")
            if child:
                assert child['type'], "type attribute cannot be empty"
                data = deep_clean_empty(child.getData())
                params[child['type']] = data
            else:
                raise ValueError("No body or media nodes found")
        serializedData = dict_to_protobuf(Message(), params)

        if toString:
            serializedData = serializedData.SerializeToString()

        if "YOWSUP_PROTOBUF_DEBUG" in os.environ:
            from yowsup.common.protobuf_inspect.types import StandardParser
            from io import BytesIO
            parser = StandardParser()
            parser.types["root"] = {}
            parser.types["root"]["compact"] = False
            print(parser.safe_call(parser.match_handler("message"), BytesIO(serializedData), "root"))

        return serializedData



    @staticmethod
    def serializeSKDM(groupId, senderKeyDistributionMessage):
        return {
            'sender_key_distribution_message': {
                'groupId': groupId,
                'axolotl_sender_key_distribution_message': senderKeyDistributionMessage.serialize()
            }
        }

    @staticmethod
    def getPadding():
        num = randint(1, 255)
        return bytearray([num] * num)


def deep_clean_empty(d):
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (deep_clean_empty(v) for v in d) if v]
    return {k: v for k, v in ((k, deep_clean_empty(v)) for k, v in d.items()) if v}
