from account_alarm.repository.account_alarm_repository_impl import AccountAlarmRepositoryImpl
from account_profile.entity.account_profile import AccountProfile
from account_alarm.service.account_alarm_service import AccountAlarmService
from board.entity.board import Board
from comment.entity.comment import Comment
from account.entity.account import Account


class AccountAlarmServiceImpl(AccountAlarmService):
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.__accountAlarmRepository = AccountAlarmRepositoryImpl.getInstance()
        return cls.__instance

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def getUserAllAlarmList(self, account_id):
        return self.__accountAlarmRepository.findUnreadAllAlarmsById(account_id)

    def getUserBoardAlarmList(self, account_id):
        return self.__accountAlarmRepository.findUnreadBoardAlarmsById(account_id)

    def getUserCommentAlarList(self, account_id):
        return self.__accountAlarmRepository.findUnreadCommentAlarmsById(account_id)



    def createCommentAlarmToBoard(self, board: Board, comment: Comment):
        return self.__accountAlarmRepository.saveCommentAlarmToBoard(board, comment)

    def createReplyCommentAlarmToBoard(self, board: Board, comment: Comment):
        return self.__accountAlarmRepository.saveReplyAlarmToBoard(board, comment)

    def createReplyCommentAlarmToParent(self, board: Board, comment: Comment, parent: Comment):
        self.__accountAlarmRepository.saveReplyAlarmToParent(board, comment, parent)

    def createReplyCommentAlarmToChild(self, board: Board, comment: Comment, recipient: Account):
        self.__accountAlarmRepository.saveReplyAlarmToChild(board, comment, recipient)



    def readAlarm(self, alarm_id):
        return self.__accountAlarmRepository.saveReadAlarmById(alarm_id)

    def countUnreadAllAlarms(self, account_id):
        return self.__accountAlarmRepository.countUnreadAllAlarmsById(account_id)

    def countUnreadBoardAlarms(self, account_id):
        return self.__accountAlarmRepository.countUnreadBoardAlarmsById(account_id)

    def countUnreadCommentAlarms(self, account_id):
        return self.__accountAlarmRepository.countUnreadCommentAlarmsById(account_id)



    def deleteCommentAlarm(self, comment_id):
        try:
            self.__accountAlarmRepository.deleteAlarmByCommentId(comment_id)
            print(f"[DEBUG] 알림이 삭제되었습니다.")            # AAA
        except Exception as e:
            print(f"[ERROR] 댓글 알림 삭제 실패: {str(e)}")                       # AAA
            raise e

    def deleteBoardRelatedAlams(self, board_id):
        try:
            delete_count = self.__accountAlarmRepository.deleteAlarmsByBoardId(board_id)
            print(f"[DEBUG] {delete_count}개의 게시글 관련 알림이 삭제되었습니다.") # AAA
        except Exception as e:
            print(f"[ERROR] 게시글 알림 삭제 중 오류 발생: {str(e)}")  # AAA
            raise e