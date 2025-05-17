from django.http import JsonResponse
from rest_framework import viewsets, status

from account_alarm.service.account_alarm_service_impl import AccountAlarmServiceImpl
from comment.service.comment_service_impl import CommentServiceImpl
from board.entity.board import Board
from account_profile.entity.account_profile import AccountProfile
from comment.entity.comment import Comment
from django.core.exceptions import ObjectDoesNotExist
from utility.auth_utils import get_user_info_from_token
from redis_cache.service.redis_cache_service_impl import RedisCacheServiceImpl


class CommentController(viewsets.ViewSet):
    __commentService = CommentServiceImpl.getInstance()
    __accountAlarmService = AccountAlarmServiceImpl.getInstance()

    def createComment(self, request):
        """새로운 댓글 생성"""
        postRequest = request.data
        board_id = postRequest.get("board_id")
        author_id = postRequest.get("author_id")
        content = postRequest.get("content")

        if not board_id or not author_id or not content:
            return JsonResponse({"error": "board_id, author_id, content가 필요합니다.", "success": False}, status=status.HTTP_400_BAD_REQUEST)

        try:
            board = Board.objects.get(id=board_id)
            author = AccountProfile.objects.get(account__id=author_id)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "게시글 또는 작성자를 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        comment = self.__commentService.createComment(board, author, content)
        if board.author.account.id != author.account.id:     # 게시물 생성자 != 댓글 생성자-> 자기 알람 불필요, 게시물 생성자만 알림 받으면 됌
            print("DEBUG comment Alarm")  #     AAA
            self.__accountAlarmService.createCommentAlarmToBoard(board, comment)

        return JsonResponse({
            "success": True,
            "comment_id": comment.id,
            "content": comment.content,
            "author_nickname": comment.getAuthorNickname()
        }, status=status.HTTP_201_CREATED)

    def createReply(self, request):
        """대댓글 생성"""
        postRequest = request.data
        board_id = postRequest.get("board_id")
        author_id = postRequest.get("author_id")
        content = postRequest.get("content")
        parent_id = postRequest.get("parent_id")

        if not board_id or not author_id or not content or not parent_id:
            return JsonResponse({"error": "board_id, author_id, content, parent_id가 필요합니다.", "success": False}, status=status.HTTP_400_BAD_REQUEST)

        try:
            board = Board.objects.get(id=board_id)
            author = AccountProfile.objects.get(account__id=author_id)
            parent = Comment.objects.get(id=parent_id)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "게시글, 작성자 또는 부모 댓글을 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        reply = self.__commentService.createComment(board, author, content, parent)
        # 게시물 생성자에게 알림 (자기 댓글 제외)
        if board.author.account.id != author.account.id:   # 게시물 생성자 != 댓글 생성자, 게시물 생성자만 알림 받으면 됌
            print("[DEBUG] createBoardReplyAlarm called")  # AAA
            self.__accountAlarmService.createReplyCommentAlarmToBoard(board, reply)

        # 부모 댓글 작성자에게 알림 (자기 댓글 제외)
        if parent.author.account.id != author.account.id:
            self.__accountAlarmService.createReplyCommentAlarmToParent(board, reply, parent)

        # 부모 댓글이 같은 자식 댓글 작성자에게 알림 (자기 댓글 제외)
        child_replies = self.__commentService.findChildRepliesByParent(parent)
        for reply in child_replies:
            if reply.author.account.id != author.account.id:  # 자기 자신 제외
                self.__accountAlarmService.createReplyCommentAlarmToChild(board, reply, reply.author.account)

        return JsonResponse({
            "success": True,
            "comment_id": reply.id,
            "content": reply.content,
            "author_nickname": reply.getAuthorNickname(),
            "parent_id": reply.parent.id if reply.parent else None,
        }, status=status.HTTP_201_CREATED)

    def getComment(self, request, comment_id):
        """특정 댓글 조회"""
        comment = self.__commentService.findCommentById(comment_id)
        if not comment:
            return JsonResponse({"error": "댓글을 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({
            "comment_id": comment.id,
            "board_id": comment.getBoardId(),
            "content": comment.content,
            "author_nickname": comment.getAuthorNickname(),
            "created_at": comment.getCreatedAt(),
            "success": True
        }, status=status.HTTP_200_OK)

    def getAllCommentsByBoard(self, request, board_id):
        """게시글의 댓글 + 대댓글 전체 조회 + 정렬 + 페이지네이션"""
        try:
            board = Board.objects.get(id=board_id)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "게시글을 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        page = int(request.GET.get("page", 1))  # 기본 1페이지
        page_size = int(request.GET.get("page_size", 10))  # 기본 댓글 10개씩

        account_id, is_admin = get_user_info_from_token(request)
        all_comments = Comment.objects.filter(board=board).select_related("author", "parent").order_by("-created_at")

        top_level_comments = [c for c in all_comments if c.parent is None]
        replies = [c for c in all_comments if c.parent is not None]

        # 댓글 페이지네이션 처리
        start = (page - 1) * page_size
        end = start + page_size
        paged_top_level = top_level_comments[start:end]

        # 각 댓글에 자식 대댓글 매핑
        comment_list = []
        for parent in paged_top_level:
            children = [r for r in replies if r.parent.id == parent.id]
            children_sorted = sorted(children, key=lambda x: x.created_at, reverse=True)

            comment_list.append({
                "comment_id": parent.id,
                "content": parent.content,
                "author_nickname": parent.getAuthorNickname(),
                "created_at": parent.getCreatedAt(),
                "author_account_id": parent.author.account.id if parent.author and parent.author.account else None,
                "is_author": parent.author.account.id == account_id if parent.author else False,
                "is_admin": is_admin,
                "parent_id": None,
                "replies_count": len(children_sorted),  # ✅ 전체 대댓글 수 포함
                "replies": [
                    {
                        "comment_id": child.id,
                        "content": child.content,
                        "author_nickname": child.getAuthorNickname(),
                        "created_at": child.getCreatedAt(),
                        "author_account_id": child.author.account.id if child.author and child.author.account else None,
                        "is_author": child.author.account.id == account_id if child.author else False,
                        "is_admin": is_admin,
                        "parent_id": parent.id
                    }
                    for child in children_sorted # 처음 5개만 응답
                ]
            })

        return JsonResponse({
            "success": True,
            "comments": comment_list,
            "total": len(top_level_comments),
            "page": page,
            "page_size": page_size
        }, status=status.HTTP_200_OK)

    def getAllCommentsByAuthor(self, request, author_id):
        """작성자의 모든 댓글 조회"""
        try:
            author = AccountProfile.objects.get(account__id=author_id)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "작성자를 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        comments = self.__commentService.findAllCommentsByAuthor(author)
        comment_list = [
            {
                "comment_id": comment.id,
                "content": comment.content,
                "board_id": comment.getBoardId(),
                "created_at": comment.getCreatedAt()
            }
            for comment in comments
        ]

        return JsonResponse({"success": True, "comments": comment_list}, status=status.HTTP_200_OK)

    def deleteComment(self, request, comment_id):
        """댓글 삭제"""
        user_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user_id = RedisCacheServiceImpl.getInstance().getValueByKey(user_token)

        if not user_token:
            return JsonResponse({"error": "Authorization 헤더가 필요합니다.", "success": False},
                                status=status.HTTP_400_BAD_REQUEST)
        if not user_id:
            return JsonResponse({"error": "user_id가 필요합니다.", "success": False}, status=status.HTTP_400_BAD_REQUEST)
        # try:
        #     user = AccountProfile.objects.get(account__id=user_id)
        # except ObjectDoesNotExist:
        #     return JsonResponse({"error": "사용자를 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        deleted, status_code, message = self.__commentService.deleteComment(comment_id, user_token)

        if deleted:
            try:
                self.__accountAlarmService.deleteCommentAlarm(comment_id)
            except Exception as e:
                print(f"[ERROR] 알림 삭제 중 오류 발생: {str(e)}")
                return JsonResponse({
                    "success": deleted,
                    "message": message,
                    "warning": "댓글 삭제는 완료되었으나 알림 삭제 중 오류가 발생했습니다."
                }, status=status_code)

        return JsonResponse({"success": deleted, "message": message}, status=status_code)

    def updateComment(self, request, comment_id):
        """댓글 수정"""
        user_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user_id = RedisCacheServiceImpl.getInstance().getValueByKey(user_token)

        if not user_id:
            return JsonResponse({"error": "로그인 인증 필요", "success": False}, status=status.HTTP_401_UNAUTHORIZED)

        content = request.data.get("content")
        if not content:
            return JsonResponse({"error": "수정할 내용이 필요합니다.", "success": False}, status=status.HTTP_400_BAD_REQUEST)

        try:
            comment = Comment.objects.get(id=comment_id)
        except Comment.DoesNotExist:
            return JsonResponse({"error": "댓글을 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        # 권한 검사 (작성자 본인 또는 관리자)
        if comment.author.account.id != int(user_id):
            return JsonResponse({"error": "수정 권한이 없습니다.", "success": False}, status=status.HTTP_403_FORBIDDEN)

        comment.content = content
        comment.save()

        return JsonResponse({"success": True, "message": "댓글이 수정되었습니다."}, status=status.HTTP_200_OK)

