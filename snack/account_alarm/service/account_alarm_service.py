from abc import ABC, abstractmethod
from board.entity.board import Board
from comment.entity.comment import Comment
from account.entity.account import Account

class AccountAlarmService(ABC):

    @abstractmethod
    def getUserAllAlarmList(self, account_id):
        pass

    @abstractmethod
    def getUserBoardAlarmList(self, account_id):
        pass

    @abstractmethod
    def getUserCommentAlarList(self, account_id):
        pass

    @abstractmethod
    def createCommentAlarmToBoard(self, board: Board, comment: Comment):
        pass

    @abstractmethod
    def createReplyCommentAlarmToBoard(self, board: Board, comment: Comment):
        pass

    @abstractmethod
    def createReplyCommentAlarmToParent(self, board: Board, comment: Comment, parent: Comment):
        pass

    @abstractmethod
    def createReplyCommentAlarmToChild(self, board: Board, comment: Comment, recipient: Account):
        pass

    @abstractmethod
    def readAlarm(self, alarm_id):
        pass

    @abstractmethod
    def countUnreadAllAlarms(self, account_id):
        pass

    @abstractmethod
    def countUnreadBoardAlarms(self, account_id):
        pass

    @abstractmethod
    def countUnreadCommentAlarms(self, account_id):
        pass

    @abstractmethod
    def deleteCommentAlarm(self, comment_id):
        pass

    @abstractmethod
    def deleteBoardRelatedAlams(self, board_id):
        pass