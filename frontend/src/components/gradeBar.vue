<template>
    <div ref="gradeBarRef" class="chart">
        <!-- <p>{{ fatherDataName }}</p> -->
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref, defineProps } from 'vue';
import * as echarts from 'echarts';
import 'echarts/theme/macarons.js';

const props = defineProps({
    chartData: Object,
});
const gradeBarRef = ref<HTMLDivElement>()
onMounted(() => {
    console.log('props.chartData:', props.chartData);
    let data = props.chartData;
    let courseNameList = data?.courseName;
    let failedNum = data?.failed_nums;
    let failedRate = data?.failed_rates;
    // 基于准备好的dom，初始化echarts实例
    var myChart = echarts.init(gradeBarRef.value as HTMLDivElement, 'macarons');
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
                data: courseNameList,
                axisPointer: {
                    type: 'shadow'
                },
                axisLabel: {
                    //  让x轴文字方向为竖向
                    formatter: function (value: string) {
                        return value.split('').join('\n')
                    }
                },
               
            }
        ],
        yAxis: [
            {
                type: 'value',
                name: '个数',
                min: 0,
                max: 10,
                interval: 1,
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
</script>
<style scoped>
.chart {
    width: 1400px;
    height: 600px;
}
</style>