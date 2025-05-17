from django.http import JsonResponse
from rest_framework import status, viewsets

from account_alarm.service.account_alarm_service_impl import AccountAlarmServiceImpl
from board.service.board_service_impl import BoardServiceImpl
from account_profile.entity.account_profile import AccountProfile
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from restaurants.entity.restaurants import Restaurant
from account.service.account_service_impl import AccountServiceImpl
from redis_cache.service.redis_cache_service_impl import RedisCacheServiceImpl
from utility.auth_utils import is_authorized_user
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone

class BoardController(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    __boardService = BoardServiceImpl.getInstance()
    __accountService = AccountServiceImpl.getInstance()
    __accountAlarmService = AccountAlarmServiceImpl.getInstance()
    __redisService = RedisCacheServiceImpl.getInstance()

    def createBoard(self, request):
        postRequest = request.data
        userToken = request.headers.get("Authorization", "").replace("Bearer ", "")
        account_id = self.__redisService.getValueByKey(userToken)

        if not account_id:
            return JsonResponse({"error": "로그인 인증이 필요합니다.", "success": False}, status=status.HTTP_401_UNAUTHORIZED)

        title = postRequest.get("title")
        content = postRequest.get("content")
        end_time = postRequest.get("end_time")
        restaurant_id = postRequest.get("restaurant_id")
        image_url = postRequest.get("image_url")

        if not title or not content or not end_time:
            return JsonResponse({"error": "필수 항목 누락", "success": False}, status=status.HTTP_400_BAD_REQUEST)

        try:
            author = AccountProfile.objects.get(account__id=account_id)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "작성자 계정을 찾을 수 없습니다", "success": False}, status=status.HTTP_404_NOT_FOUND)

        try:
            restaurant = Restaurant.objects.get(id=restaurant_id) if restaurant_id else None
        except Restaurant.DoesNotExist:
            return JsonResponse({"error": "맛집 정보를 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        board = self.__boardService.createBoard(
            title=title,
            content=content,
            author=author,
            end_time=end_time,
            restaurant=restaurant,
            image_url=image_url
        )

        return JsonResponse({
            "success": True,
            "board_id": board.id,
            "title": board.title,
            "author_nickname": board.getAuthorNickname(),
            "image_url": board.getImageUrl(),
            "restaurant": board.restaurant.name if board.restaurant else None
        }, status=status.HTTP_201_CREATED)

    def getBoard(self, request, board_id):
        board = self.__boardService.findBoardById(board_id)
        if not board:
            return JsonResponse({"error": "게시글을 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        userToken = request.headers.get("Authorization", "").replace("Bearer ", "")
        is_author, _, _ = is_authorized_user(board, userToken)

        return JsonResponse({
            "board_id": board.id,
            "title": board.title,
            "content": board.content,
            "author_nickname": board.getAuthorNickname(),
            "author_account_id": board.author.account.id,
            "created_at": board.getCreatedAt(),
            "end_time": board.getEndTime(),
            "status": board.status,
            "image_url": board.getImageUrl(),
            "restaurant": board.restaurant.name if board.restaurant else None,
            "restaurant_id": board.restaurant.id if board.restaurant else None,
            "is_author": is_author,
            "success": True
        }, status=status.HTTP_200_OK)

    def updateBoard(self, request, board_id):
        postRequest = request.data or request.POST
        userToken = request.headers.get("Authorization", "").replace("Bearer ", "")
        account_id = self.__redisService.getValueByKey(userToken)

        if not account_id:
            return JsonResponse({"error": "로그인 인증이 필요합니다.", "success": False}, status=status.HTTP_401_UNAUTHORIZED)

        title = postRequest.get("title")
        content = postRequest.get("content")
        end_time = postRequest.get("end_time")
        restaurant_id = postRequest.get("restaurant_id")
        image_url = postRequest.get("image_url")

        try:
            user = AccountProfile.objects.get(account__id=account_id)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "사용자를 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        try:
            restaurant = Restaurant.objects.get(id=restaurant_id) if restaurant_id else None
        except Restaurant.DoesNotExist:
            return JsonResponse({"error": "맛집 정보를 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        updated_board = self.__boardService.updateBoard(
            board_id=board_id,
            user=user,
            title=title,
            content=content,
            end_time=end_time,
            restaurant=restaurant,
            image_url=image_url
        )

        if not updated_board:
            return JsonResponse({"error": "게시글을 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({
            "success": True,
            "message": "게시글이 수정되었습니다.",
            "board_id": updated_board.id,
            "title": updated_board.title,
            "updated_at": updated_board.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            "restaurant": updated_board.restaurant.name if updated_board.restaurant else None,
            "image_url": updated_board.getImageUrl(),
        }, status=status.HTTP_200_OK)

    def partial_update(self, request, board_id):
        return self.updateBoard(request, board_id)

    def getAllBoards(self, request):
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 10))
        sort = request.GET.get("sort", "latest")
        status_filter = request.GET.get("status")
        title = request.GET.get("title")
        author = request.GET.get("author")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        queryset = self.__boardService.findAllBoards()

        if status_filter == "ongoing":
            queryset = queryset.filter(end_time__gte=timezone.now())
        elif status_filter == "closed":
            queryset = queryset.filter(end_time__lt=timezone.now())

        if title:
            queryset = queryset.filter(title__icontains=title)

        if author:
            queryset = queryset.filter(author__account_nickname__icontains=author)

        if start_date and end_date:
            queryset = queryset.filter(end_time__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(end_time__gte=start_date)
        elif end_date:
            queryset = queryset.filter(end_time__range=[timezone.now().date(), end_date])

        if sort == "end_date":
            queryset = queryset.order_by('end_time')
        else:
            queryset = queryset.order_by('-created_at')

        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        board_list = [
            {
                "board_id": board.id,
                "title": board.title,
                "author_nickname": board.getAuthorNickname(),
                "author_account_id": board.author.account.id,
                "created_at": board.getCreatedAt(),
                "end_time": board.getEndTime(),
                "status": board.status,
                "image_url": board.getImageUrl(),
            }
            for board in page_obj.object_list
        ]
        return JsonResponse({
            "success": True,
            "boards": board_list,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number
        }, status=status.HTTP_200_OK)

    def deleteBoard(self, request, board_id):
        userToken = request.headers.get("Authorization", "").replace("Bearer ", "")
        deleted, status_code, message = self.__boardService.deleteBoardWithToken(board_id, userToken)

        if deleted:
            try:
                self.__accountAlarmService.deleteBoardRelatedAlams(board_id)
            except Exception as e:
                print(f"[ERROR] 알림 삭제 중 오류 발생: {str(e)}")
                return JsonResponse({
                    "success": deleted,
                    "message": message,
                    "warning": "게시글 관련 알림 삭제 중 오류가 발생했습니다."
                }, status=status_code)

        return JsonResponse({"success": deleted, "message": message}, status=status_code)

    def countBoardsPerRestaurant(self, request):
        result = self.__boardService.countBoardsByRestaurant()
        return JsonResponse({"success": True, "data": list(result)}, safe=False)
