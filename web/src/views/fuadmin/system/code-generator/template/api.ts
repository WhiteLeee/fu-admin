/**
 * -*- coding: utf-8 -*-
 * time: 2022/5/22 23:43
 * author: Wick
 * 
 */
import { defHttp } from '/@/utils/http/axios';

enum DeptApi {
  prefix = '/api/system/generator_template',
}

export const getList = (params) => {
  return defHttp.get({ url: DeptApi.prefix, params });
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

export const codeGenerator = (id) => {
  return defHttp.put({ url: DeptApi.prefix + '/code/generate/' + id });
};

export const dbGenerator = (id) => {
  return defHttp.put({ url: DeptApi.prefix + '/code/generate_db/' + id });
};

export const importData = (params) => {
  return defHttp.post({ url: DeptApi.prefix + '/all/import', params });
};

export const exportData = () => {
  return defHttp.get(
    { url: DeptApi.prefix + '/all/export', responseType: 'blob' },
    { isReturnNativeResponse: true },
  );
};

/**
 * 删除
 */

export const deleteItem = (id) => {
  return defHttp.delete({ url: DeptApi.prefix + '/' + id });
};
