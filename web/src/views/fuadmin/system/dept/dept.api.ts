/**
 * -*- coding: utf-8 -*-
 * time: 2022/5/3 23:52
 * author: Wick
 * 
 */
import { defHttp } from '/@/utils/http/axios';

enum DeptApi {
  prefix = '/api/system/dept',
  GetDeptList = '/api/system/dept/list/tree',
}

/**
 * 获取菜单
 */

export const getDeptList = (params) => {
  return defHttp.get({ url: DeptApi.GetDeptList, params });
};

/**
 * 保存或更新
 */

export const createOrUpdate = (params, isUpdate) => {
  if (isUpdate) {
    return defHttp.put({ url: DeptApi.prefix + '/' + params.id, params });
  } else {
    return defHttp.post({ url: DeptApi.prefix, params });
  }
};

/**
 * 删除
 */

export const deleteItem = (id) => {
  return defHttp.delete({ url: DeptApi.prefix + '/' + id });
};
