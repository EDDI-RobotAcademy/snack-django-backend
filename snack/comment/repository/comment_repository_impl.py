from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
from comment.entity.comment import Comment
from comment.repository.comment_repository import CommentRepository
from board.entity.board import Board
from account_profile.entity.account_profile import AccountProfile

class CommentRepositoryImpl(CommentRepository):
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

    def save(self, comment: Comment):
        """새로운 댓글을 저장한다."""
        comment.save()
        return comment

    def findById(self, comment_id: int):
        """ID로 댓글을 찾는다."""
        try:
            return Comment.objects.get(id=comment_id)
        except ObjectDoesNotExist:
            return None

    def findByBoard(self, board: Board):
        """특정 게시판의 모든 댓글을 조회한다."""
        return list(Comment.objects.filter(board=board).order_by('created_at'))

    def findByAuthor(self, author: AccountProfile):
        """특정 작성자의 모든 댓글을 조회한다."""
        return list(Comment.objects.filter(author=author).order_by('created_at'))

    def delete(self, comment_id: int):
        """댓글을 삭제한다."""
        comment = self.findById(comment_id)
        if comment:
            comment.delete()
            return True
        return False

    def findRepliesByParent(self, parent):
        child_replies = Comment.objects.filter(parent=parent)
        return child_replies