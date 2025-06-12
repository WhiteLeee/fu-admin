# -*- coding: utf-8 -*-
# @Time    : 2022/5/14 15:05
# @Author  : Wick
# @FileName: login.py
# @Software: PyCharm
import json
from datetime import datetime
# from django.core.cache import cache

from django.contrib import auth
from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from ninja import Router, ModelSchema, Query, Schema, Field

from fuadmin.settings import SECRET_KEY, TOKEN_LIFETIME
from system.models import Users, Role, MenuButton, MenuColumnField
from utils.fu_jwt import FuJwt
from utils.fu_response import FuResponse
from utils.request_util import save_login_log
from utils.usual import get_user_info_from_token

router = Router()


class SchemaOut(ModelSchema):
    homePath: str = Field(None, alias="home_path")

    class Config:
        model = Users
        model_exclude = ['password', 'role', 'post']


class LoginSchema(Schema):
    username: str = Field(None, alias="username")
    password: str = Field(None, alias="password")


class Out(Schema):
    multi_depart: str
    sysAllDictItems: str
    departs: str
    userInfo: SchemaOut
    token: str


@router.post("/login", response=Out, auth=None)
def login(request, data: LoginSchema):
    """用户登录接口
    验证用户凭据，成功则生成JWT Token并返回用户信息。
    允许匿名访问 (auth=None)。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"用户尝试登录，用户名: {data.username}")

    user_obj = auth.authenticate(request, **data.dict())
    if user_obj:
        request.user = user_obj # Django 内置的 request.user 赋值
        logger.info(f"用户 {data.username} 认证成功")

        # 获取用户角色和岗位信息
        roles = user_obj.role.all().values('id', 'name') # 同时获取name用于日志
        posts = list(user_obj.post.all().values('id', 'name')) # 同时获取name用于日志
        role_ids = [item['id'] for item in roles]
        post_ids = [item['id'] for item in posts]

        logger.info(f"用户 {data.username} 角色ID: {role_ids}, 岗位ID: {post_ids}")

        # 准备JWT payload
        user_info_payload = model_to_dict(user_obj)
        user_info_payload['role'] = role_ids
        user_info_payload['post'] = post_ids
        # 从payload中移除敏感信息和不需要的信息
        sensitive_fields = ['password', 'avatar'] # avatar如果很大或不需要在token中，可以移除
        for field in sensitive_fields:
            if field in user_info_payload:
                del user_info_payload[field]

        # 生成JWT Token
        time_now = int(datetime.now().timestamp())
        jwt_payload = user_info_payload.copy() # 使用副本，避免修改原始字典
        # FuJwt 可能需要 id 字段，确保存在
        if 'id' not in jwt_payload:
            jwt_payload['id'] = user_obj.id

        fu_jwt = FuJwt(SECRET_KEY, jwt_payload, valid_to=time_now + TOKEN_LIFETIME)
        token = f"bearer {fu_jwt.encode()}"
        logger.info(f"为用户 {data.username} 生成的Token (前缀已添加)")

        # 准备返回数据
        # "multi_depart", "sysAllDictItems", "departs" 的值似乎是固定的，需要确认其含义
        response_data = {
            "multi_depart": 1, # TODO: 确认此字段含义和来源
            "sysAllDictItems": "q", # TODO: 确认此字段含义和来源
            "departs": "e", # TODO: 确认此字段含义和来源
            'userInfo': user_info_payload, # 返回给前端的用户信息
            'token': token
        }

        # 保存登录日志
        try:
            save_login_log(request=request)
            logger.info(f"用户 {data.username} 登录日志已保存")
        except Exception as e:
            logger.error(f"保存用户 {data.username} 登录日志失败: {e}", exc_info=True)

        return response_data
    else:
        logger.warning(f"用户 {data.username} 登录失败：账号或密码错误")
        return FuResponse(code=500, msg="账号/密码错误")


@router.get("/logout", auth=None) # 函数名 get_post 可能有误，应为 logout
def get_post(request):
    """用户注销接口
    允许匿名访问 (auth=None)，但通常注销需要验证Token。
    如果Token在客户端删除，此处主要用于服务端进行一些清理工作（如记录日志，清除特定缓存）。
    """
    import logging
    logger = logging.getLogger(__name__)
    user_info = None
    try:
        # 尝试从Token获取用户信息，用于日志记录
        user_info = get_user_info_from_token(request)
        if user_info and 'username' in user_info:
            logger.info(f"用户 {user_info['username']} (ID: {user_info.get('id')}) 请求注销")
        else:
            logger.info("匿名用户或无效Token尝试注销")
        
        # 如果使用了服务端Token缓存 (如Redis)，则在此处删除
        # if user_info and 'id' in user_info:
        #     cache.delete(user_info['id'])
        #     logger.info(f"用户 {user_info['username']} 的Token缓存已清除")

        # Django的auth.logout()会清除session，如果使用了session认证
        # from django.contrib.auth import logout as django_logout
        # django_logout(request)
        # logger.info(f"用户 {user_info.get('username', 'N/A')} 的Django会话已清除")

        return FuResponse(msg="注销成功")
    except Exception as e:
        # 即便注销过程出错，通常也应告知客户端注销（表面上）成功
        # 但服务端应记录错误
        if user_info and 'username' in user_info:
            logger.error(f"用户 {user_info['username']} 注销过程中发生错误: {e}", exc_info=True)
        else:
            logger.error(f"注销过程中发生错误: {e}", exc_info=True)
        return FuResponse(msg="注销操作完成，但服务端发生内部错误")


@router.get("/userinfo", response=SchemaOut)
def get_userinfo(request):
    """获取当前登录用户信息
    通过请求中的Token获取用户ID，然后从数据库查询并返回用户信息。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("请求获取当前用户信息")
    try:
        # 从Token中解析用户信息 (通常包含用户ID等)
        token_user_info = get_user_info_from_token(request)
        if not token_user_info or 'id' not in token_user_info:
            logger.warning("获取用户信息失败：Token无效或不包含用户ID")
            return FuResponse(code=401, msg="无效的Token或用户未登录")

        user_id = token_user_info['id']
        logger.info(f"根据Token中的用户ID {user_id} 查询用户信息")

        # 从数据库获取最新的用户信息
        # 使用 select_related 或 prefetch_related 优化关联查询（如果SchemaOut包含关联字段）
        user = get_object_or_404(Users.objects.select_related(), id=user_id) 
        logger.info(f"成功获取用户 {user.username} (ID: {user.id}) 的信息")
        
        # SchemaOut 会自动处理模型到Schema的转换
        # 注意：确保 SchemaOut 中排除了密码等敏感字段
        return user
    except Users.DoesNotExist:
        logger.error(f"获取用户信息失败：用户ID {user_id} 在数据库中不存在", exc_info=True)
        return FuResponse(code=404, msg="用户不存在")
    except Exception as e:
        logger.error(f"获取用户信息过程中发生未知错误: {e}", exc_info=True)
        return FuResponse(code=500, msg="获取用户信息失败")


@router.get("/permCode") # 函数名 route_menu_tree 可能有误，应为 get_permission_codes
def route_menu_tree(request):
    """获取当前用户的权限码列表 (按钮和列字段权限)
    根据用户角色或超级管理员状态，收集其拥有的所有按钮和列字段权限的 `code`。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("请求获取用户权限码列表")
    try:
        token_user_info = get_user_info_from_token(request)
        if not token_user_info or 'id' not in token_user_info:
            logger.warning("获取权限码失败：Token无效或不包含用户ID")
            return FuResponse(code=401, msg="无效的Token或用户未登录")

        user_id = token_user_info['id']
        is_superuser = token_user_info.get('is_superuser', False)
        logger.info(f"用户ID: {user_id}, 是否超级管理员: {is_superuser}")

        # 预先获取用户对象，避免多次查询
        try:
            user = Users.objects.prefetch_related('role__permission', 'role__column').get(id=user_id)
        except Users.DoesNotExist:
            logger.error(f"获取权限码失败：用户ID {user_id} 在数据库中不存在")
            return FuResponse(code=404, msg="用户不存在")

        code_list = set() # 使用集合避免重复的权限码

        if not is_superuser:
            logger.info(f"非超级管理员 {user.username}，根据角色获取权限")
            # 获取用户所有角色关联的按钮权限ID和列权限ID
            # 使用 prefetch_related 优化查询
            menu_button_codes = set()
            menu_column_codes = set()
            for role_obj in user.role.all():
                for perm in role_obj.permission.all(): # MenuButton
                    menu_button_codes.add(perm.code)
                for col_perm in role_obj.column.all(): # MenuColumnField
                    menu_column_codes.add(col_perm.code)
            
            code_list.update(menu_button_codes)
            code_list.update(menu_column_codes)
            logger.info(f"用户 {user.username} 的按钮权限码: {menu_button_codes}")
            logger.info(f"用户 {user.username} 的列权限码: {menu_column_codes}")
        else:
            logger.info("超级管理员，获取所有按钮和列权限码")
            # 超级管理员拥有所有权限
            all_button_codes = set(MenuButton.objects.values_list('code', flat=True))
            all_column_codes = set(MenuColumnField.objects.values_list('code', flat=True))
            code_list.update(all_button_codes)
            code_list.update(all_column_codes)
            logger.info(f"超级管理员获取的所有按钮权限码数量: {len(all_button_codes)}")
            logger.info(f"超级管理员获取的所有列权限码数量: {len(all_column_codes)}")

        final_code_list = list(code_list)
        logger.info(f"最终返回给用户的权限码列表 (共 {len(final_code_list)} 个): {final_code_list}")
        return FuResponse(data=final_code_list)
    except Exception as e:
        logger.error(f"获取用户权限码过程中发生未知错误: {e}", exc_info=True)
        return FuResponse(code=500, msg="获取权限码失败")
