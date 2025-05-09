from django.http import JsonResponse
from rest_framework import viewsets, status
from datetime import datetime, timedelta
from account.service.account_service_impl import AccountServiceImpl
from redis_cache.service.redis_cache_service_impl import RedisCacheServiceImpl
from rest_framework.response import Response

class AccountController(viewsets.ViewSet):
    __accountService = AccountServiceImpl.getInstance()
    redisCacheService = RedisCacheServiceImpl.getInstance()

    def createAccount(self, request):
        """새로운 계정을 생성하는 엔드포인트"""
        postRequest = request.data
        email = postRequest.get("email")
        account_path = postRequest.get("account_path")
        role_type = postRequest.get("role_type", "user")  # 기본값: user

        if not email or not account_path:
            return JsonResponse({"error": "email과 account_path가 필요합니다", "success": False}, status=status.HTTP_400_BAD_REQUEST)

        if self.__accountService.checkEmailDuplication(email):
            return JsonResponse({"error": "이미 존재하는 이메일입니다", "success": False}, status=status.HTTP_409_CONFLICT)

        account = self.__accountService.createAccount(email, account_path, role_type)

        # Redis에 계정 ID 저장 (key: email, value: account_id)
        self.redisCacheService.storeKeyValue(email, account.id)

        return JsonResponse({"success": True, "account_id": account.id}, status=status.HTTP_201_CREATED)

    def getAccount(self, request):
        account_id = request.headers.get("account-id")  
        user_token = request.headers.get("userToken")

        if not user_token or not account_id:
            return JsonResponse({"error": "userToken과 account_id가 필요합니다", "success": False}, status=status.HTTP_400_BAD_REQUEST)

        redis_account_id = self.redisCacheService.getValueByKey(user_token)
        if str(redis_account_id) != str(account_id):
            return JsonResponse({"error": "토큰 인증 실패", "success": False}, status=status.HTTP_403_FORBIDDEN)

        account = self.__accountService.findAccountById(account_id)
        if not account:
            return JsonResponse({"error": "계정을 찾을 수 없습니다", "success": False}, status=status.HTTP_404_NOT_FOUND)
        #
        # # 계정 상태 확인
        # if account.account_status == 1:       # Suspended 일시 정지
        #     return JsonResponse({"error": "정지된 계정입니다.", "success": False}, status=status.HTTP_414_FORBIDDEN)
        #
        # elif account.account_status == 4:      # 영구 정지
        #     return JsonResponse({"error": "영구 정지된 계정입니다.", "success": False}, status=status.HTTP_444_FORBIDDEN)
        #
        # elif account.account_status == 2:     # 탈퇴 회원 재가입 -> 기존 계정 정지 상태, 신규 가입 처리
        #     rejoin_account = self.__accountService.createAccount(
        #         email=account.email,
        #         account_path=account.account_path,
        #         role_type=account.role_type
        #     )
        #     # Redis에 새로운 계정 ID 저장
        #     self.redisCacheService.storeKeyValue(email=rejoin_account.email, value=rejoin__account.id)
        #
        #     return JsonResponse({"success": True, "account_id": rejoin__account.id}, status=status.HTTP_201_CREATED)
        #

        try:
            decrypted_email = account.get_decrypted_email()
            print(f"🔓 복호화된 이메일: {decrypted_email}")
        except Exception as e:
            print(f"[ERROR] 이메일 복호화 실패: {str(e)}")
            decrypted_email = account.email  # fallback: 암호화 된 그대로 반환

        return JsonResponse({
            "account_id": account.id,
            "email": decrypted_email,
            "role_type": account.role_type.role_type,
            "account_register": account.account_register.strftime('%Y-%m-%d %H:%M:%S'),
            "account_used_date": account.account_used_date.strftime('%Y-%m-%d %H:%M:%S'),
            "account_path": account.account_path,
            "account_status": account.account_status,
            "success": True
        }, status=status.HTTP_200_OK)

    def updateLastUsed(self, request, email):
        """이메일 기반으로 Redis에서 account_id를 가져와 마지막 로그인 날짜 업데이트"""
        account_id = self.redisCacheService.getValueByKey(email)

        if not account_id:
            return JsonResponse({"error": "해당 이메일에 대한 계정 정보를 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        updated_account = self.__accountService.updateLastUsed(account_id)

        if not updated_account:
            return JsonResponse({"error": "계정을 찾을 수 없습니다", "success": False}, status=status.HTTP_404_NOT_FOUND)

        self.redisCacheService.storeKeyValue(email, account_id)
        
        return JsonResponse({
            "message": "최근 사용 날짜가 업데이트되었습니다.",
            "last_used_date": updated_account.account_used_date.strftime('%Y-%m-%d %H:%M:%S'),
            "success": True
        }, status=status.HTTP_200_OK)



    #  관리자 -사용자 계정 정지 요청(SUSPEND)
    def suspendAccount(self, request):
        user_token = request.headers.get("userToken")
        target_account_id = request.data.get("target_account_id")
        reason = request.data.get("reason", "정지 사유")
        duration = request.data.get("duration")  # 정지 기간 일수 (정수)

        if not user_token:
            return JsonResponse({"error": "userToken이 필요합니다", "success": False}, status=status.HTTP_400_BAD_REQUEST)
        if not target_account_id:
            return JsonResponse({"error": "target_account_id가 필요합니다", "success": False}, status=status.HTTP_400_BAD_REQUEST)

        # 관리자 계정 로그인 확인 (userToken -> admin_account_id)
        admin_account_id = self.redisCacheService.getValueByKey(user_token)
        if not admin_account_id:
            return JsonResponse({"error": "로그인이 필요합니다.", "success": False}, status=status.HTTP_401_UNAUTHORIZED)

        # 관리자 권한 확인
        # admin_account = self.__accountService.findAccountById(admin_account_id)
        # if not admin_account or admin_account.role_type.role_type != 'ADMIN':
        #     return JsonResponse({"error": "관리자 권한이 필요합니다.", "success": False}, status=status.HTTP_403_FORBIDDEN)

        # 대상 사용자 확인
        target_account = self.__accountService.findAccountById(target_account_id)
        if not target_account:
            return Response({"error": "대상 사용자를 찾을 수 없습니다.", "success": False}, status=status.HTTP_404_NOT_FOUND)

        # 대상 사용자 정지 상태 확인 (이미 정지된 사용자 확인)
        is_suspended, message = self.__accountService.isSuspended(target_account_id)
        if is_suspended:
            return Response({"error": message, "success": False}, status=status.HTTP_400_BAD_REQUEST)


        try:
            suspended_account = self.__accountService.suspendAccountById(
                target_account_id=target_account_id,
                reason=reason,
                duration=int(duration) if duration else None
            )
            return Response({
                "success": True,
                "message": f"사용자 {suspended_account.email} (ID: {suspended_account.id})이 정지되었습니다.",
                "reason": suspended_account.suspension_reason,
                "suspended_until": suspended_account.suspended_until.strftime(
                    '%Y-%m-%d %H:%M:%S') if suspended_account.suspended_until else "무기한 정지"
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e), "success": False}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e), "success": False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 