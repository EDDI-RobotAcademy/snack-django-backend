from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import viewsets, status
from account.service.account_service_impl import AccountServiceImpl
from account_profile.service.account_profile_service_impl import AccountProfileServiceImpl
from account_alarm.service.account_alarm_service_impl import AccountAlarmServiceImpl
from comment.service.comment_service_impl import CommentServiceImpl
from redis_cache.service.redis_cache_service_impl import RedisCacheServiceImpl

class AccountAlarmController(viewsets.ViewSet):
    __accountService = AccountServiceImpl.getInstance()
    # __commentService = CommentServiceImpl.getInstance()
    __accountAlarmService = AccountAlarmServiceImpl.getInstance()
    __accountProfileService = AccountProfileServiceImpl.getInstance()
    redisCacheService = RedisCacheServiceImpl.getInstance()


    def __checkAlarmsStatus(self, account_id):
        account_profile = self.__accountProfileService.getProfileObjectByAccountId(account_id)
        if not account_profile:
            return {"success": False, "message": "프로필을 찾을 수 없습니다.", "alarms": []}

        if account_profile.alarm_board_status and account_profile.alarm_comment_status:
            alarms = self.__accountAlarmService.getUserAllAlarmList(account_id)
            unread_count = self.__accountAlarmService.countUnreadAllAlarms(account_id)

        elif account_profile.alarm_board_status and not account_profile.alarm_comment_status:
            alarms = self.__accountAlarmService.getUserBoardAlarmList(account_id)
            unread_count = self.__accountAlarmService.countUnreadBoardAlarms(account_id)

        elif not account_profile.alarm_board_status and account_profile.alarm_comment_status:
            alarms = self.__accountAlarmService.getUserCommentAlarList(account_id)
            unread_count = self.__accountAlarmService.countUnreadCommentAlarms(account_id)

        else:
            alarms = []
            unread_count = 0

        return {"success": True, "alarms": alarms, "unread_count": unread_count}


    def getUserAlarms(self, request):
        user_token = request.headers.get("userToken")
        if not user_token:
            return JsonResponse({"error": "userToken이 필요합니다", "success": False}, status=400)

        account_id = self.redisCacheService.getValueByKey(user_token)
        if not account_id:
            return JsonResponse({"error": "로그인이 필요합니다.", "success": False}, status=401)

        alarm_response = self.__checkAlarmsStatus(account_id)
        if not alarm_response.get("success"):
            return JsonResponse({"error": alarm_response.get("message"), "success": False}, status=404)

        return JsonResponse({
            "success": True,
            "data": {
                "alarms": alarm_response.get("alarms"),
                "unread_count": alarm_response.get("unread_count")
            }
        }, status=200)


    def readUserAlarm(self, request):
        user_token = request.headers.get("userToken")
        alarm_id = request.data.get("alarm_id")
        if not user_token:
            return JsonResponse({"error": "userToken이 필요합니다", "success": False}, status=400)

        account_id = self.redisCacheService.getValueByKey(user_token)
        if not account_id:
            return JsonResponse({"error": "로그인이 필요합니다.", "success": False}, status=401)

        if not alarm_id:
            return JsonResponse({"error": "alarm_id가 필요합니다.", "success": False}, status=status.HTTP_400_BAD_REQUEST)
        try:
            self.__accountAlarmService.readAlarm(alarm_id)
            return JsonResponse({"success": True, "message": "알림이 읽음 처리되었습니다."}, status=200)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "알림을 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)



