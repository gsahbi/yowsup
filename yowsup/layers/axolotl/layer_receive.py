# -*- coding utf-8 -*-

import binascii
import copy
import logging
import os
from io import BytesIO

from axolotl.axolotladdress import AxolotlAddress
from axolotl.duplicatemessagexception import DuplicateMessageException
from axolotl.ecc.curve import Curve
from axolotl.groups.groupcipher import GroupCipher
from axolotl.groups.groupsessionbuilder import GroupSessionBuilder
from axolotl.groups.senderkeyname import SenderKeyName
from axolotl.invalidkeyidexception import InvalidKeyIdException
from axolotl.invalidmessageexception import InvalidMessageException
from axolotl.nosessionexception import NoSessionException
from axolotl.protocol.prekeywhispermessage import PreKeyWhisperMessage
from axolotl.protocol.senderkeydistributionmessage import SenderKeyDistributionMessage
from axolotl.protocol.whispermessage import WhisperMessage
from axolotl.sessioncipher import SessionCipher
from axolotl.untrustedidentityexception import UntrustedIdentityException
from axolotl.util.hexutil import HexUtil
from axolotl.util.keyhelper import KeyHelper

from yowsup.common.protobuf_to_dict.convertor import protobuf_to_dict
from yowsup.common.tools import Jid
from yowsup.layers.axolotl.props import PROP_IDENTITY_AUTOTRUST
from yowsup.layers.axolotl.protocolentities import *
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity
from yowsup.layers.protocol_messages.proto.wa_pb2 import *
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.structs import ProtocolTreeNode
from .layer_base import AxolotlBaseLayer

logger = logging.getLogger(__name__)


class AxolotlReceivelayer(AxolotlBaseLayer):
    _COUNT_PREKEYS = 200

    def __init__(self):
        super(AxolotlReceivelayer, self).__init__()
        self.v2Jids = []  # people we're going to send v2 enc messages
        self.sessionCiphers = {}
        self.groupCiphers = {}
        self.pendingIncomingMessages = {}  # (jid, participantJid?) => message

    def receive(self, protocolTreeNode):
        """
        :type protocolTreeNode: ProtocolTreeNode
        """
        if not self.processIqRegistry(protocolTreeNode) and protocolTreeNode.tag == "message":
            self.onMessage(protocolTreeNode)
        else:
            self.toUpper(protocolTreeNode)

    def processPendingIncomingMessages(self, jid, participantJid=None):
        conversationIdentifier = (jid, participantJid)
        if conversationIdentifier in self.pendingIncomingMessages:
            for messageNode in self.pendingIncomingMessages[conversationIdentifier]:
                self.onMessage(messageNode)

            del self.pendingIncomingMessages[conversationIdentifier]

    # handling received data #####

    def onMessage(self, protocolTreeNode):
        encNode = protocolTreeNode.getChild("enc")
        if encNode:
            self.handleEncMessage(protocolTreeNode)
        else:
            self.toUpper(protocolTreeNode)

    def handleEncMessage(self, node):
        encMessageProtocolEntity = EncryptedMessageProtocolEntity(node)
        isGroup = node["participant"] is not None
        senderJid = node["participant"] if isGroup else node["from"]
        if node.getChild("enc")["v"] == "2" and node["from"] not in self.v2Jids:
            self.v2Jids.append(node["from"])

        try:
            if encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_PKMSG):
                self.handlePreKeyWhisperMessage(node)
            elif encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_MSG):
                self.handleWhisperMessage(node)
            if encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_SKMSG):
                self.handleSenderKeyMessage(node)

        except (InvalidMessageException, InvalidKeyIdException):
            logger.warning("InvalidMessage or InvalidKeyIdException for %s, would to send a retry",
                           Jid.denormalize(encMessageProtocolEntity.getAuthor()))


            if node["count"] is not None:
                logger.warning("This is the second retry forget it")
                return

            from yowsup.layers.axolotl.protocolentities.iq_key_get import GetKeysIqProtocolEntity
            logger.info("Trying GetKeys for %s, getting keys now",
                        Jid.denormalize(encMessageProtocolEntity.getAuthor()))
            # entity = GetKeysIqProtocolEntity([Jid.denormalize(encMessageProtocolEntity.getAuthor())])

            retry = RetryOutgoingReceiptProtocolEntity.fromMessageNode(node, self.store.getLocalRegistrationId())
            self.toLower(retry.toProtocolTreeNode())

        except NoSessionException:
            logger.warning("No session for %s, getting their keys now",
                           Jid.denormalize(encMessageProtocolEntity.getAuthor()))

            conversationIdentifier = (node["from"], node["participant"])
            if conversationIdentifier not in self.pendingIncomingMessages:
                self.pendingIncomingMessages[conversationIdentifier] = []
            self.pendingIncomingMessages[conversationIdentifier].append(node)

            def successFn(successJids, _):
                return self.processPendingIncomingMessages(*conversationIdentifier) if len(successJids) else None

            self.getKeysFor([senderJid], successFn)

        except DuplicateMessageException:
            logger.warning(
                "Received a message that we've previously decrypted, goint to send the delivery receipt myself")
            self.toLower(OutgoingReceiptProtocolEntity(node["id"], node["from"],
                                                       participant=node["participant"]).toProtocolTreeNode())

        except UntrustedIdentityException as e:
            if self.getProp(PROP_IDENTITY_AUTOTRUST, False):
                logger.warning("Autotrusting identity for %s", e.getName())
                self.store.saveIdentity(e.getName(), e.getIdentityKey())
                return self.handleEncMessage(node)
            else:
                logger.error("Ignoring message with untrusted identity")

    def handlePreKeyWhisperMessage(self, node):
        pkMessageProtocolEntity = EncryptedMessageProtocolEntity(node)
        enc_ = pkMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_PKMSG)
        preKeyWhisperMessage = PreKeyWhisperMessage(serialized=enc_.getData())
        sessionCipher = self.getSessionCipher(Jid.denormalize(pkMessageProtocolEntity.getAuthor()))
        plaintext = sessionCipher.decryptPkmsg(preKeyWhisperMessage)
        if enc_.getVersion() == 2:
            paddingByte = plaintext[-1] if type(plaintext[-1]) is int else ord(plaintext[-1])
            padding = paddingByte & 0xFF
            self.parseAndHandleMessageProto(pkMessageProtocolEntity, plaintext[:-padding])
        else:
            logger.error("Ignoring message with old version")

    def handleWhisperMessage(self, node):
        encMessageProtocolEntity = EncryptedMessageProtocolEntity(node)
        enc_ = encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_MSG)

        whisperMessage = WhisperMessage(serialized=enc_.getData())
        sessionCipher = self.getSessionCipher(Jid.denormalize(encMessageProtocolEntity.getAuthor()))
        plaintext = sessionCipher.decryptMsg(whisperMessage)

        if enc_.getVersion() == 2:
            paddingByte = plaintext[-1] if type(plaintext[-1]) is int else ord(plaintext[-1])
            padding = paddingByte & 0xFF
            self.parseAndHandleMessageProto(encMessageProtocolEntity, plaintext[:-padding])
        else:
            raise Exception("Protocol not longer supported")

    def handleSenderKeyMessage(self, node):
        encMessageProtocolEntity = EncryptedMessageProtocolEntity(node)
        enc_ = encMessageProtocolEntity.getEnc(EncProtocolEntity.TYPE_SKMSG)

        senderKeyName = SenderKeyName(encMessageProtocolEntity.sender,
                                      AxolotlAddress(Jid.denormalize(encMessageProtocolEntity.participant), 0))
        groupCipher = GroupCipher(self.store, senderKeyName)
        try:
            plaintext = groupCipher.decrypt(enc_.getData())
            paddingByte = plaintext[-1] if type(plaintext[-1]) is int else ord(plaintext[-1])
            padding = paddingByte & 0xFF
            self.parseAndHandleMessageProto(encMessageProtocolEntity, plaintext[:-padding])

        except NoSessionException:
            logger.warning("No session for %s, going to send a retry",
                           Jid.denormalize(encMessageProtocolEntity.getAuthor()))
            retry = RetryOutgoingReceiptProtocolEntity.fromMessageNode(node, self.store.getLocalRegistrationId())
            self.toLower(retry.toProtocolTreeNode())

        except Exception as ex:  # (AttributeError, TypeError)
            logger.error('Exception in handleSenderKeyMessage: %s' % ex)
            raise

    def parseAndHandleMessageProto(self, encMessageProtocolEntity, serializedData):
        node = encMessageProtocolEntity.toProtocolTreeNode()
        m = Message()
        try:
            if sys.version_info >= (3, 0) and isinstance(serializedData, str):
                serializedData = serializedData.encode()
        except AttributeError:
            logger.warning("AttributeError: 'bytes' object has no attribute 'encode'. Skipping 'encode()'")
            pass

        if "YOWSUP_PROTOBUF_DEBUG" in os.environ:
            from yowsup.common.protobuf_inspect.types import StandardParser
            parser = StandardParser()
            parser.types["root"] = {}
            parser.types["root"]["compact"] = False
            print(parser.safe_call(parser.match_handler("message"), BytesIO(serializedData), "root"))

        handled = False
        try:
            m.ParseFromString(serializedData)
            params = protobuf_to_dict(m)
        except Exception:
            raise

        if not m or not serializedData:
            raise ValueError("Empty message")

        if m.HasField("sender_key_distribution_message"):
            handled = True
            axolotlAddress = AxolotlAddress(Jid.denormalize(encMessageProtocolEntity.participant), 0)
            self.handleSenderKeyDistributionMessage(params['sender_key_distribution_message'], axolotlAddress)
            params.pop('sender_key_distribution_message')

        body_type = m.WhichOneof("body")
        if len(params) and body_type:
            messageNode = copy.deepcopy(node)
            messageNode.addChild(ProtocolTreeNode("body", {"type": body_type}, data=params[body_type]))
            self.toUpper(messageNode)

        elif not handled:
            raise ValueError("Unhandled")

    def handleSenderKeyDistributionMessage(self, senderKeyDistributionMessage, axolotlAddress):
        groupId = senderKeyDistributionMessage['groupId']
        axolotlSenderKeyDistributionMessage = SenderKeyDistributionMessage(
            serialized=senderKeyDistributionMessage['axolotl_sender_key_distribution_message'])
        groupSessionBuilder = GroupSessionBuilder(self.store)
        senderKeyName = SenderKeyName(groupId, axolotlAddress)
        groupSessionBuilder.process(senderKeyName, axolotlSenderKeyDistributionMessage)

    def getSessionCipher(self, recipientId):
        if recipientId in self.sessionCiphers:
            sessionCipher = self.sessionCiphers[recipientId]
        else:
            sessionCipher = SessionCipher(self.store, self.store, self.store, self.store, recipientId, 1)
            self.sessionCiphers[recipientId] = sessionCipher

        return sessionCipher

    def getGroupCipher(self, groupId, senderId):
        senderKeyName = SenderKeyName(groupId, AxolotlAddress(senderId, 1))
        if senderKeyName in self.groupCiphers:
            groupCipher = self.groupCiphers[senderKeyName]
        else:
            groupCipher = GroupCipher(self.store, senderKeyName)
            self.groupCiphers[senderKeyName] = groupCipher
        return groupCipher

    # keys set and get
    def sendKeys(self, fresh=True, countPreKeys=_COUNT_PREKEYS):
        identityKeyPair = KeyHelper.generateIdentityKeyPair() if fresh else self.store.getIdentityKeyPair()
        registrationId = KeyHelper.generateRegistrationId() if fresh else self.store.getLocalRegistrationId()
        preKeys = KeyHelper.generatePreKeys(KeyHelper.getRandomSequence(), countPreKeys)
        signedPreKey = KeyHelper.generateSignedPreKey(identityKeyPair, KeyHelper.getRandomSequence(65536))
        preKeysDict = {}
        for preKey in preKeys:
            keyPair = preKey.getKeyPair()
            preKeysDict[self.adjustId(preKey.getId())] = self.adjustArray(keyPair.getPublicKey().serialize()[1:])

        signedKeyTuple = (self.adjustId(signedPreKey.getId()),
                          self.adjustArray(signedPreKey.getKeyPair().getPublicKey().serialize()[1:]),
                          self.adjustArray(signedPreKey.getSignature()))

        setKeysIq = SetKeysIqProtocolEntity(self.adjustArray(identityKeyPair.getPublicKey().serialize()[1:]),
                                            signedKeyTuple, preKeysDict, Curve.DJB_TYPE, self.adjustId(registrationId))

        onResult = lambda _, __: self.persistKeys(registrationId, identityKeyPair, preKeys, signedPreKey, fresh)
        self._sendIq(setKeysIq,
                     onResult)
        # TODO: reintroduce error handler (was _sendIq(setKeysIq, onResult, self.onSentKeysError))

    def persistKeys(self, registrationId, identityKeyPair, preKeys, signedPreKey, fresh):
        total = len(preKeys)
        curr = 0
        prevPercentage = 0


    @staticmethod
    def adjustArray(arr):
        return HexUtil.decodeHex(binascii.hexlify(arr))


    @staticmethod
    def adjustId(_id):
        _id = format(_id, 'x')
        zfiller = len(_id) if len(_id) % 2 == 0 else len(_id) + 1
        _id = _id.zfill(zfiller if zfiller > 6 else 6)
        return binascii.unhexlify(_id)



    @staticmethod
    def debugProtobuf(serializedData):
        if "YOWSUP_PROTOBUF_DEBUG" in os.environ:
            from yowsup.common.protobuf_inspect.types import StandardParser
            parser = StandardParser()
            parser.types["root"] = {}
            parser.types["root"]["compact"] = False
            print(parser.safe_call(parser.match_handler("message"), BytesIO(serializedData), "root"))

