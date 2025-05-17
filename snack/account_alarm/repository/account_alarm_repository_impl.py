from board.entity.board import Board
from comment.entity.comment import Comment
from account_alarm.entity.account_alarm import AccountAlarm
from account_profile.entity.account_profile import AccountProfile
from account_alarm.repository.account_alarm_repository import AccountAlarmRepository
# from django.utils import timezone
# from datetime import timedelta

class AccountAlarmRepositoryImpl(AccountAlarmRepository):
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def findUnreadAllAlarmsById(self, account_id):
        alarms = (
            AccountAlarm.objects
            .filter(recipient=account_id, is_unread=True)  # 미읽은 알림만 조회
            .select_related('comment__author__account', 'board')  # 댓글, 댓글 작성자, 게시글을 JOIN (성능 최적화)
            .order_by('-alarm_created_at')  # 최신 알림 우선 정렬
        )

        alarm_list = []
        for alarm in alarms:
            comment = alarm.comment
            author = comment.author if comment else None

            alarm_data = {
                "alarm_id": alarm.id,
                "board_id": alarm.board.id,
                "board_title": alarm.board.title,
                "comment_id": comment.id if comment else None,
                "comment_created_at": comment.created_at if comment else None,
                "comment_author_id": alarm.comment.author.account.id if alarm.comment and alarm.comment.author else None,
                "comment_author_nickname": author.account_nickname if author else None,
                "comment_content": comment.content if comment else None
            }
            alarm_list.append(alarm_data)
        return alarm_list

    def findUnreadBoardAlarmsById(self, account_id):
        alarms = (
            AccountAlarm.objects
            .filter(recipient=account_id, is_unread=True, alarm_type="BOARD")
            .select_related('board')
            .order_by('-alarm_created_at')
        )

        alarm_list = []
        for alarm in alarms:
            alarm_data = {
                "alarm_id": alarm.id,
                "board_id": alarm.board.id,
                "board_title": alarm.board.title,
                "comment_id": alarm.comment.id if alarm.comment else None,
                "alarm_created_at": alarm.alarm_created_at
            }
            alarm_list.append(alarm_data)

        return alarm_list

    def findUnreadCommentAlarmsById(self, account_id):
        alarms = (
            AccountAlarm.objects
            .filter(recipient=account_id, is_unread=True, alarm_type="COMMENT")
            .select_related('comment__author__account', 'board')
            .order_by('-alarm_created_at')
        )

        alarm_list = []
        for alarm in alarms:
            comment = alarm.comment
            author = comment.author if comment else None

            alarm_data = {
                "alarm_id": alarm.id,
                "board_id": alarm.board.id,
                "board_title": alarm.board.title,
                "comment_id": comment.id if comment else None,
                "comment_created_at": comment.created_at if comment else None,
                "comment_author_id": comment.author.account.id if comment and comment.author else None,
                "comment_author_nickname": author.account_nickname if author else None,
                "comment_content": comment.content if comment else None,
                "alarm_created_at": alarm.alarm_created_at
            }
            alarm_list.append(alarm_data)

        return alarm_list


    def countUnreadAllAlarmsById(self, account_id):
        return AccountAlarm.objects.filter(recipient=account_id, is_unread=True).count()

    def countUnreadBoardAlarmsById(self, account_id):
        return AccountAlarm.objects.filter(recipient=account_id, is_unread=True, alarm_type="BOARD").count()

    def countUnreadCommentAlarmsById(self, account_id):
        return AccountAlarm.objects.filter(recipient=account_id, is_unread=True, alarm_type="COMMENT").count()


    def saveReadAlarmById(self, alarm_id):
        try:
            alarm = AccountAlarm.objects.get(id=alarm_id)
            alarm.is_unread = False
            alarm.save()
        except ObjectDoesNotExist:
            raise ObjectDoesNotExist("알림을 찾을 수 없습니다.")


    def saveCommentAlarmToBoard(self, board: Board, comment: Comment):
        AccountAlarm.objects.create(
            alarm_type="BOARD",
            is_unread=True,
            board=board,
            recipient=board.author.account,
            comment=comment
        )

    def saveReplyAlarmToBoard(self, board: Board, comment: Comment):
        print(f"[DEBUG] Save Board Alarm: {board.id}, {comment.id}")  # AAA
        AccountAlarm.objects.create(
            alarm_type="COMMENT",
            is_unread=True,
            board=board,
            recipient=board.author.account,
            comment=comment,
        )

    def deleteAlarmByCommentId(self, comment_id):
        return AccountAlarm.objects.filter(comment_id=comment_id).delete()


    def deleteAlarmsByBoardId(self, board_id):
        delete_count, _ = AccountAlarm.objects.filter(board_id=board_id).delete()
        return delete_count