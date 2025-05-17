from abc import ABC, abstractmethod
from board.entity.board import Board
from comment.entity.comment import Comment

class AccountAlarmRepository(ABC):

    @abstractmethod
    def findUnreadAllAlarmsById(self, account_id):
        pass

    @abstractmethod
    def findUnreadBoardAlarmsById(self, account_id):
        pass

    @abstractmethod
    def findUnreadCommentAlarmsById(self, account_id):
        pass

    @abstractmethod
    def countUnreadAllAlarmsById(self, account_id):
        pass

    @abstractmethod
    def countUnreadBoardAlarmsById(self, account_id):
        pass

    @abstractmethod
    def countUnreadCommentAlarmsById(self, account_id):
        pass

    @abstractmethod
    def saveReadAlarmById(self, alarm_id):
        pass

    @abstractmethod
    def saveCommentAlarmToBoard(self, board: Board, comment: Comment):
        pass

    @abstractmethod
    def saveReplyAlarmToBoard(self, board: Board, comment: Comment):
        pass

    @abstractmethod
    def deleteAlarmByCommentId(self, comment_id):
        pass

    @abstractmethod
    def deleteAlarmsByBoardId(self, board_id):
        pass