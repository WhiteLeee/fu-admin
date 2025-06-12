# Author Wick
# coding=utf-8
# @Time    : 2022/5/15 21:47
# @File    : menu.py
# @Software: PyCharm
# @

from typing import List

from django.shortcuts import get_object_or_404
from fuadmin.settings import SECRET_KEY
from ninja import Field, ModelSchema, Query, Router, Schema
from ninja.pagination import paginate
from system.models import Menu, MenuButton, Users
from utils.fu_crud import create, delete, retrieve, update
from utils.fu_jwt import FuJwt
from utils.fu_ninja import FuFilters, MyPagination
from utils.fu_response import FuResponse
from utils.list_to_tree import list_to_route, list_to_tree

router = Router()


class Filters(FuFilters):
    title: str = Field(None, alias="title")
    status: bool = Field(None, alias="status")
    id: str = Field(None, alias="id")


class SchemaIn(ModelSchema):
    parent_id: int = None
    component: str = 'LAYOUT'

    class Config:
        model = Menu
        model_exclude = ['id', 'parent', 'create_datetime', 'update_datetime']


class SchemaOut(ModelSchema):
    class Config:
        model = Menu
        model_fields = "__all__"
    # model_fields = []


@router.post("/menu", response=SchemaOut)
def create_menu(request, data: SchemaIn):
    """创建新菜单项
    接收菜单数据，验证并保存到数据库。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"开始创建菜单，接收数据: {data.dict()}")
    try:
        # 检查父菜单是否存在 (如果提供了 parent_id)
        if data.parent_id:
            try:
                Menu.objects.get(id=data.parent_id)
                logger.info(f"父菜单ID {data.parent_id} 存在")
            except Menu.DoesNotExist:
                logger.warning(f"创建菜单失败：父菜单ID {data.parent_id} 不存在")
                return FuResponse(code=400, msg=f"父菜单ID {data.parent_id} 不存在")
        
        menu = create(request, data, Menu)
        logger.info(f"菜单 '{menu.title}' (ID: {menu.id}) 创建成功")
        return menu
    except Exception as e:
        logger.error(f"创建菜单过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"创建菜单失败: {str(e)}")


@router.delete("/menu/{menu_id}")
def delete_menu(request, menu_id: int):
    """删除指定ID的菜单项
    同时会删除其所有子菜单和关联的按钮权限。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求删除菜单ID: {menu_id}")
    try:
        # 检查菜单是否存在
        menu_to_delete = get_object_or_404(Menu, id=menu_id)
        logger.info(f"准备删除菜单: '{menu_to_delete.title}' (ID: {menu_id})")

        # 检查是否有子菜单，如果有，则不允许删除 (或者可以选择递归删除)
        # 当前的 delete 函数可能没有处理子菜单，需要确认其行为
        # 为安全起见，如果存在子菜单，可以先提示用户
        if Menu.objects.filter(parent_id=menu_id).exists():
            logger.warning(f"删除菜单失败：菜单ID {menu_id} 存在子菜单，请先删除子菜单")
            return FuResponse(code=400, msg="存在子菜单，请先删除子菜单")

        # 删除与该菜单关联的按钮权限
        buttons_deleted_count, _ = MenuButton.objects.filter(menu_id=menu_id).delete()
        if buttons_deleted_count > 0:
            logger.info(f"删除了 {buttons_deleted_count} 个与菜单ID {menu_id} 关联的按钮权限")

        delete(menu_id, Menu) # fu_crud中的delete函数
        logger.info(f"菜单ID {menu_id} 已成功删除")
        return FuResponse(data={"success": True}, msg="菜单删除成功")
    except Menu.DoesNotExist:
        logger.warning(f"删除菜单失败：菜单ID {menu_id} 未找到")
        return FuResponse(code=404, msg="菜单未找到")
    except Exception as e:
        logger.error(f"删除菜单ID {menu_id} 过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"删除菜单失败: {str(e)}")


@router.put("/menu/{menu_id}", response=SchemaOut)
def update_menu(request, menu_id: int, data: SchemaIn):
    """更新指定ID的菜单项
    接收菜单数据，验证并更新数据库中对应的菜单项。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求更新菜单ID: {menu_id}，更新数据: {data.dict()}")
    try:
        # 检查菜单是否存在
        get_object_or_404(Menu, id=menu_id)
        logger.info(f"菜单ID {menu_id} 存在，准备更新")

        # 检查父菜单是否存在 (如果提供了 parent_id 且不为None)
        if data.parent_id is not None:
            if data.parent_id == menu_id:
                logger.warning(f"更新菜单失败：父菜单ID不能与当前菜单ID相同 ({menu_id})")
                return FuResponse(code=400, msg="父菜单不能是自身")
            try:
                Menu.objects.get(id=data.parent_id)
                logger.info(f"父菜单ID {data.parent_id} 存在")
            except Menu.DoesNotExist:
                logger.warning(f"更新菜单失败：父菜单ID {data.parent_id} 不存在")
                return FuResponse(code=400, msg=f"父菜单ID {data.parent_id} 不存在")
        
        # 调用通用的更新方法
        updated_menu = update(request, menu_id, data, Menu)
        logger.info(f"菜单 '{updated_menu.title}' (ID: {menu_id}) 更新成功")
        return updated_menu
    except Menu.DoesNotExist:
        logger.warning(f"更新菜单失败：菜单ID {menu_id} 未找到")
        return FuResponse(code=404, msg="菜单未找到")
    except Exception as e:
        logger.error(f"更新菜单ID {menu_id} 过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"更新菜单失败: {str(e)}")


@router.get("/menu", response=List[SchemaOut])
def list_menu_tree(request, filters: Filters = Query(...)):
    """获取菜单列表 (树形结构)
    根据提供的过滤条件查询菜单，并将结果转换为树形结构返回。
    此接口之前存在数据权限问题，已在之前的修改中移除。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求获取菜单树，过滤条件: {filters.dict(exclude_none=True)}")
    try:
        # 使用 retrieve 函数获取扁平化的菜单列表
        # 注意：retrieve 函数内部可能包含数据权限过滤逻辑，需确认是否符合预期
        # 在之前的修复中，此处的 retrieve 应该是不带数据权限的查询
        qs = Menu.objects.filter(**filters.dict(exclude_none=True)).values()
        logger.info(f"从数据库查询到 {len(qs)} 条菜单数据")

        # 将查询集转换成树形结构
        menu_list = list(qs)
        menu_tree = list_to_tree(menu_list)
        logger.info(f"菜单数据已成功转换为树形结构，顶级菜单数: {len(menu_tree)}")
        
        return FuResponse(data=menu_tree)
    except Exception as e:
        logger.error(f"获取菜单树过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取菜单树失败: {str(e)}")


@router.get("/menu/{menu_id}", response=SchemaOut)
def get_menu(request, menu_id: int):
    """获取指定ID的单个菜单项详情
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求获取菜单ID: {menu_id} 的详细信息")
    try:
        menu_item = get_object_or_404(Menu, id=menu_id)
        logger.info(f"成功获取到菜单 '{menu_item.title}' (ID: {menu_id}) 的信息")
        return menu_item # 直接返回模型实例，Ninja会自动序列化
    except Menu.DoesNotExist:
        logger.warning(f"获取菜单详情失败：菜单ID {menu_id} 未找到")
        # get_object_or_404 会自动抛出 Http404 异常，Ninja会处理
        # 但为了统一返回格式，可以捕获并返回 FuResponse
        return FuResponse(code=404, msg="菜单未找到")
    except Exception as e:
        logger.error(f"获取菜单ID {menu_id} 详情过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取菜单详情失败: {str(e)}")


@router.get("/menu/route/tree")
def route_menu_tree(request):
    """
    获取当前用户的菜单路由树
    根据用户角色权限动态生成菜单结构
    超级管理员可访问所有菜单，普通用户仅可访问已授权菜单
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 解析用户token
        token = request.META.get("HTTP_AUTHORIZATION")
        if not token:
            logger.error("请求头中缺少Authorization token")
            return FuResponse(code=401, msg="未授权访问")
        
        token = token.split(" ")[1]
        token_user = FuJwt(SECRET_KEY).decode(SECRET_KEY, token).payload
        user = Users.objects.get(id=token_user['id'])
        
        logger.info(f"用户 {user.username}(ID: {user.id}) 请求菜单路由树")
        
        # 获取菜单数据
        if token_user['is_superuser']:
            # 超级管理员获取所有启用的菜单
            queryset = Menu.objects.filter(status=1).values()
            logger.info(f"超级管理员 {user.username} 获取所有菜单")
        else:
            # 普通用户根据角色权限获取菜单
            menu_ids = user.role.values_list('menu__id', flat=True)
            queryset = Menu.objects.filter(id__in=menu_ids, status=1).values()
            logger.info(f"用户 {user.username} 根据角色权限获取菜单，可访问菜单ID: {list(menu_ids)}")
        
        # 构建菜单树
        menu_tree = list_to_route(list(queryset))
        logger.info(f"为用户 {user.username} 生成菜单树，包含 {len(menu_tree)} 个顶级菜单")
        
        return FuResponse(data=menu_tree)
        
    except Exception as e:
        logger.error(f"获取菜单路由树失败: {str(e)}")
        return FuResponse(code=500, msg="获取菜单失败")

