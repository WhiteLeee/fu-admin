<template>
  <div>
    <div class="p-4">
      <GrowCard :loading="loading" class="enter-y" />
      <SiteAnalysis class="!my-4 enter-y" :loading="loading" />
      <div class="md:flex enter-y">
        <VisitRadar class="md:w-1/3 w-full" :loading="loading" />
        <VisitSource class="md:w-1/3 !md:mx-4 !md:my-0 !my-4 w-full" :loading="loading" />
        <SalesProductPie class="md:w-1/3 w-full" :loading="loading" />
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { ref } from 'vue';
  import GrowCard from './components/GrowCard.vue';
  import SiteAnalysis from './components/SiteAnalysis.vue';
  import VisitSource from './components/VisitSource.vue';
  import VisitRadar from './components/VisitRadar.vue';
  import SalesProductPie from './components/SalesProductPie.vue';
  // import { Modal, Button, Space } from 'ant-design-vue'; // Modal, Button, Space 已被移除

  const loading = ref(true);
  // const open = ref(true); // open 已被移除

  // const url = 'http://124.222.210.96:8080'; // url 已被移除

  // const fastApiUrl = 'http://124.222.210.96:7070'; // fastApiUrl 已被移除

  // const fastApiOpenUrl = 'https://gitee.com/fuadmin/fu-fastapi-vue'; // fastApiOpenUrl 已被移除

  setTimeout(() => {
    loading.value = false;
  }, 1500);

  // const handleOk = () => { // handleOk 已被移除
  //   window.location.href = url;
  //   open.value = false;
  // };
  // const handleCancel = () => { // handleCancel 已被移除
  //   open.value = false;
  // };
</script>
