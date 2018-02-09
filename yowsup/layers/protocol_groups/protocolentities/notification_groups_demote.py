from .notification_groups import GroupsNotificationProtocolEntity
from yowsup.structs import ProtocolTreeNode


class DemoteGroupsNotificationProtocolEntity(GroupsNotificationProtocolEntity):
    """
    <notification notify="{{NOTIFY_NAME}}" id="{{id}}" t="{{TIMESTAMP}}" participant="{{participant_jiid}}"
                  from="{{group_jid}}" type="w:gp2">
        <demote subject="{{subject}}">
            <participant jid="{{participant_jid}}"></participant>
        </demote>
    </notification>
    """

    def __init__(self, _id, _from, timestamp, notify, participant, offline,
                 subject,
                 participants):
        super().__init__(_id, _from, timestamp, notify, participant,offline)
        self.setGroupProps(subject, participants)

    def setGroupProps(self,
                      subject,
                      participants):

        assert type(participants) is dict, "Participants must be a dict {jid => type?}"

        self.subject = subject
        self.participants = participants

    def getParticipants(self):
        return self.participants

    def getSubject(self):
        return self.subject

    def toProtocolTreeNode(self):
        node = super().toProtocolTreeNode()
        demoteNode = ProtocolTreeNode("demote", {"subject": self.subject})
        participants = []
        for jid in self.getParticipants():
            pnode = ProtocolTreeNode("participant", {"jid": jid})
            participants.append(pnode)

        demoteNode.addChildren(participants)
        node.addChild(demoteNode)

        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        demoteNode = node.getChild("demote")
        participants = {}
        for p in demoteNode.getAllChildren("participant"):
            participants[p["jid"]] = p["type"]

        return DemoteGroupsNotificationProtocolEntity(
            node["id"], node["from"], node["t"], node["notify"], node["participant"], node["offline"],
            demoteNode["subject"], participants
        )
