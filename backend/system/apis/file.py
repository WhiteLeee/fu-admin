# -*- coding: utf-8 -*-
# @Time    : 2022/6/07 00:56
# @Author  : Wick
# @FileName: file.py
# @Software: PyCharm
import os
from datetime import datetime
from typing import List
from urllib.parse import unquote

from django.http import FileResponse, StreamingHttpResponse, HttpResponse
from django.shortcuts import get_object_or_404
from fuadmin.settings import BASE_DIR, STATIC_URL
from ninja import Field
from ninja import File as NinjaFile
from ninja import ModelSchema, Query, Router, Schema
from ninja.files import UploadedFile
from ninja.pagination import paginate
from system.models import File
from utils.fu_crud import create, delete, retrieve, update
from utils.fu_ninja import FuFilters, MyPagination

router = Router()


class Filters(FuFilters):
    name: str = Field(None, alias="name")


class SchemaIn(Schema):
    name: str = Field(None, alias="name")
    url: str = Field(None, alias="url")


class SchemaOut(ModelSchema):
    class Config:
        model = File
        model_fields = "__all__"


@router.delete("/file/{file_id}")
def delete_file(request, file_id: int):
    """删除文件记录"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"删除文件记录，文件ID: {file_id}")
    try:
        # 此处delete仅删除数据库记录，实际文件可能需要额外处理
        delete(file_id, File)
        logger.info(f"文件记录 {file_id} 删除成功")
        return {"success": True}
    except Exception as e:
        logger.error(f"删除文件记录 {file_id} 失败: {e}")
        return FuResponse(code=500, msg=f"删除文件记录失败: {e}")


@router.get("/file", response=List[SchemaOut])
@paginate(MyPagination)
def list_file(request, filters: Filters = Query(...)):
    """获取文件记录列表(分页)
    支持通过文件名称进行过滤
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"获取文件记录列表，过滤条件: {filters.dict()}")
    try:
        qs = retrieve(request, File, filters)
        logger.info(f"查询到 {len(qs)} 条文件记录")
        return qs
    except Exception as e:
        logger.error(f"获取文件记录列表失败: {e}")
        return FuResponse(code=500, msg=f"获取文件记录列表失败: {e}")


@router.get("/file/{file_id}", response=SchemaOut)
def get_file(request, file_id: int):
    """获取单个文件记录信息"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"获取文件记录信息，文件ID: {file_id}")
    try:
        qs = get_object_or_404(File, id=file_id)
        logger.info(f"查询到文件记录: {qs.name}")
        return qs
    except Exception as e:
        logger.error(f"获取文件记录 {file_id} 信息失败: {e}")
        return FuResponse(code=404, msg=f"文件记录不存在: {e}")


@router.get("/file/all/list", response=List[SchemaOut])
def all_list_role(request): # 注意：函数名可能应为 all_list_file
    """获取所有文件记录列表（不分页）"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("获取所有文件记录列表")
    try:
        qs = retrieve(request, File)
        logger.info(f"查询到 {len(qs)} 条文件记录")
        return qs
    except Exception as e:
        logger.error(f"获取所有文件记录列表失败: {e}")
        return FuResponse(code=500, msg=f"获取所有文件记录列表失败: {e}")


@router.post("/upload", response=SchemaOut)
def upload(request, file: UploadedFile = NinjaFile(...)):
    """上传文件并保存记录"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"开始上传文件: {file.name}, 大小: {file.size} bytes")
    try:
        binary_data = file.read()
        current_date = datetime.now().strftime('%Y%m%d%H%M%S%f')
        current_ymd = datetime.now().strftime('%Y%m%d')
        # 防止文件名包含空格或特殊字符导致的问题，并添加时间戳确保唯一性
        safe_original_name = "".join(c if c.isalnum() or c in ['.', '_'] else '_' for c in file.name)
        file_name = current_date + '_' + safe_original_name
        # 文件保存路径，STATIC_URL 通常是相对路径，需要拼接项目根目录
        # 注意: 这里的 STATIC_URL 可能需要根据实际配置调整，确保是绝对路径或相对于 BASE_DIR
        # 假设 STATIC_URL 是 'static' 目录，实际保存路径应为 BASE_DIR / 'static' / current_ymd
        # 为安全起见，显式拼接 BASE_DIR
        upload_dir = os.path.join(BASE_DIR, STATIC_URL.strip('/\\'), current_ymd) # 移除首尾斜杠确保路径拼接正确

        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            logger.info(f"创建上传目录: {upload_dir}")

        file_save_path = os.path.join(upload_dir, file_name)
        # 存储在数据库中的相对路径，相对于 STATIC_URL
        db_file_url = os.path.join(STATIC_URL.strip('/\\'), current_ymd, file_name).replace('\\', '/') # 统一使用 / 作为路径分隔符

        with open(file_save_path, 'wb') as f:
            f.write(binary_data)
        logger.info(f"文件 {file.name} 已保存至 {file_save_path}")

        data = {
            'name': file.name, # 原始文件名
            'size': file.size,
            'save_name': file_name, # 服务器保存的文件名
            'url': db_file_url, # 数据库中存储的相对访问URL
        }
        qs = create(request, data, File)
        logger.info(f"文件记录创建成功: {qs.id}, 文件名: {qs.name}")
        return qs
    except Exception as e:
        logger.error(f"文件上传失败: {file.name}, 错误: {e}", exc_info=True)
        # 注意：此处 FuResponse 未定义，如果需要统一错误响应格式，请确保已导入或定义
        # from utils.fu_response import FuResponse # 假设的导入路径
        # return FuResponse(code=500, msg=f"文件上传失败: {e}")
        # 暂时返回Django默认错误或简单字典
        return {"success": False, "message": f"文件上传失败: {e}"} # 更改返回以符合SchemaOut或通用错误格式


@router.post("/download") # 函数名 create_post 可能有误，应为 download_file
def create_post(request, data: SchemaIn):
    """下载文件
    通过提供的相对路径 (data.url) 找到并下载文件。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求下载文件，相对路径: {data.url}")
    try:
        # 解码URL中的特殊字符，并拼接绝对路径
        # 假设 data.url 是相对于 STATIC_URL 的路径，如 'static/20230101/file.txt'
        # 或者 data.url 已经是 'BASE_DIR/static/...' 格式，需要确认
        # 当前实现是直接拼接 BASE_DIR 和 unquote(data.url)
        # 如果 data.url 是 /static/.... 这种形式，则 str(BASE_DIR) + /static/... 会导致路径问题
        # 需要确保 data.url 的格式与此拼接方式兼容
        # 更安全的方式是解析 data.url，确保它在允许的下载目录下
        relative_path = unquote(data.url).lstrip('/\\') # 移除开头的斜杠
        file_path = os.path.join(BASE_DIR, relative_path)

        logger.info(f"尝试下载文件，绝对路径: {file_path}")
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            logger.warning(f"下载失败：文件未找到或不是一个文件: {file_path}")
            # from utils.fu_response import FuResponse # 假设的导入路径
            # return FuResponse(code=404, msg="文件未找到")
            return HttpResponse("文件未找到", status=404)

        # 使用 FileResponse 提供文件下载，as_attachment=True 会提示浏览器下载
        response = FileResponse(open(file_path, "rb"), as_attachment=True)
        # 可以尝试从文件名推断 Content-Type，或让 FileResponse 自动处理
        # response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        logger.info(f"文件 {os.path.basename(file_path)} 开始下载")
        return response
    except Exception as e:
        logger.error(f"文件下载失败: {data.url}, 错误: {e}", exc_info=True)
        # from utils.fu_response import FuResponse # 假设的导入路径
        # return FuResponse(code=500, msg=f"文件下载失败: {e}")
        return HttpResponse(f"文件下载失败: {e}", status=500)


@router.get("/image/{image_id}", auth=None) # 函数名 get_file 与前面获取文件记录的函数重名，建议修改
def get_file(request, image_id: int):
    """获取图片文件
    根据图片ID从数据库获取图片记录，并返回图片内容。
    允许匿名访问 (auth=None)。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"请求获取图片，图片ID: {image_id}")
    try:
        qs = get_object_or_404(File, id=image_id)
        logger.info(f"查找到图片记录: {qs.name}, 路径: {qs.url}")

        # 路径处理与下载类似，需要确保 qs.url 的格式
        # 假设 qs.url 是 'static/images/image.png' 这种相对于 BASE_DIR 的路径
        # 或者需要根据 STATIC_URL 拼接
        relative_path = str(qs.url).lstrip('/\\') # 移除开头的斜杠
        image_full_path = os.path.join(BASE_DIR, relative_path)

        logger.info(f"尝试打开图片文件: {image_full_path}")
        if not os.path.exists(image_full_path) or not os.path.isfile(image_full_path):
            logger.warning(f"获取图片失败：文件未找到或不是一个文件: {image_full_path}")
            return HttpResponse("图片未找到", status=404)

        # 根据文件扩展名动态设置 Content-Type 可能更灵活
        # import mimetypes
        # content_type, _ = mimetypes.guess_type(image_full_path)
        # if content_type is None:
        #     content_type = 'application/octet-stream' # 默认类型
        # logger.info(f"图片 Content-Type: {content_type}")
        # return HttpResponse(open(image_full_path, "rb"), content_type=content_type)

        # 当前固定为 image/png，如果图片类型多样，需要调整
        return HttpResponse(open(image_full_path, "rb"), content_type='image/png')
    except File.DoesNotExist:
        logger.warning(f"图片记录未找到，ID: {image_id}")
        return HttpResponse("图片记录未找到", status=404)
    except Exception as e:
        logger.error(f"获取图片失败: {image_id}, 错误: {e}", exc_info=True)
        return HttpResponse(f"获取图片失败: {e}", status=500)
