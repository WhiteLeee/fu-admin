# from application.ninja_cof import api
# Author Wick
# coding=utf-8
# @Time    : 2022/5/29 01:36
# @File    : user.py
# @Software: PyCharm
# @

from typing import List

from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from ninja import Field, ModelSchema, Query, Router, Schema
from ninja.pagination import paginate
from system.models import Users
from utils.fu_crud import create, delete, retrieve
from utils.fu_ninja import FuFilters, MyPagination
from utils.fu_response import FuResponse
from utils.usual import get_user_info_from_token

router = Router()


class Filters(FuFilters):
    name: str = Field(None, alias="name")
    mobile: str = Field(None, alias="mobile")
    status: bool = Field(None, alias="status")
    dept_id__in: list = Field(None, alias="dept_ids[]")
    id: int = Field(None, alias="id")


class SchemaIn(ModelSchema):
    dept_id: int = Field(None, alias="dept")
    post: list = []
    role: list = []

    class Config:
        model = Users
        model_exclude = ['id', 'groups', 'user_permissions', 'is_superuser', 'dept', 'post', 'role', 'password',
                         'create_datetime', 'update_datetime']


class SchemaOut(ModelSchema):
    class Config:
        model = Users
        model_exclude = ['password']


@router.post("/user", response=SchemaOut)
def create_user(request, data: SchemaIn):
    """
    创建新用户，并关联岗位和角色。
    接收用户基本信息 (不含密码，密码将设为默认值 '123456')、岗位ID列表和角色ID列表。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    
    payload_dict = data.dict()
    logger.info(f"请求创建用户，接收数据: {payload_dict}")
    
    try:
        # 设置默认密码，使用 Django 的 make_password 进行哈希处理
        default_password = '123456'
        payload_dict['password'] = make_password(default_password)
        logger.info(f"用户 '{payload_dict.get('username')}' 将使用默认密码进行创建")
        
        # 提取多对多关系的ID列表，同时从payload_dict中移除它们
        post_ids = payload_dict.pop('post', [])
        role_ids = payload_dict.pop('role', [])
        
        logger.info(f"提取的岗位ID: {post_ids}")
        logger.info(f"提取的角色ID: {role_ids}")

        # 创建用户基本信息 (不包含多对多字段)
        # create 函数来自于 utils.fu_crud
        # Users 模型需要确保 username 字段是唯一的，否则 create 可能会失败
        user_instance = create(request, payload_dict, Users)
        logger.info(f"用户 '{user_instance.username}' (ID: {user_instance.id}) 基本信息创建成功")
        
        # 设置多对多关系：岗位 (post) 和角色 (role)
        if post_ids:
            user_instance.post.set(post_ids)
            logger.info(f"用户ID {user_instance.id} 关联岗位: {post_ids}")
        
        if role_ids:
            user_instance.role.set(role_ids)
            logger.info(f"用户ID {user_instance.id} 关联角色: {role_ids}")
            
        logger.info(f"用户 '{user_instance.username}' (ID: {user_instance.id}) 及关联信息创建完成")
        return user_instance
        
    except Exception as e:
        # 常见的异常可能是 IntegrityError (例如，用户名已存在)
        logger.error(f"创建用户过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"创建用户失败: {str(e)}")


@router.delete("/user/{user_id}")
def delete_user(request, user_id: int):
    """
    删除指定ID的用户。
    需要认证访问。
    注意：实际项目中可能需要考虑是否允许删除自己，或有其他业务约束。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求删除用户ID: {user_id}")

    try:
        # 检查用户是否存在
        user_to_delete = get_object_or_404(Users, id=user_id)
        logger.info(f"准备删除用户: {user_to_delete.username} (ID: {user_id})")

        # delete 函数来自于 utils.fu_crud
        delete(user_id, Users)
        logger.info(f"用户ID {user_id} 删除成功")
        return FuResponse(msg="用户删除成功") # 保持与原逻辑相似的返回，或使用FuResponse

    except Users.DoesNotExist:
        logger.warning(f"尝试删除的用户ID {user_id} 未找到")
        return FuResponse(code=404, msg="用户未找到")
    except Exception as e:
        logger.error(f"删除用户ID {user_id} 过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"删除用户失败: {str(e)}")


@router.put("/user/{user_id}", response=SchemaOut)
def update_user(request, user_id: int, payload: SchemaIn):
    """
    更新指定ID的用户信息，包括基本信息、岗位和角色关联。
    接收用户基本信息、岗位ID列表和角色ID列表。
    密码字段不会在此处更新，应通过专门的密码修改接口处理。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求更新用户ID: {user_id}，接收数据: {payload.dict()}")

    try:
        user_instance = get_object_or_404(Users, id=user_id)
        logger.info(f"找到待更新用户: {user_instance.username} (ID: {user_id})")

        payload_data = payload.dict(exclude_unset=True) # exclude_unset=True 使得未提供的字段不会被更新为None

        # 分别处理基本字段和多对多关系字段
        post_ids = payload_data.pop('post', None) # 使用None作为默认值，以便区分未提供和提供空列表的情况
        role_ids = payload_data.pop('role', None)

        # 更新用户基本信息字段 (排除密码等敏感或不应在此更新的字段)
        # SchemaIn 中已通过 model_exclude排除了 password
        for key, value in payload_data.items():
            if hasattr(user_instance, key):
                # 特别注意：如果 payload_data 中包含 password 字段，应在此处跳过或明确处理
                # 但根据 SchemaIn 的定义，password 已经被排除了
                setattr(user_instance, key, value)
                logger.info(f"更新用户 {user_id} 的基本字段 {key}: {value}")
            else:
                logger.warning(f"尝试更新用户 {user_id} 的未知字段 {key}")

        user_instance.save() # 保存基本信息变更
        logger.info(f"用户 {user_id} 基本信息更新完成")

        # 更新多对多关系：岗位 (post) 和角色 (role)
        if post_ids is not None:
            user_instance.post.set(post_ids)
            logger.info(f"用户 {user_id} 的岗位已更新为: {post_ids}")
        
        if role_ids is not None:
            user_instance.role.set(role_ids)
            logger.info(f"用户 {user_id} 的角色已更新为: {role_ids}")

        logger.info(f"用户 '{user_instance.username}' (ID: {user_id}) 信息及关联更新完成")
        return user_instance

    except Users.DoesNotExist:
        logger.warning(f"尝试更新的用户ID {user_id} 未找到")
        return FuResponse(code=404, msg="用户未找到")
    except Exception as e:
        logger.error(f"更新用户ID {user_id} 过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"更新用户失败: {str(e)}")


@router.get("/user", response=List[SchemaOut]) # 修改路由以匹配 /api/system/user
@paginate(MyPagination)
def list_user(request, filters: Filters = Query(...)):
    """
    获取用户列表，支持通过用户名、昵称、手机号、邮箱、状态和部门ID进行过滤。
    返回用户列表，包含基本信息，但不包含密码等敏感信息。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    filters_dict = filters.dict(exclude_none=True)
    logger.info(f"请求用户列表，过滤条件: {filters_dict}")

    try:
        qs = Users.objects.all()
        if filters_dict:
            # 特殊处理部门过滤，因为它是外键
            dept_id = filters_dict.pop('dept_id', None)
            if dept_id is not None:
                qs = qs.filter(dept_id=dept_id)
                logger.info(f"按部门ID {dept_id} 过滤")
            
            # 处理其他直接映射的过滤条件
            if filters_dict: # 检查是否还有其他过滤条件
                qs = qs.filter(**filters_dict)
                logger.info(f"应用其他过滤条件: {filters_dict}")
        
        # 预加载关联的部门、岗位和角色信息，以减少N+1查询问题
        # 注意：SchemaOut 中可能需要定义 depth 或显式指定关联字段的序列化方式
        qs = qs.select_related('dept').prefetch_related('post', 'role')

        user_list = list(qs)
        logger.info(f"查询到 {len(user_list)} 个用户")
        return user_list

    except Exception as e:
        logger.error(f"获取用户列表过程中发生错误: {e}", exc_info=True)
        # 根据项目的错误处理机制，这里可以返回一个空的列表或者一个包含错误信息的FuResponse
        # 为了保持与原接口行为一致（如果出错可能直接抛出500），这里暂时不改变返回类型
        # 但在实际项目中，统一的错误响应会更好
        # return FuResponse(code=500, msg=f"获取用户列表失败: {str(e)}")
        # 或者，如果希望在出错时返回空列表，可以这样做：
        # return [] 
        # 此处选择向上抛出异常，由全局异常处理器处理，或根据具体需求调整
        raise e


@router.get("/user/all/list", response=List[SchemaOut])
def all_list_user(request, filters: Filters = Query(...)):
    """
    获取所有用户列表，通常用于下拉选择等场景，不分页。
    支持通过用户名、昵称、手机号、邮箱、状态和部门ID进行过滤。
    返回用户列表，包含基本信息，但不包含密码等敏感信息。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    filters_dict = filters.dict(exclude_none=True)
    logger.info(f"请求所有用户列表（不分页），过滤条件: {filters_dict}")

    try:
        qs = Users.objects.all()
        if filters_dict:
            # 特殊处理部门过滤
            dept_id = filters_dict.pop('dept_id', None)
            if dept_id is not None:
                qs = qs.filter(dept_id=dept_id)
                logger.info(f"按部门ID {dept_id} 过滤")
            
            # 处理其他过滤条件
            if filters_dict:
                qs = qs.filter(**filters_dict)
                logger.info(f"应用其他过滤条件: {filters_dict}")

        # 预加载关联数据以优化性能
        qs = qs.select_related('dept').prefetch_related('post', 'role')

        user_list = list(qs)
        logger.info(f"查询到 {len(user_list)} 个用户（所有用户列表）")
        return user_list

    except Exception as e:
        logger.error(f"获取所有用户列表过程中发生错误: {e}", exc_info=True)
        # 考虑返回空列表或 FuResponse 错误对象
        # raise e # 或者向上抛出，由全局异常处理器处理
        return FuResponse(code=500, msg=f"获取所有用户列表失败: {str(e)}") # 示例：返回统一错误响应


@router.get("/user/{user_id}", response=SchemaOut)
def get_user(request, user_id: int):
    """
    获取指定ID的用户详细信息。
    返回用户基本信息、所属部门、关联岗位和角色。
    不包含密码等敏感信息。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求获取用户ID: {user_id} 的详细信息")

    try:
        # 使用 select_related 和 prefetch_related 优化查询性能
        # select_related 用于一对一和多对一关系 (如 dept)
        # prefetch_related 用于多对多和一对多关系 (如 post, role)
        user_instance = Users.objects.select_related('dept').prefetch_related('post', 'role').get(id=user_id)
        logger.info(f"成功获取用户 '{user_instance.username}' (ID: {user_id}) 的信息")
        return user_instance
    except Users.DoesNotExist:
        logger.warning(f"用户ID {user_id} 未找到")
        return FuResponse(code=404, msg="用户未找到")
    except Exception as e:
        logger.error(f"获取用户ID {user_id} 信息过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取用户信息失败: {str(e)}")


class UserPasswordUpdateIn(Schema):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码")

class UserResetPasswordIn(Schema):
    new_password: str = Field(..., description="新密码")


@router.put("/user/password/{user_id}")
def update_password(request, user_id: int, payload: UserPasswordUpdateIn):
    """
    修改指定用户的密码。
    需要提供旧密码和新密码。
    需要认证访问，并且通常只允许用户修改自己的密码，或管理员修改他人密码（需额外权限检查）。
    注意：此实现中未做权限检查，假设调用者有权修改目标用户密码。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求修改用户ID: {user_id} 的密码")

    try:
        user = get_object_or_404(Users, id=user_id)
        logger.info(f"找到用户: {user.username} (ID: {user_id})，准备修改密码")

        # 验证旧密码
        if not user.check_password(payload.old_password):
            logger.warning(f"用户 {user.username} (ID: {user_id}) 修改密码失败：旧密码错误")
            return FuResponse(code=400, msg="旧密码错误")

        # 检查新旧密码是否相同
        if payload.old_password == payload.new_password:
            logger.info(f"用户 {user.username} (ID: {user_id}) 修改密码：新旧密码相同，未做更改")
            return FuResponse(code=400, msg="新密码不能与旧密码相同")

        # 设置新密码
        user.set_password(payload.new_password)
        user.save(update_fields=["password"])
        logger.info(f"用户 {user.username} (ID: {user_id}) 的密码已成功修改")
        return FuResponse(msg="密码修改成功")

    except Users.DoesNotExist:
        logger.warning(f"尝试修改密码的用户ID {user_id} 未找到")
        return FuResponse(code=404, msg="用户未找到")
    except Exception as e:
        logger.error(f"修改用户ID {user_id} 密码过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"密码修改失败: {str(e)}")


@router.put("/user/reset/password/{user_id}")
def reset_password(request, user_id: int, payload: UserResetPasswordIn):
    """
    重置指定用户的密码（通常由管理员操作）。
    直接设置新密码，不需要旧密码验证。
    需要认证访问和相应的管理员权限（本实现未做权限检查）。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求重置用户ID: {user_id} 的密码")

    try:
        user = get_object_or_404(Users, id=user_id)
        logger.info(f"找到用户: {user.username} (ID: {user_id})，准备重置密码")

        # 检查新密码是否为空或无效 (根据 UserResetPasswordIn 的校验)
        if not payload.new_password:
            logger.warning(f"用户 {user.username} (ID: {user_id}) 重置密码失败：新密码不能为空")
            return FuResponse(code=400, msg="新密码不能为空")

        # 设置新密码
        user.set_password(payload.new_password)
        user.save(update_fields=["password"])
        logger.info(f"用户 {user.username} (ID: {user_id}) 的密码已成功重置")
        return FuResponse(msg="密码重置成功")

    except Users.DoesNotExist:
        logger.warning(f"尝试重置密码的用户ID {user_id} 未找到")
        return FuResponse(code=404, msg="用户未找到")
    except Exception as e:
        logger.error(f"重置用户ID {user_id} 密码过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"密码重置失败: {str(e)}")
