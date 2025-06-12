# -*- coding: utf-8 -*-
# @Time    : 2022/5/10 21:56
# @Author  : Wick
# @FileName: post.py
# @Software: PyCharm

from typing import List

from django.shortcuts import get_object_or_404
from ninja import Field, ModelSchema, Query, Router, Schema, UploadedFile
from ninja.pagination import paginate
from system.models import Post
from utils.fu_crud import (
    ImportSchema,
    create,
    delete,
    export_data,
    import_data,
    retrieve,
    update,
)
from utils.fu_ninja import FuFilters, MyPagination

router = Router()


class Filters(FuFilters):
    name: str = Field(None, alias="name")
    code: str = Field(None, alias="code")
    status: int = Field(None, alias="status")

    id: str = Field(None, alias="post_id")


class PostSchemaIn(ModelSchema):
    class Config:
        model = Post
        model_fields = ['name', 'code', 'sort', 'status']


class PostSchemaOut(ModelSchema):
    creator: str = Field(None, alias="creator.username")

    class Config:
        model = Post
        model_fields = "__all__"


@router.post("/post", response=PostSchemaOut)
def create_post(request, data: PostSchemaIn):
    """创建新的岗位信息
    接收岗位数据，验证并保存到数据库。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"开始创建岗位，接收数据: {data.dict()}")
    try:
        # 检查岗位编码是否已存在 (如果 code 是唯一的)
        if Post.objects.filter(code=data.code).exists():
            logger.warning(f"创建岗位失败：岗位编码 '{data.code}' 已存在")
            return FuResponse(code=400, msg=f"岗位编码 '{data.code}' 已存在")
        
        post = create(request, data, Post) # fu_crud中的create函数
        logger.info(f"岗位 '{post.name}' (ID: {post.id}, 编码: {post.code}) 创建成功")
        return post
    except Exception as e:
        logger.error(f"创建岗位过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"创建岗位失败: {str(e)}")


@router.delete("/post/{post_id}")
def delete_post(request, post_id: int):
    """删除指定ID的岗位信息
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求删除岗位ID: {post_id}")
    try:
        # 检查岗位是否存在
        post_to_delete = get_object_or_404(Post, id=post_id)
        logger.info(f"准备删除岗位: '{post_to_delete.name}' (ID: {post_id})")
        
        # 注意：需要考虑岗位是否已被用户关联，如果有关联，可能需要给出提示或禁止删除
        # 例如: if Users.objects.filter(post__id=post_id).exists():
        #           logger.warning(f"删除岗位失败：岗位ID {post_id} 已被用户关联")
        #           return FuResponse(code=400, msg="岗位已被用户关联，无法删除")

        delete(post_id, Post) # fu_crud中的delete函数
        logger.info(f"岗位ID {post_id} 已成功删除")
        return FuResponse(data={"success": True}, msg="岗位删除成功")
    except Post.DoesNotExist:
        logger.warning(f"删除岗位失败：岗位ID {post_id} 未找到")
        return FuResponse(code=404, msg="岗位未找到")
    except Exception as e:
        logger.error(f"删除岗位ID {post_id} 过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"删除岗位失败: {str(e)}")


@router.put("/post/{post_id}", response=PostSchemaOut)
def update_post(request, post_id: int, data: PostSchemaIn):
    """更新指定ID的岗位信息
    接收岗位数据，验证并更新数据库中对应的岗位项。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求更新岗位ID: {post_id}，更新数据: {data.dict()}")
    try:
        # 检查岗位是否存在
        get_object_or_404(Post, id=post_id)
        logger.info(f"岗位ID {post_id} 存在，准备更新")

        # 检查岗位编码是否与现有其他岗位冲突 (如果 code 是唯一的)
        if Post.objects.filter(code=data.code).exclude(id=post_id).exists():
            logger.warning(f"更新岗位失败：岗位编码 '{data.code}' 已被其他岗位使用")
            return FuResponse(code=400, msg=f"岗位编码 '{data.code}' 已被其他岗位使用")

        updated_post = update(request, post_id, data, Post) # fu_crud中的update函数
        logger.info(f"岗位 '{updated_post.name}' (ID: {post_id}) 更新成功")
        return updated_post
    except Post.DoesNotExist:
        logger.warning(f"更新岗位失败：岗位ID {post_id} 未找到")
        return FuResponse(code=404, msg="岗位未找到")
    except Exception as e:
        logger.error(f"更新岗位ID {post_id} 过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"更新岗位失败: {str(e)}")


@router.get("/post", response=List[PostSchemaOut])
@paginate(MyPagination)
def list_post(request, filters: Filters = Query(...)):
    """获取岗位列表 (分页)
    根据提供的过滤条件查询岗位信息，并进行分页处理。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求获取岗位列表，过滤条件: {filters.dict(exclude_none=True)}")
    try:
        # retrieve 函数通常包含了数据权限过滤和查询逻辑
        qs = retrieve(request, Post, filters)
        logger.info(f"查询到岗位数据，准备分页返回")
        # 分页操作由 @paginate(MyPagination) 装饰器处理
        return qs
    except Exception as e:
        logger.error(f"获取岗位列表过程中发生错误: {e}", exc_info=True)
        # 此处直接返回空列表或向上抛出异常，具体取决于框架如何处理分页中的错误
        # 通常 @paginate 会处理异常，但添加日志总是个好习惯
        # 如果需要自定义错误响应，则不能直接返回qs，而是FuResponse
        # return FuResponse(code=500, msg=f"获取岗位列表失败: {str(e)}") # 如果不依赖paginate处理
        raise # 重新抛出异常，让分页装饰器或全局异常处理器处理


@router.get("/post/{post_id}", response=PostSchemaOut)
def get_post(request, post_id: int):
    """获取指定ID的单个岗位信息详情
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求获取岗位ID: {post_id} 的详细信息")
    try:
        post_item = get_object_or_404(Post, id=post_id)
        logger.info(f"成功获取到岗位 '{post_item.name}' (ID: {post_id}) 的信息")
        return post_item # Ninja会自动序列化模型实例
    except Post.DoesNotExist:
        logger.warning(f"获取岗位详情失败：岗位ID {post_id} 未找到")
        # get_object_or_404 会自动抛出 Http404，由Ninja处理
        # 若需统一FuResponse格式，可捕获并返回
        return FuResponse(code=404, msg="岗位未找到")
    except Exception as e:
        logger.error(f"获取岗位ID {post_id} 详情过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取岗位详情失败: {str(e)}")


@router.get("/post/all/list", response=List[PostSchemaOut])
def all_list_post(request):
    """获取所有岗位列表 (不分页)
    用于下拉选择等场景。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("请求获取所有岗位列表")
    try:
        # retrieve 函数在不传递 filters 时，通常返回所有数据
        # 需确认 retrieve 是否有内置的数据权限处理
        qs = retrieve(request, Post) 
        logger.info(f"查询到 {len(qs) if qs else 0} 条岗位数据")
        return qs
    except Exception as e:
        logger.error(f"获取所有岗位列表过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"获取所有岗位列表失败: {str(e)}")


@router.get("/post/all/export")
def export_post(request):
    """导出所有岗位数据为Excel文件
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("请求导出所有岗位数据")
    try:
        export_fields = ['name', 'code', 'status', 'sort', 'creator']
        logger.info(f"岗位数据导出字段: {export_fields}")
        # export_data 函数处理实际的导出逻辑并返回 HttpResponse
        response = export_data(request, Post, PostSchemaOut, export_fields)
        logger.info("岗位数据导出成功")
        return response
    except Exception as e:
        logger.error(f"导出岗位数据过程中发生错误: {e}", exc_info=True)
        # 返回一个表示错误的HTTP响应，或者让全局异常处理器处理
        # 根据 export_data 的实现，它可能自己处理异常或向上抛出
        # 此处假设 export_data 不会返回 FuResponse 对象，而是直接的 HttpResponse
        # 如果需要 FuResponse 风格的错误，需要调整
        from django.http import JsonResponse
        return JsonResponse({'code': 500, 'msg': f'导出失败: {str(e)}'}, status=500)


@router.post("/post/all/import")
def import_post(request, data: ImportSchema):
    """从Excel文件导入岗位数据
    接收包含文件ID的请求，读取文件内容并批量创建或更新岗位信息。
    需要认证访问。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求导入岗位数据，文件ID: {data.file_id if data else '未知'}") # 假设ImportSchema有file_id
    try:
        if not data or not hasattr(data, 'file_id') or not data.file_id:
            logger.warning("岗位数据导入请求无效：缺少文件ID")
            return FuResponse(code=400, msg="缺少导入文件信息")

        import_fields = ['name', 'code', 'status', 'sort']
        logger.info(f"岗位数据导入字段: {import_fields}")
        
        # import_data 函数处理实际的导入逻辑
        # 它可能返回一个包含成功和失败信息的字典或 FuResponse
        result = import_data(request, Post, PostSchemaIn, data, import_fields)
        logger.info(f"岗位数据导入完成，结果: {result}") # 假设result是可序列化的
        
        # 根据 import_data 的返回类型调整响应
        if isinstance(result, FuResponse):
            return result
        elif isinstance(result, dict) and ('success' in result or 'code' in result):
             # 假设 import_data 返回类似 {'success': True, 'msg': '导入成功', 'data': ...}
             # 或者 {'code': 200, 'msg': '导入成功', 'data': ...}
            return FuResponse(**result) if 'code' in result else FuResponse(data=result.get('data'), msg=result.get('msg', '操作成功'), code=200 if result.get('success') else 400)
        else:
            # 兜底处理，如果返回格式未知
            logger.warning(f"import_data 返回了未知格式的结果: {type(result)}")
            return FuResponse(data=result, msg="导入操作已执行，但结果格式未知")

    except Exception as e:
        logger.error(f"导入岗位数据过程中发生错误: {e}", exc_info=True)
        return FuResponse(code=500, msg=f"导入失败: {str(e)}")
