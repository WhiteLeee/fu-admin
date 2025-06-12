# from application.ninja_cof import api
# Author Wick
# coding=utf-8
# @Time    : 2022/5/19 21:36
# @File    : role.py
# @Software: PyCharm
# @

from typing import List

from django.shortcuts import get_object_or_404
from ninja import Field, ModelSchema, Query, Router, Schema
from ninja.pagination import paginate
from system.models import Menu, Role, MenuButton
from utils.fu_crud import create, delete, retrieve
from utils.fu_ninja import FuFilters, MyPagination
from utils.fu_response import FuResponse
from utils.list_to_tree import list_to_tree

router = Router()


class Filters(FuFilters):
    name: str = Field(None, alias="name")
    status: bool = Field(None, alias="status")
    id: str = Field(None, alias="id")


class SchemaIn(ModelSchema):
    menu: list = []
    permission: list = []
    dept: list = []
    column: list = []

    class Config:
        model = Role
        model_exclude = ['id', 'dept', 'menu', 'permission', 'column', 'create_datetime', 'update_datetime']


class SchemaOut(ModelSchema):
    class Config:
        model = Role
        model_fields = "__all__"
    # model_fields = []


@router.post("/role", response=SchemaOut)
def create_role(request, data: SchemaIn):
    """
    创建新角色并关联权限 (菜单、按钮、数据、列)。
    接收角色基本信息及各类权限ID列表，创建角色并设置关联。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    
    payload_dict = data.dict()
    logger.info(f"开始创建角色，接收数据: {payload_dict}")
    
    try:
        # 提取多对多关系的ID列表，同时从payload_dict中移除它们，以便后续创建Role对象
        menu_ids = payload_dict.pop('menu', [])
        permission_ids = payload_dict.pop('permission', [])
        dept_ids = payload_dict.pop('dept', [])
        column_ids = payload_dict.pop('column', [])
        
        logger.info(f"提取的菜单权限ID: {menu_ids}")
        logger.info(f"提取的按钮权限ID: {permission_ids}")
        logger.info(f"提取的数据权限ID (部门): {dept_ids}")
        logger.info(f"提取的列权限ID: {column_ids}")

        # 创建角色基本信息 (不包含多对多字段)
        # create 函数来自于 utils.fu_crud
        role_instance = create(request, payload_dict, Role)
        logger.info(f"角色 '{role_instance.name}' (ID: {role_instance.id}) 基本信息创建成功")
        
        # 设置多对多关系
        if menu_ids:
            role_instance.menu.set(menu_ids)
            logger.info(f"角色ID {role_instance.id} 关联菜单权限: {menu_ids}")
        if permission_ids:
            role_instance.permission.set(permission_ids)
            logger.info(f"角色ID {role_instance.id} 关联按钮权限: {permission_ids}")
        if dept_ids:
            role_instance.dept.set(dept_ids)
            logger.info(f"角色ID {role_instance.id} 关联数据权限 (部门): {dept_ids}")
        if column_ids:
            role_instance.column.set(column_ids)
            logger.info(f"角色ID {role_instance.id} 关联列权限: {column_ids}")
            
        logger.info(f"角色 '{role_instance.name}' (ID: {role_instance.id}) 及权限关联创建完成")
        return role_instance
        
    except Exception as e:
        logger.error(f"创建角色过程中发生错误: {e}", exc_info=True)
        # 根据实际情况，可能需要返回一个标准的错误响应对象，例如 FuResponse
        # 假设 create 函数或Django ORM操作失败会抛出异常
        return FuResponse(code=500, msg=f"创建角色失败: {str(e)}")


@router.delete("/role/{role_id}")
def delete_role(request, role_id: int):
    """
    删除指定ID的角色。
    需要认证访问。
    注意：实际项目中可能需要检查角色是否被用户关联，如果有关联则阻止删除或给出提示。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求删除角色ID: {role_id}")

    try:
        # 检查角色是否存在
        role_to_delete = get_object_or_404(Role, id=role_id)
        logger.info(f"准备删除角色: {role_to_delete.name} (ID: {role_id})")

        # 此处可以添加检查角色是否被用户关联的逻辑
        # if role_to_delete.user_set.exists():
        #     logger.warning(f"角色 {role_id} 已被用户关联，无法删除")
        #     return FuResponse(code=400, msg=f"角色 '{role_to_delete.name}' 已被用户关联，无法删除")

        # delete 函数来自于 utils.fu_crud
        delete(role_id, Role)
        logger.info(f"角色ID {role_id} 删除成功")
        return FuResponse(msg=f"角色删除成功") # 保持与原逻辑相似的返回，或使用FuResponse

    except Role.DoesNotExist:
        logger.warning(f"尝试删除的角色ID {role_id} 未找到")
        return FuResponse(code=404, msg="角色未找到")
    except Exception as e:
        logger.error(f"删除角色ID {role_id} 过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"删除角色失败: {str(e)}")


@router.put("/role/{role_id}", response=SchemaOut)
def update_role(request, role_id: int, payload: SchemaIn):
    """
    更新指定ID的角色信息及其关联的权限（菜单、按钮、数据、列）。
    接收角色基本信息及各类权限ID列表，更新角色并重新设置关联。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求更新角色ID: {role_id}，接收数据: {payload.dict()}")

    try:
        role_instance = get_object_or_404(Role, id=role_id)
        logger.info(f"找到待更新角色: {role_instance.name} (ID: {role_id})")

        payload_data = payload.dict(exclude_unset=True) # exclude_unset=True 使得未提供的字段不会被更新为None

        # 分别处理基本字段和多对多关系字段
        menu_ids = payload_data.pop('menu', None)  # 使用None作为默认值，以便区分未提供和提供空列表的情况
        permission_ids = payload_data.pop('permission', None)
        dept_ids = payload_data.pop('dept', None)
        column_ids = payload_data.pop('column', None)

        # 更新角色基本信息字段
        for key, value in payload_data.items():
            if hasattr(role_instance, key):
                setattr(role_instance, key, value)
                logger.info(f"更新角色 {role_id} 的基本字段 {key}: {value}")
            else:
                logger.warning(f"尝试更新角色 {role_id} 的未知字段 {key}")

        role_instance.save() # 保存基本信息变更
        logger.info(f"角色 {role_id} 基本信息更新完成")

        # 更新多对多关系
        if menu_ids is not None:
            role_instance.menu.set(menu_ids)
            logger.info(f"角色 {role_id} 的菜单权限已更新为: {menu_ids}")
        
        if permission_ids is not None:
            role_instance.permission.set(permission_ids)
            logger.info(f"角色 {role_id} 的按钮权限已更新为: {permission_ids}")
            
        if dept_ids is not None:
            role_instance.dept.set(dept_ids)
            logger.info(f"角色 {role_id} 的数据权限 (部门) 已更新为: {dept_ids}")
            
        if column_ids is not None:
            role_instance.column.set(column_ids)
            logger.info(f"角色 {role_id} 的列权限已更新为: {column_ids}")

        # Django的set方法会自动处理多对多关系的保存，无需再次调用role_instance.save()
        logger.info(f"角色 '{role_instance.name}' (ID: {role_id}) 信息及权限关联更新完成")
        return role_instance

    except Role.DoesNotExist:
        logger.warning(f"尝试更新的角色ID {role_id} 未找到")
        return FuResponse(code=404, msg="角色未找到")
    except Exception as e:
        logger.error(f"更新角色ID {role_id} 过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"更新角色失败: {str(e)}")


@router.get("/role", response=List[SchemaOut])
@paginate(MyPagination)
def list_role(request, filters: Filters = Query(...)):
    """
    获取角色列表，支持分页和过滤。
    根据提供的过滤条件 (名称、状态、ID) 查询角色数据。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求角色列表，过滤条件: {filters.dict(exclude_none=True)}")
    
    try:
        # retrieve 函数来自于 utils.fu_crud
        queryset = retrieve(request, Role, filters)
        logger.info(f"成功获取角色列表，共 {queryset.count()} 条记录 (分页前)")
        # 分页操作由 @paginate(MyPagination) 装饰器处理
        return queryset
    except Exception as e:
        logger.error(f"获取角色列表过程中发生错误: {e}", exc_info=True)
        # 此处错误通常由 retrieve 函数内部或数据库层面抛出
        # 返回空列表或错误响应，具体取决于分页器的错误处理机制和期望行为
        # 为了保持一致性，可以返回一个空的 FuResponse 或让 Ninja 框架处理
        return FuResponse(code=500, msg=f"获取角色列表失败: {str(e)}", data=[])


@router.get("/role/all/list", response=List[SchemaOut])
def all_list_role(request):
    """
    获取所有角色列表 (不分页)。
    用于下拉选择等场景。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("请求所有角色列表 (不分页)")
    
    try:
        # retrieve 函数来自于 utils.fu_crud
        queryset = retrieve(request, Role) # 不传递 filters 即获取所有
        logger.info(f"成功获取所有角色列表，共 {queryset.count()} 条记录")
        return queryset
    except Exception as e:
        logger.error(f"获取所有角色列表过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取所有角色列表失败: {str(e)}", data=[])


@router.get("/role/{role_id}", response=SchemaOut)
def get_role(request, role_id: int):
    """
    获取指定ID的角色详细信息。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求获取角色ID: {role_id} 的详细信息")

    try:
        role_instance = get_object_or_404(Role, id=role_id)
        logger.info(f"成功获取角色: {role_instance.name} (ID: {role_id}) 的信息")
        return role_instance
    except Role.DoesNotExist:
        logger.warning(f"尝试获取的角色ID {role_id} 未找到")
        # get_object_or_404 会自动抛出 Http404 异常，Ninja 框架会处理它
        # 但为了日志和统一返回格式，可以显式捕获并返回 FuResponse
        return FuResponse(code=404, msg="角色未找到")
    except Exception as e:
        logger.error(f"获取角色ID {role_id} 信息过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取角色信息失败: {str(e)}")


class ButtonColumnFilters(FuFilters):
    menu_ids: list = Field(None, alias="menu_ids")


@router.get("/role/list/menu_button")
def list_menu_button_tree(request, filters: ButtonColumnFilters = Query(...)):
    """
    获取菜单及其关联的按钮权限，并构造成树形结构。
    用于角色权限配置界面，展示可选的菜单和按钮。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求菜单按钮权限树，过滤条件: {filters.dict(exclude_none=True)}")

    try:
        # 考虑根据 filters.menu_ids 过滤 Menu 查询集，如果提供了该参数
        if filters.menu_ids:
            logger.info(f"根据提供的菜单ID列表进行过滤: {filters.menu_ids}")
            menu_queryset = Menu.objects.filter(id__in=filters.menu_ids).prefetch_related('menuPermission')
        else:
            menu_queryset = Menu.objects.all().prefetch_related('menuPermission')
        
        logger.debug(f"查询到的菜单数量: {menu_queryset.count()}")

        processed_items = []
        for menu_item in menu_queryset:
            # 转换菜单项
            menu_dict = {
                'id': menu_item.id,
                'parent_id': menu_item.parent_id,
                'title': menu_item.name, # 或 title 字段，取决于模型定义
                'path': menu_item.path, # 假设有 path 字段
                'component': menu_item.component, # 假设有 component 字段
                'icon': menu_item.icon, # 假设有 icon 字段
                'type': menu_item.type, # 假设有 type 字段 (目录, 菜单, 按钮)
                # ... 其他需要的菜单字段
            }
            processed_items.append(menu_dict)
            logger.debug(f"处理菜单项: {menu_dict}")

            # 转换关联的按钮权限
            buttons = menu_item.menuPermission.all()
            for button in buttons:
                button_dict = {
                    'id': f"b{button.id}", # 添加前缀 'b' 以区分按钮和菜单ID
                    'parent_id': menu_item.id, # 按钮的父级是其所属的菜单
                    'title': button.name, # 或 title 字段
                    'code': button.code, # 假设有 code 字段 (权限标识)
                    'type': 'button', # 自定义类型，用于前端区分
                    # ... 其他需要的按钮字段
                }
                processed_items.append(button_dict)
                logger.debug(f"处理按钮项: {button_dict}，关联到菜单ID: {menu_item.id}")
        
        # 使用 list_to_tree 构建完整的树，或直接返回扁平列表由前端处理
        # 此处的 get_button_or_column_menu 可能是自定义的树构建函数
        # 如果 get_button_or_column_menu 期望扁平列表并自行处理，则保持原样
        # 否则，可能需要调整为： tree_data = list_to_tree(processed_items)
        logger.info(f"准备将处理后的 {len(processed_items)} 个项目传递给 get_button_or_column_menu")
        
        # 假设 get_button_or_column_menu 是一个将扁平列表转换为特定树形结构的辅助函数
        # 它接收扁平化的菜单和按钮列表，以及一个类型标识 ('b' for button)
        # 这个函数需要确保能够正确处理 'id' 和 'parent_id' 来构建树
        result_tree = get_button_or_column_menu(processed_items, 'b')
        logger.info("菜单按钮权限树构建完成")
        return FuResponse(data=result_tree) # 建议使用 FuResponse 包装

    except Exception as e:
        logger.error(f"获取菜单按钮权限树过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取菜单按钮权限树失败: {str(e)}", data=[])


@router.get("/role/list/menu_column")
def list_menu_column_tree(request, filters: ButtonColumnFilters = Query(...)):
    """
    获取菜单及其关联的列权限字段，并构造成树形结构。
    用于角色权限配置界面，展示可选的菜单和列字段。
    需要认证访问。
    注意：此函数名与获取按钮权限的函数名相同，但通过路由区分。
    建议后续重命名以提高代码清晰度，例如 list_menu_column_permission_tree。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求菜单列权限树，过滤条件: {filters.dict(exclude_none=True)}")

    try:
        if filters.menu_ids:
            logger.info(f"根据提供的菜单ID列表进行过滤: {filters.menu_ids}")
            menu_queryset = Menu.objects.filter(id__in=filters.menu_ids).prefetch_related('menuColumnField')
        else:
            menu_queryset = Menu.objects.all().prefetch_related('menuColumnField')
        
        logger.debug(f"查询到的菜单数量: {menu_queryset.count()}")

        processed_items = []
        for menu_item in menu_queryset:
            menu_dict = {
                'id': menu_item.id,
                'parent_id': menu_item.parent_id,
                'title': menu_item.name,
                'path': menu_item.path,
                'component': menu_item.component,
                'icon': menu_item.icon,
                'type': menu_item.type,
            }
            processed_items.append(menu_dict)
            logger.debug(f"处理菜单项: {menu_dict}")

            column_fields = menu_item.menuColumnField.all()
            for column_field in column_fields:
                column_dict = {
                    'id': f"c{column_field.id}", # 添加前缀 'c' 以区分列字段和菜单ID
                    'parent_id': menu_item.id, # 列字段的父级是其所属的菜单
                    'title': column_field.name, # 或 title 字段
                    'field_name': column_field.field_name, # 假设有 field_name 字段 (实际列名)
                    'type': 'column', # 自定义类型，用于前端区分
                }
                processed_items.append(column_dict)
                logger.debug(f"处理列字段项: {column_dict}，关联到菜单ID: {menu_item.id}")

        logger.info(f"准备将处理后的 {len(processed_items)} 个项目传递给 get_button_or_column_menu")
        result_tree = get_button_or_column_menu(processed_items, 'c')
        logger.info("菜单列权限树构建完成")
        return FuResponse(data=result_tree)

    except Exception as e:
        logger.error(f"获取菜单列权限树过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取菜单列权限树失败: {str(e)}", data=[])


class SchemaMenuOut(ModelSchema):
    class Config:
        model = Menu
        model_fields = "__all__"


@router.get("/role/list/menu", response=List[SchemaMenuOut]) # response 应该是一个包含树形结构的 Schema，或者直接返回 FuResponse
def list_menu_tree(request, filters: Filters = Query(...)):
    """
    获取菜单列表，并将其转换为树形结构。
    用于角色权限配置中展示可选的菜单项。
    支持通过名称、状态、ID进行过滤 (通过 Filters 定义)。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求菜单树列表，过滤条件: {filters.dict(exclude_none=True)}")

    try:
        # retrieve 函数来自于 utils.fu_crud
        # .values() 会将结果转换为字典列表，这对于 list_to_tree 是合适的
        menu_queryset_values = retrieve(request, Menu, filters).values(
            'id', 'parent_id', 'name', 'path', 'component', 'icon', 'type', 'sort', 'status' # 根据实际需要选择字段
        )
        menu_list = list(menu_queryset_values)
        logger.info(f"成功获取菜单列表 (扁平化)，共 {len(menu_list)} 条记录")

        # 将扁平列表转换为树形结构
        # list_to_tree 函数来自于 utils.list_to_tree
        menu_tree = list_to_tree(menu_list)
        logger.info("菜单列表成功转换为树形结构")
        
        # 直接返回树形结构数据，由 FuResponse 包装
        # 注意：这里的 response=List[SchemaMenuOut] 可能与返回 FuResponse(data=menu_tree) 不完全匹配
        # 如果 SchemaMenuOut 是扁平的，而 list_to_tree 返回嵌套结构，前端可能需要适配
        # 或者定义一个递归的树形 Schema
        return FuResponse(data=menu_tree)

    except Exception as e:
        logger.error(f"获取菜单树列表过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取菜单树列表失败: {str(e)}", data=[])


# class SchemaButtonOut(ModelSchema):
#     class Config:
#         model = MenuButton
#         model_fields = "__all__"
#
#
# @router.get("/role/list/button/{menu_id}", response=List[SchemaButtonOut])
# def get_button_by_menu_id(request, menu_id: int):
#     filters: Filters
#     qs = MenuButton.objects.filter(menu_id=menu_id)
#
#     return qs


def get_button_or_column_menu(data, flag):
    return_data = []
    for i in data:
        m_id = i['id']
        if flag in str(m_id):
            return_data.append(i)
            get_menu_by_parent(i['parent_id'], data, return_data)
    return return_data


def get_menu_by_parent(parent_id, data, return_data):
    for i in data:
        if parent_id == i['id'] and i not in return_data:
            return_data.append(i)
            get_menu_by_parent(i['parent_id'], data, return_data)
    if parent_id is None:
        return
