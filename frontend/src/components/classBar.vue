<template>
    <div ref="classBarRef" class="chart">
        <!-- <p>{{ fatherDataName }}</p> -->
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref, defineProps, watchEffect } from 'vue';
import * as echarts from 'echarts';
import 'echarts/theme/macarons.js';
import { fetchExcellentBarData } from '../api/index';

const props = defineProps({
    chartData: Object,
});
const classBarRef = ref<HTMLDivElement>()
onMounted(() => {
    watchEffect(()=>{
        console.log('props.chartData:',props.chartData);
        let data = props.chartData;
        let classNameList = data?.classNameList;
        let failedNum = data?.failedNum;
        let failedRate = data?.failedRate;
        // 基于准备好的dom，初始化echarts实例
        var myChart = echarts.init(classBarRef.value as HTMLDivElement, 'macarons');
        var option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross',
                    crossStyle: {
                        color: '#999'
                    }
                }
            },
            toolbox: {
                feature: {
                    dataView: { show: true, readOnly: false },
                    magicType: { show: true, type: ['line', 'bar'] },
                    restore: { show: true },
                    saveAsImage: { show: true }
                }
            },
            legend: {
                data: ['挂科人数', '挂科率']
            },
            xAxis: [
                {
                    type: 'category',
                    data: classNameList,
                    axisPointer: {
                        type: 'shadow'
                    }
                }
            ],
            yAxis: [
                {
                    type: 'value',
                    name: '个数',
                    min: 0,
                    max: 35,
                    interval: 5,
                    axisLabel: {
                        formatter: '{value} 个'
                    }
                },
                {
                    type: 'value',
                    name: '比例',
                    min: 0,
                    max: 100,
                    interval: 10,
                    axisLabel: {
                        formatter: '{value} %'
                    }
                }
            ],
            series: [
                {
                    name: '挂科人数',
                    type: 'bar',
                    tooltip: {
                        valueFormatter: function (value: string) {
                            return value + ' 个';
                        }
                    },
                    data: failedNum
                },
                {
                    name: '挂科率',
                    type: 'line',
                    yAxisIndex: 1,
                    tooltip: {
                        valueFormatter: function (value: string) {
                            return value + ' %';
                        }
                    },
                    data: failedRate
                }
            ]
        };
        // 绘制图表
        myChart.setOption(option);
        window.addEventListener('resize', () => {
            myChart.resize()
        })
    })
})
</script>
<style scoped>
.chart {
    width: 1400px;
    height: 500px;
}
</style>