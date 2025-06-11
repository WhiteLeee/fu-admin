/**
 * -*- coding: utf-8 -*-
 * time: 2022/5/22 23:43
 * author: Wick
 * 
 */
import { defHttp } from '/@/utils/http/axios';

enum DeptApi {
  prefix = '/api/system/monitor',
}

export const getSystemInfo = () => {
  return defHttp.get({ url: DeptApi.prefix });
};
