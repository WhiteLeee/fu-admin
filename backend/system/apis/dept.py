# from application.ninja_cof import api
# Author Wick
# coding=utf-8
# @Time    : 2022/5/15 21:47
# @File    : dept.py
# @Software: PyCharm
# @

from typing import List

from django.shortcuts import get_object_or_404
from ninja import Field, ModelSchema, Query, Router, Schema
from ninja.pagination import paginate
from system.models import Dept
from utils.fu_crud import create, delete, retrieve, update
from utils.fu_ninja import FuFilters, MyPagination
from utils.fu_response import FuResponse
from utils.list_to_tree import list_to_route, list_to_tree

router = Router()


class Filters(FuFilters):
    name: str = Field(None, alias="name")
    status: bool = Field(None, alias="status")
    id: str = Field(None, alias="id")


class SchemaIn(ModelSchema):
    parent_id: int = None

    class Config:
        model = Dept
        model_exclude = ['id', 'parent', 'create_datetime', 'update_datetime']


class SchemaOut(ModelSchema):
    class Config:
        model = Dept
        model_fields = "__all__"
    # model_fields = []


@router.post("/dept", response=SchemaOut)
def create_dept(request, data: SchemaIn):
    """创建部门信息"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"创建部门，请求数据: {data.dict()}")
    try:
        dept = create(request, data, Dept)
        logger.info(f"部门创建成功: {dept.id} - {dept.name}")
        return dept
    except Exception as e:
        logger.error(f"创建部门失败: {e}")
        return FuResponse(code=500, msg=f"创建部门失败: {e}")


@router.delete("/dept/{dept_id}")
def delete_dept(request, dept_id: int):
    """删除部门信息"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"删除部门，部门ID: {dept_id}")
    try:
        delete(dept_id, Dept)
        logger.info(f"部门 {dept_id} 删除成功")
        return {"success": True}
    except Exception as e:
        logger.error(f"删除部门 {dept_id} 失败: {e}")
        return FuResponse(code=500, msg=f"删除部门失败: {e}")


@router.put("/dept/{dept_id}", response=SchemaOut)
def update_dept(request, dept_id: int, data: SchemaIn):
    """更新部门信息"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"更新部门 {dept_id}，请求数据: {data.dict()}")
    try:
        dept = update(request, dept_id, data, Dept)
        logger.info(f"部门 {dept_id} 更新成功")
        return dept
    except Exception as e:
        logger.error(f"更新部门 {dept_id} 失败: {e}")
        return FuResponse(code=500, msg=f"更新部门失败: {e}")


@router.get("/dept", response=List[SchemaOut])
@paginate(MyPagination)
def list_dept(request, filters: Filters = Query(...)):
    """获取部门列表(分页)
    支持通过部门名称、状态进行过滤
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"获取部门列表，过滤条件: {filters.dict()}")
    try:
        qs = retrieve(request, Dept, filters)
        logger.info(f"查询到 {len(qs)} 条部门记录")
        return qs
    except Exception as e:
        logger.error(f"获取部门列表失败: {e}")
        return FuResponse(code=500, msg=f"获取部门列表失败: {e}")


@router.get("/dept/{dept_id}", response=SchemaOut)
def get_dept(request, dept_id: int):
    """获取单个部门信息"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"获取部门信息，部门ID: {dept_id}")
    try:
        dept = get_object_or_404(Dept, id=dept_id)
        logger.info(f"查询到部门: {dept.name}")
        return dept
    except Exception as e:
        logger.error(f"获取部门 {dept_id} 信息失败: {e}")
        return FuResponse(code=404, msg=f"部门不存在: {e}")


@router.get("/dept/list/tree")
def list_dept_tree(request, filters: Filters = Query(...)):
    """获取部门树形列表
    支持通过部门名称、状态进行过滤
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"获取部门树形列表，过滤条件: {filters.dict()}")
    try:
        qs = retrieve(request, Dept, filters).values()
        logger.info(f"查询到 {len(qs)} 条部门记录(用于构建树)")
        dept_tree = list_to_tree(list(qs))
        logger.info(f"生成部门树，包含 {len(dept_tree)} 个顶级部门")
        return FuResponse(data=dept_tree)
    except Exception as e:
        logger.error(f"获取部门树形列表失败: {e}")
        return FuResponse(code=500, msg=f"获取部门树形列表失败: {e}")
